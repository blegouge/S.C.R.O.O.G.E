#!/usr/bin/env python3
"""Tests for ccr_manager cache dir resolution, cleanup and block compression."""

from __future__ import annotations

import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[4]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import ccr_manager as ccr


class CacheDirTests(unittest.TestCase):
    def test_uses_cursor_home(self) -> None:
        with patch.dict("os.environ", {"CURSOR_HOME": "/tmp/hub"}, clear=True):
            self.assertEqual(
                ccr.get_ccr_cache_dir(), Path("/tmp/hub").resolve() / "projects" / "ccr_cache"
            )

    def test_default_home(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            self.assertEqual(
                ccr.get_ccr_cache_dir(), Path.home() / ".cursor" / "projects" / "ccr_cache"
            )


class CleanOldCacheTests(unittest.TestCase):
    def test_missing_dir_returns_zero(self) -> None:
        with patch.object(ccr, "get_ccr_cache_dir", return_value=Path("/no/such/dir")):
            self.assertEqual(ccr.clean_old_cache(), 0)

    def test_deletes_old_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cache = Path(tmp)
            old = cache / "old.txt"
            old.write_text("x", encoding="utf-8")
            past = time.time() - 48 * 3600
            os.utime(old, (past, past))
            fresh = cache / "fresh.txt"
            fresh.write_text("y", encoding="utf-8")
            with patch.object(ccr, "get_ccr_cache_dir", return_value=cache):
                deleted = ccr.clean_old_cache(ttl_hours=24.0)
            self.assertEqual(deleted, 1)
            self.assertFalse(old.exists())
            self.assertTrue(fresh.exists())


class CcrCompressTests(unittest.TestCase):
    def test_empty_text(self) -> None:
        self.assertEqual(ccr.ccr_compress(""), ("", False))

    def test_large_block_cached(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cache = Path(tmp)
            block = "print('x')\n" * 50  # well above a small threshold
            text = f"```python\n{block}\n```"
            with patch.object(ccr, "get_ccr_cache_dir", return_value=cache):
                out, applied = ccr.ccr_compress(text, threshold_chars=20)
            self.assertTrue(applied)
            self.assertIn("[CCR_BLOCK:", out)
            self.assertTrue(any(p.suffix == ".txt" for p in cache.iterdir()))

    def test_small_block_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cache = Path(tmp)
            text = "```py\nx=1\n```"
            with patch.object(ccr, "get_ccr_cache_dir", return_value=cache):
                out, applied = ccr.ccr_compress(text, threshold_chars=9999)
            self.assertFalse(applied)
            self.assertEqual(out, text)

    def test_already_ccr_block_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cache = Path(tmp)
            inner = "ccr_retrieve.py [CCR_BLOCK: abc]" + "x" * 100
            text = f"```\n{inner}\n```"
            with patch.object(ccr, "get_ccr_cache_dir", return_value=cache):
                out, applied = ccr.ccr_compress(text, threshold_chars=20)
            self.assertFalse(applied)


if __name__ == "__main__":
    unittest.main()
