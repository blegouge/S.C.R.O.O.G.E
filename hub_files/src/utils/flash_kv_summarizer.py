#!/usr/bin/env python3
"""
Flash KV summarizer: lightweight LLM extraction with heuristic fallback.
"""

from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass

from utils.adaptive_context_manager import StateDict, local_kv_summarizer

SummarizerFn = Callable[[str, int], StateDict]

_FLASH_SYSTEM = (
    "You compress conversation history into a compact JSON object of string keys and string values. "
    "Use concise PascalCase or Snake_Case keys (examples: Status, Active_Branch, Blocker, "
    "Files_Touched, Decision). Keep values short (max 240 chars). "
    "Output ONLY a valid JSON object, no markdown and no commentary."
)


@dataclass(slots=True)
class FlashSummarizerConfig:
    """Runtime options for flash summarization."""

    provider: str = ""  # ollama | openai | anthropic | empty = auto-detect
    ollama_host: str = "http://127.0.0.1:11434"
    ollama_model: str = "llama3.2:1b"
    openai_model: str = "gpt-4o-mini"
    anthropic_model: str = "claude-3-5-haiku-20241022"
    timeout_sec: float = 8.0
    min_chars: int = 400
    max_input_chars: int = 12000


def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def _normalize_key(key: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9_]+", "_", key.strip()).strip("_")
    return normalized[:64]


def _normalize_state(raw: object, max_items: int) -> StateDict:
    if not isinstance(raw, dict):
        return {}
    out: StateDict = {}
    for key, value in raw.items():
        if not isinstance(key, str):
            continue
        if value is None:
            continue
        text_value = str(value).strip()
        if not text_value:
            continue
        normalized_key = _normalize_key(key)
        if not normalized_key or normalized_key in out:
            continue
        out[normalized_key] = text_value[:240]
        if len(out) >= max_items:
            break
    return out


def _extract_json_object(text: str) -> StateDict:
    stripped = text.strip()
    if not stripped:
        return {}
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", stripped, re.DOTALL)
    if fence:
        stripped = fence.group(1)
    else:
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start >= 0 and end > start:
            stripped = stripped[start : end + 1]
    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError:
        return {}
    return _normalize_state(parsed, max_items=64)


def _http_post_json(url: str, payload: dict, headers: dict[str, str], timeout_sec: float) -> dict:
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=body, headers=headers, method="POST")
    with urllib.request.urlopen(request, timeout=timeout_sec) as response:
        raw = response.read().decode("utf-8")
    parsed = json.loads(raw)
    return parsed if isinstance(parsed, dict) else {}


def _build_user_prompt(text: str, max_items: int) -> str:
    clipped = text[:12000]
    return (
        f"Summarize this conversation fragment into at most {max_items} key-value pairs.\n\n"
        f"---\n{clipped}\n---"
    )


def _detect_provider(config: FlashSummarizerConfig) -> str:
    if config.provider:
        return config.provider.lower()
    if _env("FLASH_SUMMARIZER_PROVIDER"):
        return _env("FLASH_SUMMARIZER_PROVIDER").lower()
    if _env("OLLAMA_HOST") or _ollama_reachable(config):
        return "ollama"
    if _env("OPENAI_API_KEY"):
        return "openai"
    if _env("ANTHROPIC_API_KEY"):
        return "anthropic"
    return ""


def _ollama_reachable(config: FlashSummarizerConfig) -> bool:
    url = f"{config.ollama_host.rstrip('/')}/api/tags"
    try:
        with urllib.request.urlopen(url, timeout=2.0):
            return True
    except (urllib.error.URLError, TimeoutError, ValueError):
        return False


def _call_ollama(text: str, max_items: int, config: FlashSummarizerConfig) -> StateDict:
    host = _env("OLLAMA_HOST", config.ollama_host).rstrip("/")
    model = _env("OLLAMA_MODEL", config.ollama_model)
    url = f"{host}/api/chat"
    payload = {
        "model": model,
        "stream": False,
        "format": "json",
        "messages": [
            {"role": "system", "content": _FLASH_SYSTEM},
            {"role": "user", "content": _build_user_prompt(text, max_items)},
        ],
        "options": {"temperature": 0.1, "num_predict": 512},
    }
    response = _http_post_json(
        url, payload, headers={"Content-Type": "application/json"}, timeout_sec=config.timeout_sec
    )
    message = response.get("message")
    content = message.get("content") if isinstance(message, dict) else ""
    if not isinstance(content, str):
        return {}
    return _extract_json_object(content)


def _call_openai(text: str, max_items: int, config: FlashSummarizerConfig) -> StateDict:
    api_key = _env("OPENAI_API_KEY")
    if not api_key:
        return {}
    model = _env("FLASH_OPENAI_MODEL", config.openai_model)
    url = _env("FLASH_OPENAI_BASE_URL", "https://api.openai.com/v1/chat/completions")
    payload = {
        "model": model,
        "temperature": 0.1,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": _FLASH_SYSTEM},
            {"role": "user", "content": _build_user_prompt(text, max_items)},
        ],
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    response = _http_post_json(url, payload, headers=headers, timeout_sec=config.timeout_sec)
    choices = response.get("choices")
    if not isinstance(choices, list) or not choices:
        return {}
    first = choices[0]
    if not isinstance(first, dict):
        return {}
    message = first.get("message")
    if not isinstance(message, dict):
        return {}
    content = message.get("content")
    if not isinstance(content, str):
        return {}
    return _extract_json_object(content)


def _call_anthropic(text: str, max_items: int, config: FlashSummarizerConfig) -> StateDict:
    api_key = _env("ANTHROPIC_API_KEY")
    if not api_key:
        return {}
    model = _env("FLASH_ANTHROPIC_MODEL", config.anthropic_model)
    url = "https://api.anthropic.com/v1/messages"
    payload = {
        "model": model,
        "max_tokens": 512,
        "temperature": 0.1,
        "system": _FLASH_SYSTEM,
        "messages": [{"role": "user", "content": _build_user_prompt(text, max_items)}],
    }
    headers = {
        "Content-Type": "application/json",
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
    }
    response = _http_post_json(url, payload, headers=headers, timeout_sec=config.timeout_sec)
    content_blocks = response.get("content")
    if not isinstance(content_blocks, list):
        return {}
    text_parts: list[str] = []
    for block in content_blocks:
        if isinstance(block, dict) and block.get("type") == "text":
            text_value = block.get("text")
            if isinstance(text_value, str):
                text_parts.append(text_value)
    return _extract_json_object("\n".join(text_parts))


def flash_kv_summarize(
    text: str, max_items: int = 12, config: FlashSummarizerConfig | None = None
) -> StateDict:
    """Call a flash/local model and return normalized KV state (may be empty)."""
    runtime = config or FlashSummarizerConfig(
        provider=_env("FLASH_SUMMARIZER_PROVIDER"),
        ollama_host=_env("OLLAMA_HOST", "http://127.0.0.1:11434"),
        ollama_model=_env("OLLAMA_MODEL", "llama3.2:1b"),
        openai_model=_env("FLASH_OPENAI_MODEL", "gpt-4o-mini"),
        anthropic_model=_env("FLASH_ANTHROPIC_MODEL", "claude-3-5-haiku-20241022"),
        timeout_sec=float(_env("FLASH_SUMMARIZER_TIMEOUT_SEC", "8") or "8"),
        min_chars=int(_env("FLASH_SUMMARIZER_MIN_CHARS", "400") or "400"),
        max_input_chars=int(_env("FLASH_SUMMARIZER_MAX_INPUT_CHARS", "12000") or "12000"),
    )
    if len(text.strip()) < runtime.min_chars:
        return {}

    provider = _detect_provider(runtime)
    clipped = text[: runtime.max_input_chars]
    try:
        if provider == "ollama":
            state = _call_ollama(clipped, max_items, runtime)
        elif provider == "openai":
            state = _call_openai(clipped, max_items, runtime)
        elif provider == "anthropic":
            state = _call_anthropic(clipped, max_items, runtime)
        else:
            return {}
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, ValueError) as exc:
        print(f"[flash-summarizer] provider={provider or 'none'} failed: {exc}", file=sys.stderr)
        return {}

    return _normalize_state(state, max_items=max_items)


def hybrid_kv_summarizer(
    text: str, max_items: int = 12, config: FlashSummarizerConfig | None = None
) -> StateDict:
    """Try flash summarization first, then fallback to local heuristic summarizer."""
    flash_state = flash_kv_summarize(text, max_items=max_items, config=config)
    if flash_state:
        return flash_state
    return local_kv_summarizer(text, max_items=max_items)


def create_summarizer(mode: str | None = None) -> SummarizerFn:
    """
    Build a summarizer callable.

    Modes:
    - heuristic: local only (fast, no network)
    - flash: flash only (returns {} then caller should fallback - use hybrid instead)
    - auto: flash attempt with heuristic fallback (recommended)
    """
    selected = (mode or _env("ADAPTIVE_CTX_SUMMARIZER", "auto")).strip().lower()
    runtime_config = FlashSummarizerConfig(
        provider=_env("FLASH_SUMMARIZER_PROVIDER"),
        ollama_host=_env("OLLAMA_HOST", "http://127.0.0.1:11434"),
        ollama_model=_env("OLLAMA_MODEL", "llama3.2:1b"),
        openai_model=_env("FLASH_OPENAI_MODEL", "gpt-4o-mini"),
        anthropic_model=_env("FLASH_ANTHROPIC_MODEL", "claude-3-5-haiku-20241022"),
        timeout_sec=float(_env("FLASH_SUMMARIZER_TIMEOUT_SEC", "8") or "8"),
        min_chars=int(_env("FLASH_SUMMARIZER_MIN_CHARS", "400") or "400"),
        max_input_chars=int(_env("FLASH_SUMMARIZER_MAX_INPUT_CHARS", "12000") or "12000"),
    )

    if selected == "heuristic":
        return local_kv_summarizer
    if selected == "flash":

        def _flash_sum(text: str, max_items: int) -> StateDict:
            return flash_kv_summarize(
                text, max_items=max_items, config=runtime_config
            ) or local_kv_summarizer(text, max_items=max_items)

        return _flash_sum

    # auto (default)
    def _auto_sum(text: str, max_items: int) -> StateDict:
        return hybrid_kv_summarizer(text, max_items=max_items, config=runtime_config)

    return _auto_sum
