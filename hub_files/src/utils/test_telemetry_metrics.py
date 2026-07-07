#!/usr/bin/env python3
"""Tests for telemetry metrics calculations and KPI aggregations."""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

# Setup path so telemetry_metrics can be imported
_HOME_DIR = os.getenv("CODEX_HOME") or os.getenv("ANTIGRAVITY_HOME") or os.getenv("CURSOR_HOME")
if _HOME_DIR:
    _HOME_PATH = Path(_HOME_DIR).resolve()
else:
    _HOME_PATH = Path(__file__).resolve().parent.parent.parent
TELEMETRY_DIR = _HOME_PATH / "token-telemetry"
if str(TELEMETRY_DIR) not in sys.path:
    sys.path.insert(0, str(TELEMETRY_DIR))

# Import the metrics functions to test
import telemetry_metrics


class TelemetryMetricsTests(unittest.TestCase):
    def test_is_subagent_stop(self) -> None:
        self.assertTrue(telemetry_metrics.is_subagent_stop({"event": "subagentStop"}))
        self.assertFalse(telemetry_metrics.is_subagent_stop({"event": "subagentLaunch"}))
        self.assertFalse(telemetry_metrics.is_subagent_stop({}))

    def test_subagent_stop_breakdown(self) -> None:
        rows = [
            {"event": "subagentStop", "subagent_stop_source": "hook"},
            {"event": "subagentStop", "subagent_stop_source": "postToolUse_fallback"},
            {"event": "subagentStop"},  # unknown source
            {"event": "subagentLaunch"},  # not a stop
        ]
        breakdown = telemetry_metrics.subagent_stop_breakdown(rows)
        self.assertEqual(breakdown["stop_total"], 3)
        self.assertEqual(breakdown["stop_hook"], 1)
        self.assertEqual(breakdown["stop_post_tool_fallback"], 1)
        self.assertEqual(breakdown["stop_unknown_source"], 1)

    def test_hook_saved_tokens(self) -> None:
        # If input_tokens is present
        self.assertEqual(
            telemetry_metrics.hook_saved_tokens(
                {
                    "compression_saved_tokens": 100,
                    "compression_input_tokens": 500,
                    "compression_after_tokens": 300,
                }
            ),
            200,  # max(100, 500 - 300) = 200
        )
        # If legacy is larger
        self.assertEqual(
            telemetry_metrics.hook_saved_tokens(
                {
                    "compression_saved_tokens": 300,
                    "compression_input_tokens": 500,
                    "compression_after_tokens": 300,
                }
            ),
            300,
        )
        # If input_tokens is not present
        self.assertEqual(
            telemetry_metrics.hook_saved_tokens({"compression_saved_tokens": 120}),
            120,
        )

    def test_hook_overhead_tokens(self) -> None:
        # Explicit overhead
        self.assertEqual(
            telemetry_metrics.hook_overhead_tokens({"compression_overhead_tokens": 50}),
            50,
        )
        # Calculated overhead
        self.assertEqual(
            telemetry_metrics.hook_overhead_tokens(
                {
                    "compression_input_tokens": 100,
                    "compression_after_tokens": 130,
                }
            ),
            30,
        )
        # No overhead
        self.assertEqual(
            telemetry_metrics.hook_overhead_tokens(
                {
                    "compression_input_tokens": 200,
                    "compression_after_tokens": 150,
                }
            ),
            0,
        )

    def test_row_git_cache_hit(self) -> None:
        self.assertTrue(telemetry_metrics.row_git_cache_hit({"compression_git_cache_hit": True}))
        self.assertTrue(telemetry_metrics.row_git_cache_hit({"git_cache_hit": True}))
        self.assertFalse(telemetry_metrics.row_git_cache_hit({"git_cache_hit": False}))
        self.assertFalse(telemetry_metrics.row_git_cache_hit({}))

    def test_row_git_cache_tokens_preserved(self) -> None:
        # Explicit key 1
        self.assertEqual(
            telemetry_metrics.row_git_cache_tokens_preserved(
                {"git_cache_block2_tokens_preserved": 150}
            ),
            150,
        )
        # Explicit key 2
        self.assertEqual(
            telemetry_metrics.row_git_cache_tokens_preserved(
                {"compression_block2_tokens_preserved": 250}
            ),
            250,
        )
        # Heuristic when git cache hit
        self.assertEqual(
            telemetry_metrics.row_git_cache_tokens_preserved(
                {
                    "git_cache_hit": True,
                    "compression_after_tokens": 1000,
                }
            ),
            120,  # 1000 * 0.12 = 120
        )
        # Not a hit
        self.assertEqual(
            telemetry_metrics.row_git_cache_tokens_preserved(
                {
                    "git_cache_hit": False,
                    "compression_after_tokens": 1000,
                }
            ),
            0,
        )

    def test_row_guardrail_loop_halt(self) -> None:
        self.assertTrue(telemetry_metrics.row_guardrail_loop_halt({"guardrail_loop_halt": True}))
        self.assertFalse(telemetry_metrics.row_guardrail_loop_halt({}))

    def test_row_guardrail_intercepted(self) -> None:
        self.assertTrue(
            telemetry_metrics.row_guardrail_intercepted({"guardrail_intercepted": True})
        )
        self.assertTrue(telemetry_metrics.row_guardrail_intercepted({"guardrail_loop_halt": True}))
        self.assertTrue(
            telemetry_metrics.row_guardrail_intercepted(
                {
                    "guardrail_roi_gate": True,
                    "guardrail_risk": "high",
                }
            )
        )
        self.assertFalse(
            telemetry_metrics.row_guardrail_intercepted(
                {
                    "guardrail_roi_gate": True,
                    "guardrail_risk": "low",
                }
            )
        )
        self.assertFalse(telemetry_metrics.row_guardrail_intercepted({}))

    def test_row_guardrail_avoided_tokens(self) -> None:
        # Explicit
        self.assertEqual(
            telemetry_metrics.row_guardrail_avoided_tokens({"guardrail_avoided_tokens": 500}),
            500,
        )
        # Avoided due to loop halt
        self.assertEqual(
            telemetry_metrics.row_guardrail_avoided_tokens(
                {
                    "guardrail_loop_halt": True,
                    "compression_input_tokens": 100,
                    "compression_after_tokens": 50,
                    "guardrail_failure_streak": 2,
                }
            ),
            2
            * (100 + max(50, 100 // 3)),  # cycles = max(1, 4 - 2) = 2. output: 2 * (100 + 50) = 300
        )
        # Avoided due to other intercept (e.g. ROI gate)
        self.assertEqual(
            telemetry_metrics.row_guardrail_avoided_tokens(
                {
                    "guardrail_intercepted": True,
                    "compression_input_tokens": 1000,
                    "compression_after_tokens": 400,
                }
            ),
            int(1000 * 0.35 + max(400, 1000 // 4)),  # 350 + max(400, 250) = 350 + 400 = 750
        )
        # Not intercepted
        self.assertEqual(
            telemetry_metrics.row_guardrail_avoided_tokens(
                {
                    "compression_input_tokens": 1000,
                    "compression_after_tokens": 400,
                }
            ),
            0,
        )

    def test_summarize_report_empty(self) -> None:
        res = telemetry_metrics.summarize_report([])
        self.assertEqual(res["event_count"], 0)
        self.assertEqual(res["edit"]["passes"], 0)
        self.assertEqual(res["subagents"]["launch"], 0)

    def test_summarize_report_full(self) -> None:
        rows = [
            {
                "event": "afterFileEdit",
                "lines_added": 10,
                "lines_removed": 5,
            },
            {
                "event": "afterTabFileEdit",
                "lines_added": 8,
            },
            {
                "event": "afterAgentResponse",
                "consumption_present": True,
                "consumption_complete": True,
                "billed_total_tokens": 120,
                "input_tokens": 80,
                "output_tokens": 40,
                "ts": "2026-07-07T12:00:00Z",
            },
            {
                "event": "subagentLaunch",
                "compression_used_claw_compactor": True,
                "compression_after_tokens": 100,
            },
            {
                "event": "subagentStop",
                "approx_tokens": 50,
                "subagent_stop_source": "hook",
            },
        ]
        res = telemetry_metrics.summarize_report(rows)
        self.assertEqual(res["event_count"], 5)
        self.assertEqual(res["edit"]["lines_added"], 10)
        self.assertEqual(res["edit"]["lines_removed"], 5)
        self.assertEqual(res["edit"]["tab_accepted"], 1)
        self.assertEqual(res["edit"]["tab_lines_added"], 8)
        self.assertEqual(res["consumption_coverage"]["complete"], 1)
        self.assertEqual(res["parent_billed"]["latest"], 120)
        self.assertEqual(res["parent_billed"]["latest_input"], 80)
        self.assertEqual(res["parent_billed"]["latest_output"], 40)
        self.assertEqual(res["hook_compression"]["runs"], 1)
        self.assertEqual(res["subagents"]["launch"], 1)
        self.assertEqual(res["subagents"]["stop"], 1)
        self.assertEqual(res["subagents"]["prompt_proxy_tokens"], 100)
        self.assertEqual(res["subagents"]["out_proxy_tokens"], 50)


if __name__ == "__main__":
    unittest.main()
