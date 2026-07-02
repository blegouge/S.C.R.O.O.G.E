#!/usr/bin/env python3
"""
Reusable middleware to compress large prompt payloads before LLM calls.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from pathlib import Path
import sys

# Add parent directory to sys.path to resolve root-level modules (like token_compactor)
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from token_compactor import compress_prompt_context

CURSOR_HOME = Path.home() / ".cursor"
SRC_DIR = CURSOR_HOME / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from utils.adaptive_context_manager import (  # pylint: disable=import-error
    AdaptiveContextConfig,
    AdaptiveContextManager,
)
from utils.summarizer_factory import resolve_summarizer, resolve_summarizer_mode  # pylint: disable=import-error
from utils.static_prompt_registry import build_global_static_block  # pylint: disable=import-error


class PromptCompressionMiddleware:
    """Middleware-style helper for adaptive context + selective compression."""

    def __init__(
        self,
        default_rate: float = 0.6,
        min_chars_to_compress: int = 1200,
        adaptive_config: AdaptiveContextConfig | None = None,
        summarizer_mode: str | None = None,
    ) -> None:
        self.default_rate = default_rate
        self.min_chars_to_compress = min_chars_to_compress
        mode = summarizer_mode or resolve_summarizer_mode()
        runtime_config = adaptive_config or AdaptiveContextConfig(summarizer_mode=mode)
        self.adaptive_manager = AdaptiveContextManager(
            config=runtime_config,
            summarize_fn=resolve_summarizer(mode),
        )
        self.global_static_block = build_global_static_block()

    @staticmethod
    def _as_text(content: Any) -> str:
        return content if isinstance(content, str) else ""

    @staticmethod
    def _merge_system_blocks(messages: list[dict[str, Any]]) -> str:
        chunks: list[str] = []
        for message in messages:
            if message.get("role") != "system":
                continue
            text = PromptCompressionMiddleware._as_text(message.get("content")).strip()
            if text:
                chunks.append(text)
        return "\n\n".join(chunks)

    def _rebuild_messages(
        self,
        payload_copy: dict[str, Any],
        history_messages: list[dict[str, Any]],
        latest_message: dict[str, Any],
    ) -> None:
        static_block = self._merge_system_blocks(payload_copy["messages"]) or self.global_static_block
        latest_text = self._as_text(latest_message.get("content"))
        state = payload_copy.get("global_state")
        state_dict = state if isinstance(state, dict) else {}

        compacted_history, merged_state, _ = self.adaptive_manager.compact_history(
            history_messages,
            previous_state=state_dict,
        )
        rebuilt = self.adaptive_manager.build_cache_friendly_messages(
            static_system_block=static_block,
            global_state=merged_state,
            history_messages=compacted_history,
            latest_user_message=latest_text,
            ephemeral={"model": payload_copy.get("model", "")},
        )
        payload_copy["messages"] = rebuilt
        payload_copy["global_state"] = merged_state

    def before_llm_call(
        self,
        payload: dict[str, Any],
        rate: float | None = None,
    ) -> dict[str, Any]:
        """Return a payload clone with large text parts compressed."""
        if "messages" not in payload or not isinstance(payload["messages"], list):
            return payload

        final_rate = self.default_rate if rate is None else rate
        payload_copy = deepcopy(payload)

        if len(payload_copy["messages"]) >= 2:
            latest = payload_copy["messages"][-1]
            history = payload_copy["messages"][:-1]
            self._rebuild_messages(payload_copy, history, latest)

        for msg in payload_copy["messages"]:
            if not isinstance(msg, dict):
                continue
            content = msg.get("content")
            role = str(msg.get("role", ""))
            if (
                isinstance(content, str)
                and role != "system"
                and len(content) >= self.min_chars_to_compress
            ):
                compressed, _applied = compress_prompt_context(content, rate=final_rate)
                msg["content"] = compressed

        return payload_copy


def compress_messages(
    messages: list[dict[str, Any]],
    rate: float = 0.6,
    min_chars_to_compress: int = 1200,
) -> list[dict[str, Any]]:
    """Functional helper if you do not want to instantiate the middleware class."""
    middleware = PromptCompressionMiddleware(
        default_rate=rate,
        min_chars_to_compress=min_chars_to_compress,
    )
    return middleware.before_llm_call({"messages": messages})["messages"]
