#!/usr/bin/env python3
"""
CCR Retrieval Tool.
Usage: python3 ccr_retrieve.py <sha256>
Reads the cached file content from projects/ccr_cache/<sha256>.txt and prints to stdout.
"""

import os
import sys
from pathlib import Path


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 ccr_retrieve.py <sha256>", file=sys.stderr)
        sys.exit(1)

    sha256 = sys.argv[1].strip()
    if not sha256.isalnum() or len(sha256) != 64:
        print("Error: Invalid SHA256 format", file=sys.stderr)
        sys.exit(1)

    home_dir = os.getenv("ANTIGRAVITY_HOME") or os.getenv("CURSOR_HOME")
    if home_dir:
        home_path = Path(home_dir).resolve()
    else:
        home_path = Path(__file__).resolve().parent.parent

    cache_file = home_path / "projects" / "ccr_cache" / f"{sha256}.txt"
    if not cache_file.is_file():
        print(f"Error: Cache file not found for {sha256}", file=sys.stderr)
        sys.exit(1)

    try:
        content = cache_file.read_text(encoding="utf-8")
        sys.stdout.write(content)
    except Exception as e:
        print(f"Error reading cache file: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
