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

PROJECT_ROOT = Path(__file__).resolve().parents[3]
for sub in ["src/telemetry", "src/compaction", "src/bridge", "hub_files/src"]:
    p = PROJECT_ROOT / sub
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import ccr_manager as ccr


class CacheDirTests(unittest.TestCase):
    def test_uses_claude_home(self) -> None:
        with patch.dict("os.environ", {"CLAUDE_HOME": "/tmp/hub"}, clear=True):
            self.assertEqual(
                ccr.get_ccr_cache_dir(), Path("/tmp/hub").resolve() / "projects" / "ccr_cache"
            )

    def test_uses_cursor_home(self) -> None:
        with patch.dict("os.environ", {"CURSOR_HOME": "/tmp/hub"}, clear=True):
            self.assertEqual(
                ccr.get_ccr_cache_dir(), Path("/tmp/hub").resolve() / "projects" / "ccr_cache"
            )

    def test_default_home(self) -> None:
        with patch.dict(
            "os.environ",
            {
                "CLAUDE_HOME": "",
                "GEMINI_HOME": "",
                "ANTIGRAVITY_HOME": "",
                "HERMES_HOME": "",
                "CODEX_HOME": "",
                "CURSOR_HOME": "",
            },
            clear=False,
        ):
            self.assertTrue(
                str(ccr.get_ccr_cache_dir()).endswith(
                    str(Path(".claude") / "projects" / "ccr_cache")
                )
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

    def test_near_duplicate_reuse(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cache = Path(tmp)
            block1 = "print('Hello World')\n" + "x" * 200
            block2 = "print('Hello World!')\n" + "x" * 200  # slightly different

            text1 = f"```python\n{block1}\n```"
            text2 = f"```python\n{block2}\n```"

            with patch.object(ccr, "get_ccr_cache_dir", return_value=cache):
                out1, applied1 = ccr.ccr_compress(text1, threshold_chars=50)
                self.assertTrue(applied1)

                # Check that 1 file is written
                files_before = sorted(cache.iterdir())
                self.assertEqual(len(files_before), 1)

                # Now compress the near-duplicate block2
                out2, applied2 = ccr.ccr_compress(text2, threshold_chars=50)
                self.assertTrue(applied2)

                # Check that no new file is written
                files_after = sorted(cache.iterdir())
                self.assertEqual(len(files_after), 1)

                # Check that out2 references the same sha256 as out1
                sha1 = out1.split("[CCR_BLOCK: ")[1].split(" ")[0]
                sha2 = out2.split("[CCR_BLOCK: ")[1].split(" ")[0]
                self.assertEqual(sha1, sha2)
                self.assertIn("near-duplicate", out2)

    def test_jaccard_similarity_calculation(self) -> None:
        t1 = "hello world python code test"
        t2 = "hello world python code testing"
        sim = ccr._compute_jaccard_similarity(t1, t2)
        self.assertTrue(0.5 <= sim <= 1.0)


if __name__ == "__main__":
    unittest.main()
