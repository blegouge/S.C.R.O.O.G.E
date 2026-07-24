#!/usr/bin/env python3
"""Tests for the measured-vs-modeled savings taxonomy (P0-2 measurement honesty)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[4]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import measurement_source as ms


class RowHasApiUsageTests(unittest.TestCase):
    def test_billed_total_tokens_is_measured(self) -> None:
        self.assertTrue(ms.row_has_api_usage({"billed_total_tokens": 100}))

    def test_cache_and_io_tokens_are_measured(self) -> None:
        self.assertTrue(ms.row_has_api_usage({"cache_read_tokens": 50}))
        self.assertTrue(ms.row_has_api_usage({"output_tokens": 5}))

    def test_no_usage_fields_is_not_measured(self) -> None:
        self.assertFalse(ms.row_has_api_usage({"approx_tokens": 10}))
        self.assertFalse(ms.row_has_api_usage({}))


class ClassifyGitCacheSourceTests(unittest.TestCase):
    def test_explicit_block2_tokens_is_measured(self) -> None:
        row = {
            "event": "subagentLaunch",
            "compression_git_cache_hit": True,
            "git_cache_block2_tokens_preserved": 800,
        }
        self.assertEqual(ms.classify_git_cache_source(row), ms.MEASURED)

    def test_coefficient_fallback_is_modeled(self) -> None:
        row = {
            "event": "subagentLaunch",
            "compression_git_cache_hit": True,
            "compression_after_tokens": 1000,
        }
        self.assertEqual(ms.classify_git_cache_source(row), ms.MODELED)


class MeasuredVsModeledSavingsTests(unittest.TestCase):
    def test_empty_rows(self) -> None:
        out = ms.measured_vs_modeled_savings([])
        self.assertEqual(out["total_savings_tokens"], 0)
        self.assertEqual(out["measured_pct"], 0.0)

    def test_measured_git_cache_from_api_usage(self) -> None:
        rows = [
            {
                "event": "subagentLaunch",
                "compression_git_cache_hit": True,
                "git_cache_block2_tokens_preserved": 500,
            }
        ]
        out = ms.measured_vs_modeled_savings(rows)
        self.assertEqual(out["measured"]["savings_tokens"], 500)
        self.assertEqual(out["modeled"]["savings_tokens"], 0)
        self.assertEqual(out["measured_pct"], 100.0)

    def test_modeled_diff_only_and_guardrail(self) -> None:
        rows = [
            {"event": "diffOnlyApply", "diff_only_chars_saved": 400},  # -> 100 tokens proxy
            {
                "event": "subagentLaunch",
                "guardrail_intercepted": True,
                "guardrail_avoided_tokens": 300,
            },
        ]
        out = ms.measured_vs_modeled_savings(rows)
        self.assertEqual(out["measured"]["savings_tokens"], 0)
        self.assertEqual(out["modeled"]["savings_tokens"], 400)
        self.assertEqual(out["measured_pct"], 0.0)

    def test_measured_rtk_shell_rewrite(self) -> None:
        rows = [
            {"event": "rtkShellRewrite", "rtk_before_tokens": 1000, "rtk_after_tokens": 200},
        ]
        out = ms.measured_vs_modeled_savings(rows)
        self.assertEqual(out["measured"]["savings_tokens"], 800)
        self.assertEqual(out["measured_pct"], 100.0)

    def test_mixed_measured_and_modeled_ratio(self) -> None:
        rows = [
            {"event": "rtkShellRewrite", "rtk_before_tokens": 700, "rtk_after_tokens": 400},
            {"event": "diffOnlyApply", "diff_only_chars_saved": 400},
        ]
        out = ms.measured_vs_modeled_savings(rows)
        # measured = 300 (rtk), modeled = 100 (diff proxy) -> 300/400 = 75%
        self.assertEqual(out["measured"]["savings_tokens"], 300)
        self.assertEqual(out["modeled"]["savings_tokens"], 100)
        self.assertEqual(out["measured_pct"], 75.0)


if __name__ == "__main__":
    unittest.main()
