#!/usr/bin/env python3
"""Verify rules ↔ skills SSOT pairs (stub references canonical file)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

import os
CURSOR_HOME = Path(os.getenv("ANTIGRAVITY_HOME") or os.getenv("CURSOR_HOME") or Path.home() / ".cursor")

SSOT_PAIRS = [
    ("token-budget-guardrail.mdc", "skills/token-budget-guardrail/SKILL.md"),
    ("code-review-graph.mdc", "skills/code-review-graph/SKILL.md"),
    ("diff-only-protocol.mdc", "src/rules/diff_protocol.md"),
    ("subagent-skill-routing.mdc", "src/rules/skills_routing.md"),
]


class SsotPairsTests(unittest.TestCase):
    def test_stub_references_canonical(self) -> None:
        for rule_name, canonical in SSOT_PAIRS:
            rule_path = CURSOR_HOME / "rules" / rule_name
            canon_path = CURSOR_HOME / canonical
            self.assertTrue(rule_path.is_file(), f"missing rule: {rule_name}")
            self.assertTrue(canon_path.is_file(), f"missing canonical: {canonical}")
            body = rule_path.read_text(encoding="utf-8")
            self.assertIn(canonical, body, f"{rule_name} must reference {canonical}")

    def test_routing_catalog_lists_core_skills(self) -> None:
        catalog = (CURSOR_HOME / "src/rules/skills_routing.md").read_text(encoding="utf-8")
        for skill in ("spec-driven-idempotency", "subagent-playbook"):
            self.assertIn(f"`{skill}`", catalog)


if __name__ == "__main__":
    unittest.main()
