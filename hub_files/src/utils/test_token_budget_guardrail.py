#!/usr/bin/env python3
"""Tests for token budget guardrail."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

local_src = Path(__file__).resolve().parents[2]
if str(local_src) not in sys.path:
    sys.path.insert(0, str(local_src))

from utils.token_budget_guardrail import (
    analyze_guardrail_launch,
    build_upstream_guardrail_report,
)


class TokenBudgetGuardrailTests(unittest.TestCase):
    def test_build_upstream_report_basic(self) -> None:
        report = build_upstream_guardrail_report(
            subagent_type="generalpurpose",
            prompt="Hello World",
            description="Testing guardrails",
        )
        self.assertIn("[TOKEN_BUDGET_GUARDRAIL_REPORT]", report)
        self.assertIn("subagent_type=generalpurpose", report)
        self.assertIn("prompt_tokens_est=", report)
        self.assertIn(
            "risk=medium", report
        )  # generalpurpose mentions large read is false but type is generalpurpose

    def test_build_upstream_report_halt(self) -> None:
        report = build_upstream_guardrail_report(
            subagent_type="explore",
            prompt="Read whole codebase",
            description="Testing loop halt",
            tool_input={
                "guardrail_state": {"failure_streak": 2, "last_failure_kind": "infinite_loop"}
            },
        )
        self.assertIn("loop_halt_active=yes", report)
        self.assertIn("risk=high", report)
        self.assertIn("last_failure_kind=infinite_loop", report)

    def test_analyze_guardrail_launch_low_risk(self) -> None:
        telemetry = analyze_guardrail_launch(
            subagent_type="writer",
            prompt="Short text",
            description="Writing a summary",
            after_tokens=10,
        )
        self.assertFalse(telemetry["guardrail_intercepted"])
        self.assertFalse(telemetry["guardrail_loop_halt"])
        self.assertEqual(telemetry["guardrail_risk"], "low")

    def test_analyze_guardrail_launch_high_risk_halt(self) -> None:
        telemetry = analyze_guardrail_launch(
            subagent_type="explore",
            prompt="Large read of a file",
            description="Testing guardrails",
            tool_input={"guardrail_state": {"failure_streak": 3}},
            after_tokens=100,
        )
        self.assertTrue(telemetry["guardrail_intercepted"])
        self.assertTrue(telemetry["guardrail_loop_halt"])
        self.assertEqual(telemetry["guardrail_risk"], "high")
        self.assertGreater(telemetry["guardrail_avoided_tokens"], 0)
