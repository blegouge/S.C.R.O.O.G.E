#!/usr/bin/env python3
"""
CCR (Compress-Cache-Retrieve) Manager.
Caches large text blocks to ~/.cursor/projects/ccr_cache/<sha256>.txt
and replaces them with an instruction placeholder.
"""

import hashlib
import os
import re
import sys
import time
from pathlib import Path


def get_ccr_cache_dir() -> Path:
    home_dir = os.getenv("CURSOR_HOME") or os.getenv("ANTIGRAVITY_HOME")
    if home_dir:
        home_path = Path(home_dir).resolve()
    else:
        home_path = Path.home() / ".cursor"

    cache_dir = home_path / "projects" / "ccr_cache"
    return cache_dir


def clean_old_cache(ttl_hours: float = 24.0) -> int:
    """Cleans files in ccr_cache older than ttl_hours. Returns count of deleted files."""
    cache_dir = get_ccr_cache_dir()
    if not cache_dir.is_dir():
        return 0
    now = time.time()
    ttl_seconds = ttl_hours * 3600
    deleted = 0
    for item in cache_dir.iterdir():
        if item.is_file() and item.suffix == ".txt":
            try:
                mtime = item.stat().st_mtime
                if now - mtime > ttl_seconds:
                    item.unlink()
                    deleted += 1
            except Exception as e:
                sys.stderr.write(f"[ccr] Error cleaning {item}: {e}\n")
    return deleted


def ccr_compress(text: str, threshold_chars: int | None = None) -> tuple[str, bool]:
    """
    Scans the text for large code/log blocks, saves them to cache,
    and replaces them with a retrieval placeholder.
    Returns (processed_text, applied).
    """
    if not text:
        return text, False

    if threshold_chars is None:
        from telemetry_config import config

        threshold_chars = config.ccr_threshold_chars

    cache_dir = get_ccr_cache_dir()
    cache_dir.mkdir(parents=True, exist_ok=True)

    try:
        clean_old_cache()
    except Exception as e:
        sys.stderr.write(f"[ccr] Cleanup failed: {e}\n")

    applied = False

    def replacer(match: re.Match) -> str:
        nonlocal applied
        content = match.group(2)

        if len(content) < threshold_chars:
            return match.group(0)

        if "ccr_retrieve.py" in content and "[CCR_BLOCK:" in content:
            return match.group(0)

        sha256_val = hashlib.sha256(content.encode("utf-8")).hexdigest()
        cache_file = cache_dir / f"{sha256_val}.txt"

        try:
            cache_file.write_text(content, encoding="utf-8")
            applied = True

            retrieve_path = "~/.cursor/bin/ccr_retrieve.py"
            return f"[CCR_BLOCK: {sha256_val} (Collapsed logs). To retrieve the original, run the command: python3 {retrieve_path} {sha256_val}]"
        except Exception as exc:
            sys.stderr.write(f"[ccr] Error caching block {sha256_val}: {exc}\n")
            return match.group(0)

    processed_text = re.sub(r"```([a-zA-Z0-9_-]*)\n(.*?)\n```", replacer, text, flags=re.DOTALL)

    return processed_text, applied
