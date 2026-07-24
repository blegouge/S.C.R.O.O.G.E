#!/usr/bin/env python3
"""Tests for headroom_adapter compression orchestration and fallbacks."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[4]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import headroom_adapter


class _FakeCompressor:
    def __init__(self, output: str) -> None:
        self.output = output

    def compress(self, _text: str) -> str:
        return self.output


class HeadroomFlagTests(unittest.TestCase):
    def test_enabled_default_true(self) -> None:
        with patch.dict("os.environ", {}, clear=False):
            import os

            os.environ.pop("HEADROOM_ENABLED", None)
            self.assertTrue(headroom_adapter._enabled())

    def test_enabled_off(self) -> None:
        with patch.dict("os.environ", {"HEADROOM_ENABLED": "off"}, clear=False):
            self.assertFalse(headroom_adapter._enabled())

    def test_min_savings_pct_default_and_invalid(self) -> None:
        with patch.dict("os.environ", {"HEADROOM_MIN_SAVINGS_PCT": "not-a-number"}, clear=False):
            self.assertEqual(headroom_adapter._min_savings_pct(), 3.0)
        with patch.dict("os.environ", {"HEADROOM_MIN_SAVINGS_PCT": "10"}, clear=False):
            self.assertEqual(headroom_adapter._min_savings_pct(), 10.0)

    def test_is_json_like(self) -> None:
        self.assertTrue(headroom_adapter.is_json_like('{"a": 1}'))
        self.assertTrue(headroom_adapter.is_json_like("[1, 2, 3]"))
        self.assertFalse(headroom_adapter.is_json_like("plain text"))
        self.assertFalse(headroom_adapter.is_json_like("{not valid}"))


class LocalCodeCompressorFallbackTests(unittest.TestCase):
    def setUp(self) -> None:
        headroom_adapter._CODE_COMPRESSOR = None

    def tearDown(self) -> None:
        headroom_adapter._CODE_COMPRESSOR = None

    def test_local_code_compressor_collapses_blanks_and_trailing_ws(self) -> None:
        # Force ImportError path so the local fallback compressor is used.
        with patch.dict("sys.modules", {"headroom.compressors": None}):
            cc = headroom_adapter._get_code_compressor()
        out = cc.compress("a   \n\n\n\nb   \n")
        self.assertEqual(out, "a\n\nb")


class CompressPromptTextTests(unittest.TestCase):
    def setUp(self) -> None:
        headroom_adapter._CODE_COMPRESSOR = None
        headroom_adapter._SMART_CRUSHER = None

    def tearDown(self) -> None:
        headroom_adapter._CODE_COMPRESSOR = None
        headroom_adapter._SMART_CRUSHER = None

    def test_empty_or_disabled(self) -> None:
        out, stats = headroom_adapter.compress_prompt_text("")
        self.assertTrue(stats["skipped"])
        with patch.dict("os.environ", {"HEADROOM_ENABLED": "0"}, clear=False):
            out, stats = headroom_adapter.compress_prompt_text("hello")
            self.assertTrue(stats["skipped"])

    def test_code_compression_applied(self) -> None:
        headroom_adapter._CODE_COMPRESSOR = _FakeCompressor("short")
        long_text = "x" * 400
        with patch.object(headroom_adapter, "_ccr_enabled", return_value=False):
            out, stats = headroom_adapter.compress_prompt_text(long_text, tags={"code"})
        self.assertTrue(stats["applied"])
        self.assertEqual(out, "short")
        self.assertGreater(stats["saved_tokens"], 0)

    def test_below_min_savings_returns_original(self) -> None:
        # Compressor barely shrinks the text -> below 3% default threshold.
        text = "y" * 400
        headroom_adapter._CODE_COMPRESSOR = _FakeCompressor("y" * 399)
        with patch.object(headroom_adapter, "_ccr_enabled", return_value=False):
            out, stats = headroom_adapter.compress_prompt_text(text, tags={"code"})
        self.assertFalse(stats["applied"])
        self.assertEqual(out, text)

    def test_json_path_uses_smart_crusher(self) -> None:
        headroom_adapter._SMART_CRUSHER = _FakeCompressor("{}")
        payload = '{"key": "' + ("v" * 400) + '"}'
        with patch.object(headroom_adapter, "_ccr_enabled", return_value=False):
            out, stats = headroom_adapter.compress_prompt_text(payload)
        self.assertTrue(stats["applied"])
        self.assertIn("SmartCrusher", stats["compressor"])

    def test_unchanged_when_no_compressor_effect(self) -> None:
        headroom_adapter._CODE_COMPRESSOR = _FakeCompressor("plain text")
        with patch.object(headroom_adapter, "_ccr_enabled", return_value=False):
            # No tags, not json -> no compressor path applies -> falls to general (ImportError).
            with patch.dict("sys.modules", {"headroom": None}):
                out, stats = headroom_adapter.compress_prompt_text("plain text")
        self.assertFalse(stats.get("applied", False))


if __name__ == "__main__":
    unittest.main()
