#!/usr/bin/env python3
"""Tests for token_compactor (LLMLingua adapter) pure helpers and fallbacks."""

from __future__ import annotations

import sys
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

import token_compactor


class _FakeCompressor:
    """Minimal stand-in for LLMLingua PromptCompressor."""

    def __init__(self, ratio: float = 0.5) -> None:
        self.ratio = ratio
        self.calls = 0

    def compress_prompt(self, context, **_kwargs):
        self.calls += 1
        chunk = context[0]
        compressed = chunk[: max(1, int(len(chunk) * self.ratio))]
        return {
            "compressed_prompt": compressed,
            "origin_tokens": max(1, len(chunk) // 4),
            "compressed_tokens": max(1, len(compressed) // 4),
        }


class TokenCompactorHelperTests(unittest.TestCase):
    def tearDown(self) -> None:
        # Reset module-level singletons to avoid cross-test contamination.
        token_compactor._COMPRESSOR = None
        token_compactor._COMPRESSOR_ERROR = None

    def test_first_non_empty_dedupes_and_filters(self) -> None:
        result = token_compactor._first_non_empty(("", "a", "b", "a", ""))
        self.assertEqual(result, ["a", "b"])

    def test_approx_token_count(self) -> None:
        self.assertEqual(token_compactor._approx_token_count(""), 0)
        self.assertEqual(token_compactor._approx_token_count("abcd"), 1)
        self.assertEqual(token_compactor._approx_token_count("a" * 9), 3)

    def test_pick_count_prefers_first_match_and_casts(self) -> None:
        self.assertEqual(token_compactor._pick_count({"b": 5}, ("a", "b")), 5)
        self.assertEqual(token_compactor._pick_count({"a": 2.9}, ("a",)), 2)
        self.assertIsNone(token_compactor._pick_count({"a": "x"}, ("a",)))
        self.assertIsNone(token_compactor._pick_count({}, ("a",)))

    def test_chunk_text_short_returns_single(self) -> None:
        self.assertEqual(token_compactor._chunk_text("short"), ["short"])

    def test_chunk_text_splits_large_input(self) -> None:
        text = ("word " * 500).strip()
        chunks = token_compactor._chunk_text(text, chunk_size=100)
        self.assertGreater(len(chunks), 1)
        # Reassembly must be lossless.
        self.assertEqual("".join(chunks), text)


class CompressPromptContextTests(unittest.TestCase):
    def tearDown(self) -> None:
        token_compactor._COMPRESSOR = None
        token_compactor._COMPRESSOR_ERROR = None

    def test_empty_prompt_short_circuits(self) -> None:
        out, applied = token_compactor.compress_prompt_context("")
        self.assertEqual(out, "")
        self.assertFalse(applied)

    def test_skips_when_not_ready_and_blocking_disabled(self) -> None:
        token_compactor._COMPRESSOR = None
        token_compactor._COMPRESSOR_ERROR = None

        class _Cfg:
            llmlingua_blocking_init = False

        with patch("telemetry_config.config", _Cfg()):
            with patch.object(token_compactor, "warmup_compressor") as warm:
                out, applied = token_compactor.compress_prompt_context("some text here")
        self.assertEqual(out, "some text here")
        self.assertFalse(applied)
        warm.assert_called_once()

    def test_init_failure_falls_back_to_original(self) -> None:
        token_compactor._COMPRESSOR = None

        class _Cfg:
            llmlingua_blocking_init = True

        with patch("telemetry_config.config", _Cfg()):
            with patch.object(
                token_compactor, "_init_compressor", side_effect=RuntimeError("boom")
            ):
                out, applied = token_compactor.compress_prompt_context("payload")
        self.assertEqual(out, "payload")
        self.assertFalse(applied)

    def test_happy_path_with_injected_compressor(self) -> None:
        token_compactor._COMPRESSOR = _FakeCompressor(ratio=0.5)
        text = "def f():\n    return 42\n" * 5
        out, applied = token_compactor.compress_prompt_context(text, rate=0.5)
        self.assertTrue(applied)
        self.assertLess(len(out), len(text))

    def test_rate_is_bounded(self) -> None:
        fake = _FakeCompressor(ratio=0.5)
        token_compactor._COMPRESSOR = fake
        # rate above 1.0 must be clamped without raising.
        out, applied = token_compactor.compress_prompt_context("hello world", rate=5.0)
        self.assertTrue(applied)
        self.assertGreaterEqual(fake.calls, 1)

    def test_chunk_compression_failure_keeps_chunk(self) -> None:
        class _RaisingCompressor:
            def compress_prompt(self, context, **_kwargs):
                raise ValueError("chunk failure")

        token_compactor._COMPRESSOR = _RaisingCompressor()
        out, applied = token_compactor.compress_prompt_context("keep me intact")
        # applied is True (attempted) but content is preserved on failure.
        self.assertTrue(applied)
        self.assertEqual(out, "keep me intact")


if __name__ == "__main__":
    unittest.main()
