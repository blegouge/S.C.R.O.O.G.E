#!/usr/bin/env python3
"""Tests for telemetry metrics calculations and KPI aggregations."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

# Setup path so telemetry_metrics can be imported from local project root
project_root = Path(__file__).resolve().parents[4]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

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

    def test_summarize_report_cache_aware(self) -> None:
        rows = [
            {
                "event": "afterAgentResponse",
                "billed_total_tokens": 1000,
                "input_tokens": 800,
                "output_tokens": 200,
                "cache_read_tokens": 500,
                "cache_write_tokens": 100,
                "ts": "2026-07-07T12:00:00Z",
            },
            {
                "event": "afterAgentResponse",
                "billed_total_tokens": 1500,
                "input_tokens": 1200,
                "output_tokens": 300,
                "cache_read_tokens": 800,
                "cache_write_tokens": 200,
                "ts": "2026-07-07T13:00:00Z",
            },
        ]
        res = telemetry_metrics.summarize_report(rows)
        # Billed totals
        self.assertEqual(res["parent_billed"]["sum"], 2500)
        self.assertEqual(res["parent_billed"]["avg"], 1250)

        # Cache sums
        self.assertEqual(res["parent_billed"]["cache_read_sum"], 1300)
        self.assertEqual(res["parent_billed"]["cache_write_sum"], 300)

        # Adjusted calculations (fallback = 0.1 weight):
        # Row 1: adj_in = (800 - 500) + 500 * 0.1 = 300 + 50 = 350 -> adj_billed = 350 + 200 = 550
        # Row 2: adj_in = (1200 - 800) + 800 * 0.1 = 400 + 80 = 480 -> adj_billed = 480 + 300 = 780
        # Total adjusted_sum = 550 + 780 = 1330
        # Adjusted average = 1330 // 2 = 665
        self.assertEqual(res["parent_billed"]["adjusted_sum"], 1330)
        self.assertEqual(res["parent_billed"]["adjusted_avg"], 665)

        # Latest check: latest is at 13:00:00Z
        self.assertEqual(res["parent_billed"]["latest"], 1500)
        self.assertEqual(res["parent_billed"]["latest_adjusted"], 780)

    def test_summarize_report_cache_aware_openai(self) -> None:
        rows = [
            {
                "event": "afterAgentResponse",
                "billed_total_tokens": 1000,
                "input_tokens": 800,
                "output_tokens": 200,
                "cache_read_tokens": 500,
                "cache_write_tokens": 100,
                "model": "gpt-4o",
                "ts": "2026-07-07T12:00:00Z",
            }
        ]
        res = telemetry_metrics.summarize_report(rows)
        # OpenAI weight = 0.5:
        # adj_in = (800 - 500) + 500 * 0.5 = 300 + 250 = 550 -> adj_billed = 550 + 200 = 750
        self.assertEqual(res["parent_billed"]["adjusted_sum"], 750)
        self.assertEqual(res["parent_billed"]["latest_adjusted"], 750)

    def test_summarize_report_cache_aware_anthropic(self) -> None:
        rows = [
            {
                "event": "afterAgentResponse",
                "billed_total_tokens": 1000,
                "input_tokens": 800,
                "output_tokens": 200,
                "cache_read_tokens": 500,
                "cache_write_tokens": 100,
                "model": "claude-3-5-sonnet",
                "ts": "2026-07-07T12:00:00Z",
            }
        ]
        res = telemetry_metrics.summarize_report(rows)
        # Anthropic weight = 0.1:
        # adj_in = (800 - 500) + 500 * 0.1 = 300 + 50 = 350 -> adj_billed = 350 + 200 = 350 + 200 = 550
        self.assertEqual(res["parent_billed"]["adjusted_sum"], 550)
        self.assertEqual(res["parent_billed"]["latest_adjusted"], 550)

    def test_summarize_report_ab_testing(self) -> None:
        rows = [
            {
                "event": "subagentLaunch",
                "ab_group": "control",
                "compression_input_tokens": 1000,
                "compression_after_tokens": 1000,
            },
            {
                "event": "subagentLaunch",
                "ab_group": "treatment",
                "compression_input_tokens": 2000,
                "compression_after_tokens": 800,
            },
            {
                "event": "subagentLaunch",
                "ab_group": "treatment",
                "compression_input_tokens": 1000,
                "compression_after_tokens": 200,
            }
        ]
        res = telemetry_metrics.summarize_report(rows)
        ab = res.get("ab_test")
        self.assertIsNotNone(ab)
        self.assertEqual(ab["control"]["launches"], 1)
        self.assertEqual(ab["control"]["input_tokens"], 1000)
        self.assertEqual(ab["control"]["after_tokens"], 1000)
        self.assertEqual(ab["control"]["saved_tokens"], 0)

        self.assertEqual(ab["treatment"]["launches"], 2)
        self.assertEqual(ab["treatment"]["input_tokens"], 3000)
        self.assertEqual(ab["treatment"]["after_tokens"], 1000)
        # 3000 - 1000 = 2000
        self.assertEqual(ab["treatment"]["saved_tokens"], 2000)
        self.assertEqual(ab["treatment"]["saved_pct"], 66.67)


if __name__ == "__main__":
    unittest.main()

