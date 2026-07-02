#!/usr/bin/env python3
"""
LLMLingua prompt compaction utility for large prompt/context payloads.
"""
from __future__ import annotations

import os
import sys
import threading
from typing import Any

# Local venv dependency; imported lazily inside _init_compressor.
# from llmlingua import PromptCompressor

_DEFAULT_MODEL_CANDIDATES = (
    os.getenv("LLMLINGUA_MODEL", "").strip(),
    "microsoft/llmlingua-2-bert-base-multilingual-cased-meetingbank",
    "microsoft/llmlingua-2-xlm-roberta-large-meetingbank",
    "microsoft/llmlingua-2-bert-base-multilingual-cased",
)

_COMPRESSOR: Any = None
_COMPRESSOR_ERROR: Exception | None = None
_COMPRESSOR_LOCK = threading.Lock()
_LOADING_THREAD: threading.Thread | None = None


def _first_non_empty(items: tuple[str, ...]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if not item:
            continue
        if item in seen:
            continue
        seen.add(item)
        out.append(item)
    return out


def _init_compressor(blocking: bool = True) -> Any:
    # pylint: disable=global-statement,broad-exception-caught
    global _COMPRESSOR
    global _COMPRESSOR_ERROR

    if _COMPRESSOR is not None:
        return _COMPRESSOR
    if _COMPRESSOR_ERROR is not None:
        if blocking:
            raise _COMPRESSOR_ERROR
        return None

    if not blocking:
        return None

    with _COMPRESSOR_LOCK:
        if _COMPRESSOR is not None:
            return _COMPRESSOR
        if _COMPRESSOR_ERROR is not None:
            raise _COMPRESSOR_ERROR

        try:
            from llmlingua import PromptCompressor
        except Exception as exc:
            _COMPRESSOR_ERROR = exc
            raise exc

        last_error: Exception | None = None
        for model_name in _first_non_empty(_DEFAULT_MODEL_CANDIDATES):
            try:
                # LLMLingua-2 performs token filtering with perplexity-aware scoring.
                _COMPRESSOR = PromptCompressor(
                    model_name=model_name,
                    use_llmlingua2=True,
                    device_map="cpu",
                )
                print(f"[LLMLingua] Model loaded: {model_name}", file=sys.stderr)
                return _COMPRESSOR
            except Exception as exc:  # pragma: no cover - defensive init fallback
                last_error = exc
                print(f"[LLMLingua] Model init failed for '{model_name}': {exc}", file=sys.stderr)

        _COMPRESSOR_ERROR = last_error or RuntimeError("Unable to initialize LLMLingua")
        raise _COMPRESSOR_ERROR


def warmup_compressor() -> None:
    """Spins up a background thread to load LLMLingua-2 without blocking the main execution."""
    global _LOADING_THREAD
    if _COMPRESSOR is not None or _COMPRESSOR_ERROR is not None:
        return
    with _COMPRESSOR_LOCK:
        if _COMPRESSOR is not None or _COMPRESSOR_ERROR is not None:
            return
        if _LOADING_THREAD is not None and _LOADING_THREAD.is_alive():
            return

        def bg_load():
            try:
                _init_compressor(blocking=True)
            except Exception:
                pass

        _LOADING_THREAD = threading.Thread(target=bg_load, name="llmlingua-warmup", daemon=True)
        _LOADING_THREAD.start()
        print("[LLMLingua] Background warmup initiated.", file=sys.stderr)


def _approx_token_count(text: str) -> int:
    # Fast, model-agnostic estimate close enough for runtime gain tracking.
    return max(1, (len(text) + 3) // 4) if text else 0


def _pick_count(result: dict[str, Any], keys: tuple[str, ...]) -> int | None:
    for key in keys:
        value = result.get(key)
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            return int(value)
    return None


def _chunk_text(text: str, chunk_size: int = 900) -> list[str]:
    if len(text) <= chunk_size:
        return [text]
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(len(text), start + chunk_size)
        if end < len(text):
            split_newline = text.rfind("\n", start, end)
            split_space = text.rfind(" ", start, end)
            best_split = max(split_newline, split_space)
            if best_split > start + (chunk_size // 2):
                end = best_split + 1
        chunks.append(text[start:end])
        start = end
    return chunks


def compress_prompt_context(prompt: str, rate: float = 0.6) -> tuple[str, bool]:
    """
    Compress a prompt/context block using LLMLingua-2.

    Args:
        prompt: Raw prompt/context text (code, traces, sub-agent output, etc.).
        rate: Kept information ratio (0.1..1.0). Lower value = stronger compression.

    Returns:
        Tuple of (compressed prompt, applied). Falls back to original prompt when init fails.
    """
    # pylint: disable=broad-exception-caught
    if not prompt:
        return prompt, False

    bounded_rate = min(max(rate, 0.1), 1.0)
    try:
        from telemetry_config import config
        blocking_init = config.llmlingua_blocking_init
        if _COMPRESSOR is None:
            if not blocking_init:
                warmup_compressor()
                print("[LLMLingua] Model not ready and blocking init is disabled, skipping compression for this turn.", file=sys.stderr)
                return prompt, False
            compressor = _init_compressor(blocking=True)
        else:
            compressor = _COMPRESSOR
    except Exception as exc:
        print(f"[LLMLingua] Initialization failed, fallback to original prompt: {exc}", file=sys.stderr)
        return prompt, False

    compressed_parts: list[str] = []
    original_total = 0
    compressed_total = 0

    for chunk in _chunk_text(prompt):
        try:
            result = compressor.compress_prompt(
                context=[chunk],
                rate=bounded_rate,
                force_tokens=["\n", "```", "def", "class", "import"],
                drop_consecutive=True,
            )
            if isinstance(result, dict):
                compressed_chunk = result.get("compressed_prompt", "") or chunk
                original_tokens = _pick_count(
                    result,
                    (
                        "origin_tokens",
                        "original_tokens",
                        "origin_token_count",
                        "origin_token_length",
                    ),
                )
                compressed_tokens = _pick_count(
                    result,
                    (
                        "compressed_tokens",
                        "compressed_token_count",
                        "compressed_token_length",
                    ),
                )
            else:
                compressed_chunk = str(result)
                original_tokens = None
                compressed_tokens = None
        except Exception as exc:
            print(f"[LLMLingua] Compression failed on chunk, keep original chunk: {exc}", file=sys.stderr)
            compressed_chunk = chunk
            original_tokens = None
            compressed_tokens = None

        compressed_parts.append(compressed_chunk)
        original_total += original_tokens or _approx_token_count(chunk)
        compressed_total += compressed_tokens or _approx_token_count(compressed_chunk)

    compressed = "".join(compressed_parts)

    saved = max(0.0, 100.0 * (1.0 - (compressed_total / max(1, original_total))))

    print(
        "[LLMLingua] "
        f"Tokens Originaux: {original_total} | "
        f"Tokens Compresses: {compressed_total} | "
        f"Economie: {saved:.2f}%",
        file=sys.stderr,
    )

    return compressed, True
