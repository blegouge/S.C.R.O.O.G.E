#!/usr/bin/env python3
"""
Benchmark and quality test suite for Key-Value summarizers.
Verifies that critical constraints, active branches, and pending items
are correctly preserved during conversation history compaction.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
for sub in ["src/telemetry", "src/compaction", "src/bridge", "hub_files/src"]:
    p = PROJECT_ROOT / sub
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from flash_kv_summarizer import hybrid_kv_summarizer

from utils.adaptive_context_manager import local_kv_summarizer


class KVSummarizerQualityBenchmark(unittest.TestCase):
    def test_structured_metadata_preservation(self) -> None:
        """Verify that structured metadata (key-value pairs) are fully preserved."""
        raw_context = (
            "Here is the developer metadata for this session:\n"
            "- Active_Branch: feature/P2-agent-optim\n"
            "- Blocker: None\n"
            "- DB_Port: 5432\n"
            "- Codebase_Path: /app/private/src\n"
        )

        # Test local_kv_summarizer
        local_res = local_kv_summarizer(raw_context)
        self.assertEqual(local_res.get("Active_Branch"), "feature/P2-agent-optim")
        self.assertEqual(local_res.get("DB_Port"), "5432")
        self.assertEqual(local_res.get("Codebase_Path"), "/app/private/src")
        self.assertEqual(local_res.get("Blocker"), "None")

        # Test hybrid_kv_summarizer (which falls back to local when no LLM provider is active)
        hybrid_res = hybrid_kv_summarizer(raw_context)
        self.assertEqual(hybrid_res.get("Active_Branch"), "feature/P2-agent-optim")

    def test_unstructured_conversation_focus_and_constraints(self) -> None:
        """Verify fallback behavior on unstructured dialogue preserves focus and constraints."""
        raw_dialogue = (
            "We need to implement the secure authentication flow immediately. "
            "Please ensure that the JWT expiration token is set to exactly 15 minutes. "
            "Also we need to clean up the test suite and verify the coverage."
        )

        local_res = local_kv_summarizer(raw_dialogue)

        # First sentence is conversation focus
        self.assertIn("secure authentication flow", local_res.get("Conversation_Focus", ""))

        # Second sentence is the latest constraint
        self.assertIn("JWT expiration token", local_res.get("Latest_Constraint", ""))

        # Last sentence is the pending item
        self.assertIn("clean up the test suite", local_res.get("Pending_Item", ""))

    def test_value_length_safety_limit(self) -> None:
        """Verify that extracted values never exceed the 240-character safety limit."""
        long_value = "X" * 300
        raw_context = f"- Critical_Instruction: {long_value}\n"

        local_res = local_kv_summarizer(raw_context)
        val = local_res.get("Critical_Instruction", "")
        self.assertTrue(len(val) <= 240)
        self.assertTrue(val.startswith("X" * 200))


if __name__ == "__main__":
    unittest.main()
