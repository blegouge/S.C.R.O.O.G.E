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
    home_dir = (
        os.getenv("CLAUDE_HOME")
        or os.getenv("GEMINI_HOME")
        or os.getenv("ANTIGRAVITY_HOME")
        or os.getenv("HERMES_HOME")
        or os.getenv("CODEX_HOME")
        or os.getenv("CURSOR_HOME")
    )
    if home_dir:
        home_path = Path(home_dir).resolve()
    else:
        try:
            home_path = Path.home() / ".claude"
        except (RuntimeError, OSError):
            home_path = Path.cwd()

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


def _compute_jaccard_similarity(text1: str, text2: str) -> float:
    """Compute Jaccard similarity of 3-word shingles between two texts."""
    words1 = re.findall(r"\w+", text1.lower())
    words2 = re.findall(r"\w+", text2.lower())

    if not words1 or not words2:
        return 0.0

    shingles1 = {" ".join(words1[i : i + 3]) for i in range(len(words1) - 2)}
    shingles2 = {" ".join(words2[i : i + 3]) for i in range(len(words2) - 2)}

    # Fallback to single words if too short for 3-shingles
    if not shingles1 or not shingles2:
        shingles1 = set(words1)
        shingles2 = set(words2)

    intersection = shingles1 & shingles2
    union = shingles1 | shingles2

    if not union:
        return 0.0

    return len(intersection) / len(union)


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

        # Check config for similarity threshold
        from telemetry_config import config

        sim_threshold = getattr(config, "ccr_similarity_threshold", 0.85)

        best_sha = sha256_val
        best_similarity = 1.0
        found_near_dup = False

        if sim_threshold < 1.0 and cache_dir.is_dir():
            for item in cache_dir.iterdir():
                if item.is_file() and item.suffix == ".txt" and item.stem != sha256_val:
                    try:
                        cached_content = item.read_text(encoding="utf-8")
                        similarity = _compute_jaccard_similarity(content, cached_content)
                        if similarity >= sim_threshold:
                            if not found_near_dup or similarity > best_similarity:
                                best_similarity = similarity
                                best_sha = item.stem
                                found_near_dup = True
                    except Exception:
                        pass

        cache_file = cache_dir / f"{best_sha}.txt"

        try:
            if not found_near_dup:
                cache_file.write_text(content, encoding="utf-8")

            applied = True
            retrieve_path = "~/.cursor/bin/ccr_retrieve.py"
            if found_near_dup:
                pct = int(best_similarity * 100)
                return f"[CCR_BLOCK: {best_sha} (Collapsed logs, near-duplicate with {pct}% similarity). To retrieve the original, run the command: python3 {retrieve_path} {best_sha}]"
            else:
                return f"[CCR_BLOCK: {best_sha} (Collapsed logs). To retrieve the original, run the command: python3 {retrieve_path} {best_sha}]"
        except Exception as exc:
            sys.stderr.write(f"[ccr] Error caching block {best_sha}: {exc}\n")
            return match.group(0)

    processed_text = re.sub(r"```([a-zA-Z0-9_-]*)\n(.*?)\n```", replacer, text, flags=re.DOTALL)

    return processed_text, applied
