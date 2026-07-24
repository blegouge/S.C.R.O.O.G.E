#!/usr/bin/env python3
"""Tests for claw_compactor_adapter flags and compression wrapper."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[4]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import claw_compactor_adapter as claw


class _FakeEngine:
    def __init__(self, compressed: str, reduction_pct: float) -> None:
        self.compressed = compressed
        self.reduction_pct = reduction_pct

    def compress(self, _text: str, content_type: str = "text", role: str = "user") -> dict:
        return {
            "compressed": self.compressed,
            "stats": {"reduction_pct": self.reduction_pct, "content_type": content_type},
        }


class ClawFlagTests(unittest.TestCase):
    def test_enabled_default_and_off(self) -> None:
        import os

        with patch.dict("os.environ", {}, clear=False):
            os.environ.pop("CLAW_COMPACTOR_ENABLED", None)
            self.assertTrue(claw._enabled())
        with patch.dict("os.environ", {"CLAW_COMPACTOR_ENABLED": "false"}, clear=False):
            self.assertFalse(claw._enabled())

    def test_min_savings_pct_invalid(self) -> None:
        with patch.dict("os.environ", {"CLAW_COMPACTOR_MIN_SAVINGS_PCT": "abc"}, clear=False):
            self.assertEqual(claw._min_savings_pct(), 3.0)

    def test_aggressive_and_rewind_flags(self) -> None:
        with patch.dict("os.environ", {"CLAW_COMPACTOR_AGGRESSIVE": "0"}, clear=False):
            self.assertFalse(claw._aggressive())
        with patch.dict("os.environ", {"CLAW_COMPACTOR_REWIND": "1"}, clear=False):
            self.assertTrue(claw._enable_rewind())

    def test_content_type_from_tags(self) -> None:
        self.assertEqual(claw.content_type_from_tags({"code"}), "code")
        self.assertEqual(claw.content_type_from_tags({"logs"}), "log")
        self.assertEqual(claw.content_type_from_tags({"subagent"}), "text")
        self.assertEqual(claw.content_type_from_tags(set()), "text")


class ClawCompressTests(unittest.TestCase):
    def tearDown(self) -> None:
        claw._ENGINE = None
        claw._ENGINE_ERROR = None

    def test_empty_or_disabled(self) -> None:
        out, stats = claw.compress_prompt_text("")
        self.assertTrue(stats["skipped"])
        with patch.dict("os.environ", {"CLAW_COMPACTOR_ENABLED": "0"}, clear=False):
            out, stats = claw.compress_prompt_text("hello")
            self.assertTrue(stats["skipped"])

    def test_engine_error_returns_original(self) -> None:
        with patch.object(claw, "_get_engine", side_effect=RuntimeError("no engine")):
            out, stats = claw.compress_prompt_text("keep me")
        self.assertEqual(out, "keep me")
        self.assertTrue(stats["skipped"])
        self.assertEqual(stats["reason"], "error")

    def test_happy_path_applied(self) -> None:
        claw._ENGINE = _FakeEngine(compressed="short", reduction_pct=50.0)
        out, stats = claw.compress_prompt_text("a much longer original text", tags={"code"})
        self.assertEqual(out, "short")
        self.assertTrue(stats["applied"])
        self.assertEqual(stats["content_type"], "code")

    def test_below_min_savings_keeps_original(self) -> None:
        claw._ENGINE = _FakeEngine(compressed="slightly shorter", reduction_pct=1.0)
        out, stats = claw.compress_prompt_text("original longer text here")
        self.assertEqual(out, "original longer text here")
        self.assertFalse(stats["applied"])

    def test_unchanged_output(self) -> None:
        same = "identical"
        claw._ENGINE = _FakeEngine(compressed=same, reduction_pct=90.0)
        out, stats = claw.compress_prompt_text(same)
        self.assertEqual(out, same)
        self.assertFalse(stats["applied"])
        self.assertEqual(stats["reason"], "unchanged")


if __name__ == "__main__":
    unittest.main()
