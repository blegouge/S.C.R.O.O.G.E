#!/usr/bin/env python3
"""Tests for compliance KPI aggregation."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

# Setup path so telemetry_metrics can be imported from local project root
project_root = Path(__file__).resolve().parents[4]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from telemetry_metrics import summarize_compliance_kpis  # noqa: E402


class ComplianceMetricsTests(unittest.TestCase):
    def test_consumption_and_brief_rates(self) -> None:
        rows = [
            {
                "event": "afterAgentResponse",
                "consumption_present": True,
                "consumption_complete": True,
            },
            {
                "event": "afterAgentResponse",
                "consumption_present": True,
                "consumption_complete": False,
            },
            {"event": "subagentLaunch", "idempotent_context_injected": True},
            {"event": "taskBriefValidation", "brief_valid": False},
            {
                "event": "consumptionReportCompliance",
                "consumption_enforced": True,
                "consumption_complete": False,
                "loop_count": 0,
            },
        ]
        comp = summarize_compliance_kpis(rows)
        self.assertEqual(comp["consumption"]["responses"], 2)
        self.assertEqual(comp["consumption"]["complete"], 1)
        self.assertEqual(comp["consumption"]["complete_pct"], 50)
        self.assertEqual(comp["task_brief"]["denied"], 1)
        self.assertEqual(comp["task_brief"]["launches"], 1)
        self.assertEqual(comp["task_brief"]["pass_rate_pct"], 50)
        self.assertEqual(comp["consumption"]["hook_followups"], 1)


if __name__ == "__main__":
    unittest.main()
