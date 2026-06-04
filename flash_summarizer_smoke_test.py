#!/usr/bin/env python3
"""Quick smoke test for flash/heuristic summarizers."""
from __future__ import annotations

import json
import sys
from pathlib import Path

SRC_DIR = Path.home() / ".cursor" / "src"
sys.path.insert(0, str(SRC_DIR))

from utils.flash_kv_summarizer import create_summarizer  # noqa: E402

SAMPLE = """
user: We fixed Bug_X on branch feature/token-opt and need to continue middleware wiring.
assistant: Implemented adaptive context manager with 4 cache-friendly blocks.
user: Add flash summarizer mode with Ollama fallback and keep heuristic mode.
"""


def main() -> None:
    for mode in ("heuristic", "auto", "flash"):
        summarizer = create_summarizer(mode)
        state = summarizer(SAMPLE, 8)
        print(f"\n=== mode={mode} ===")
        print(json.dumps(state, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
