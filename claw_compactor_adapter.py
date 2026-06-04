#!/usr/bin/env python3
"""
Claw Compactor adapter for Cursor global hooks (FusionEngine, zero LLM cost).
"""
from __future__ import annotations

import os
import threading
from typing import Any

_ENGINE = None
_ENGINE_LOCK = threading.Lock()
_ENGINE_ERROR: Exception | None = None


def _enabled() -> bool:
    return os.getenv("CLAW_COMPACTOR_ENABLED", "1").strip().lower() not in {
        "0",
        "false",
        "no",
        "off",
    }


def _min_savings_pct() -> float:
    try:
        return max(0.0, float(os.getenv("CLAW_COMPACTOR_MIN_SAVINGS_PCT", "3")))
    except ValueError:
        return 3.0


def _aggressive() -> bool:
    return os.getenv("CLAW_COMPACTOR_AGGRESSIVE", "1").strip().lower() not in {
        "0",
        "false",
        "no",
        "off",
    }


def _enable_rewind() -> bool:
    return os.getenv("CLAW_COMPACTOR_REWIND", "0").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def content_type_from_tags(tags: set[str]) -> str:
    if "code" in tags:
        return "code"
    if "logs" in tags:
        return "log"
    if "subagent" in tags:
        return "text"
    return "text"


def _get_engine():
    global _ENGINE, _ENGINE_ERROR
    if _ENGINE is not None:
        return _ENGINE
    if _ENGINE_ERROR is not None:
        raise _ENGINE_ERROR
    with _ENGINE_LOCK:
        if _ENGINE is not None:
            return _ENGINE
        if _ENGINE_ERROR is not None:
            raise _ENGINE_ERROR
        try:
            from claw_compactor.fusion.engine import FusionEngine

            _ENGINE = FusionEngine(
                enable_rewind=_enable_rewind(),
                aggressive=_aggressive(),
            )
            return _ENGINE
        except Exception as exc:  # pylint: disable=broad-exception-caught
            _ENGINE_ERROR = exc
            raise


def compress_prompt_text(
    text: str,
    *,
    tags: set[str] | None = None,
    role: str = "user",
) -> tuple[str, dict[str, Any]]:
    """
    Compress prompt text via Claw Compactor Fusion pipeline.

    Returns (compressed_text, stats_dict). On skip/disabled/error, returns (text, {}).
    """
    if not text or not _enabled():
        return text, {"skipped": True, "reason": "disabled_or_empty"}

    content_type = content_type_from_tags(tags or set())
    try:
        engine = _get_engine()
        result = engine.compress(text, content_type=content_type, role=role)
    except Exception as exc:  # pylint: disable=broad-exception-caught
        return text, {"skipped": True, "reason": "error", "error": str(exc)}

    compressed = str(result.get("compressed", text))
    stats = result.get("stats") if isinstance(result.get("stats"), dict) else {}
    reduction = float(stats.get("reduction_pct", 0) or 0)
    if reduction < _min_savings_pct() and compressed != text:
        # Keep original when savings are below threshold (avoid noise for tiny blocks).
        return text, {**stats, "applied": False, "reason": "below_min_savings_pct"}
    if compressed == text:
        return text, {**stats, "applied": False, "reason": "unchanged"}

    return compressed, {**stats, "applied": True, "content_type": content_type}
