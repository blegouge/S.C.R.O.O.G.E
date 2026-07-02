#!/usr/bin/env python3
"""Tests for task brief and consumption report validators."""

from __future__ import annotations

import unittest

from utils.consumption_report_validator import analyze_consumption_report
from utils.task_brief_validator import inject_idempotent_tag, validate_task_brief

GOOD_BRIEF = """
Skill: spec-driven-idempotency
MCP task class: LOCAL_CODE
[MCP_ALLOWLIST]: code-review-graph
[MCP_DENYLIST]: datadog
[CONTEXT]
src/foo.py:10-25
def bar(): ...
[GOALS] Fix bug
[AC]
- Tests pass
"""


class TaskBriefValidatorTests(unittest.TestCase):
    def test_valid_brief(self) -> None:
        result = validate_task_brief(GOOD_BRIEF, subagent_type="generalPurpose")
        self.assertTrue(result.ok)
        self.assertTrue(result.has_context_excerpts)
        tagged = inject_idempotent_tag(GOOD_BRIEF, result)
        self.assertIn("[IDEMPOTENT_CONTEXT_INJECTED]", tagged)

    def test_missing_skill_denied(self) -> None:
        bad = GOOD_BRIEF.replace("Skill: spec-driven-idempotency\n", "")
        result = validate_task_brief(bad, subagent_type="generalPurpose")
        self.assertFalse(result.ok)
        self.assertTrue(any("Skill" in v for v in result.violations))

    def test_explore_allows_rescan(self) -> None:
        explore = """
Skill: functional-domain-mapping
MCP task class: LOCAL_CODE
[MCP_ALLOWLIST]: code-review-graph
RESCAN: allowed — greenfield mapping
[AC]
- Map entry points
"""
        result = validate_task_brief(explore, subagent_type="explore")
        self.assertTrue(result.ok)


class ConsumptionReportValidatorTests(unittest.TestCase):
    def test_complete_report(self) -> None:
        text = """
Answer body.

## Consumption report
- **Work mode**: direct tools only
- **Tool activity**: 3 tool calls
- **Token risk level**: low
- **Main cost drivers**: one read
- **Optimization applied**: rtk grep
- exact token count unavailable in this environment
"""
        status = analyze_consumption_report(text)
        self.assertTrue(status.complete)

    def test_missing_report(self) -> None:
        status = analyze_consumption_report("Just an answer.")
        self.assertFalse(status.complete)
        self.assertFalse(status.present)


if __name__ == "__main__":
    unittest.main()
