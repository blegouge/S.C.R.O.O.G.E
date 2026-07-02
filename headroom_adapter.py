#!/usr/bin/env python3
"""
Headroom adapter for Cursor global hooks.
Provides CodeCompressor, SmartCrusher, CCR caching, and general headroom compression.
"""
from __future__ import annotations

import os
import json
import threading
from typing import Any
import sys

_CODE_COMPRESSOR = None
_SMART_CRUSHER = None
_LOCK = threading.Lock()
_ERRORS: dict[str, Exception] = {}

def _enabled() -> bool:
    return os.getenv("HEADROOM_ENABLED", "1").strip().lower() not in {
        "0",
        "false",
        "no",
        "off",
    }

def _ccr_enabled() -> bool:
    from telemetry_config import config
    return config.ccr_enabled

def _min_savings_pct() -> float:
    try:
        return max(0.0, float(os.getenv("HEADROOM_MIN_SAVINGS_PCT", "3")))
    except ValueError:
        return 3.0

def _get_code_compressor():
    global _CODE_COMPRESSOR
    if _CODE_COMPRESSOR is not None:
        return _CODE_COMPRESSOR
    with _LOCK:
        if _CODE_COMPRESSOR is not None:
            return _CODE_COMPRESSOR
        try:
            from headroom.compressors import CodeCompressor, CodeCompressorConfig
            _CODE_COMPRESSOR = CodeCompressor(CodeCompressorConfig())
        except ImportError:
            class LocalCodeCompressor:
                def compress(self, text: str) -> str:
                    lines = []
                    for line in text.splitlines():
                        line_stripped = line.rstrip()
                        if not line_stripped:
                            if not lines or lines[-1] != "":
                                lines.append("")
                        else:
                            lines.append(line_stripped)
                    return "\n".join(lines)
            _CODE_COMPRESSOR = LocalCodeCompressor()
        return _CODE_COMPRESSOR

def _get_smart_crusher():
    global _SMART_CRUSHER
    if _SMART_CRUSHER is not None:
        return _SMART_CRUSHER
    with _LOCK:
        if _SMART_CRUSHER is not None:
            return _SMART_CRUSHER
        try:
            from headroom.compressors import SmartCrusher, SmartCrusherConfig
            _SMART_CRUSHER = SmartCrusher(SmartCrusherConfig())
        except ImportError:
            try:
                from smart_crusher import SmartCrusher as LocalSmartCrusher, SmartCrusherConfig as LocalSmartCrusherConfig
                _SMART_CRUSHER = LocalSmartCrusher(LocalSmartCrusherConfig())
            except Exception as exc:
                sys.stderr.write(f"[headroom] Fallback SmartCrusher import error: {exc}\n")
                raise
        return _SMART_CRUSHER

def is_json_like(text: str) -> bool:
    trimmed = text.strip()
    if (trimmed.startswith("{") and trimmed.endswith("}")) or (trimmed.startswith("[") and trimmed.endswith("]")):
        try:
            json.loads(trimmed)
            return True
        except ValueError:
            pass
    return False

def compress_prompt_text(
    text: str,
    *,
    tags: set[str] | None = None,
    role: str = "user",
) -> tuple[str, dict[str, Any]]:
    """
    Compress prompt text via Headroom and CCR compressors.
    Returns (compressed_text, stats_dict).
    """
    if not text or not _enabled():
        return text, {"skipped": True, "reason": "disabled_or_empty"}

    tags = tags or set()
    compressed = text
    compressor_name = "none"
    applied = False

    if _ccr_enabled():
        try:
            from ccr_manager import ccr_compress
            compressed, ccr_applied = ccr_compress(text)
            if ccr_applied:
                compressor_name = "CCR"
                applied = True
        except Exception as exc:
            sys.stderr.write(f"[headroom] CCR compression error: {exc}\n")

    try:
        if "code" in tags:
            try:
                cc = _get_code_compressor()
                text_before = compressed
                compressed = cc.compress(compressed)
                if compressed != text_before:
                    compressor_name = "CCR+CodeCompressor" if applied else "CodeCompressor"
                    applied = True
            except Exception as exc:
                sys.stderr.write(f"[headroom] CodeCompressor error: {exc}\n")

        if (is_json_like(compressed) or "logs" in tags):
            try:
                sc = _get_smart_crusher()
                text_before = compressed
                compressed = sc.compress(compressed)
                if compressed != text_before:
                    compressor_name = "CCR+SmartCrusher" if applied else "SmartCrusher"
                    applied = True
            except Exception as exc:
                sys.stderr.write(f"[headroom] SmartCrusher error: {exc}\n")

        if not applied:
            try:
                from headroom import compress
                messages = [{"role": role, "content": text}]
                result = compress(messages)
                if hasattr(result, "messages") and len(result.messages) > 0:
                    compressed = result.messages[0].get("content", text)
                    compressor_name = "GeneralCompress"
                    applied = (compressed != text)
            except ImportError:
                pass
            except Exception as exc:
                sys.stderr.write(f"[headroom] General compress error: {exc}\n")

    except Exception as exc:
        return text, {"skipped": True, "reason": "error", "error": str(exc)}

    if not applied:
        return text, {"applied": False, "reason": "unchanged"}

    before_tokens = (len(text) + 3) // 4
    after_tokens = (len(compressed) + 3) // 4
    saved_tokens = max(0, before_tokens - after_tokens)
    reduction_pct = round((saved_tokens * 100.0 / before_tokens) if before_tokens else 0.0, 2)

    stats = {
        "applied": True,
        "compressor": compressor_name,
        "reduction_pct": reduction_pct,
        "saved_tokens": saved_tokens,
    }

    if reduction_pct < _min_savings_pct():
        return text, {**stats, "applied": False, "reason": "below_min_savings_pct"}

    return compressed, stats
