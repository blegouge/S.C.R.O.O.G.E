#!/usr/bin/env python3
"""Tests for telemetry_common tool label and Task output parsing."""

from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

CURSOR_HOME = Path(os.environ.get("CURSOR_HOME", Path.home() / ".cursor"))
TELEMETRY_DIR = CURSOR_HOME / "token-telemetry"
SRC_DIR = CURSOR_HOME / "src"
for path in (TELEMETRY_DIR, SRC_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from telemetry_common import extract_tool_label, tool_output_text  # noqa: E402


class TelemetryCommonTests(unittest.TestCase):
    def test_extract_tool_label_tool_name(self) -> None:
        data = {"tool_name": "Task", "tool_input": {"prompt": "x"}}
        self.assertEqual(extract_tool_label(data), "Task")

    def test_extract_tool_label_legacy_tool(self) -> None:
        data = {"tool": "Shell"}
        self.assertEqual(extract_tool_label(data), "Shell")

    def test_tool_output_text_string(self) -> None:
        self.assertEqual(tool_output_text("hello"), "hello")

    def test_tool_output_text_dict(self) -> None:
        self.assertIn("ok", tool_output_text({"text": "ok"}))


class TokenTelemetrySubagentStopTests(unittest.TestCase):
    def test_post_tool_use_task_emits_subagent_stop_fallback(self) -> None:
        hooks_dir = CURSOR_HOME / "hooks"
        sys.path.insert(0, str(hooks_dir))
        # Import module under test by path
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "token_telemetry_hook", hooks_dir / "token-telemetry.py"
        )
        assert spec and spec.loader
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        payload = {
            "tool_name": "Task",
            "tool_input": {
                "subagent_type": "explore",
                "description": "map module",
                "prompt": "Skill: functional-domain-mapping\n[AC]\n- done",
            },
            "tool_output": "Found 3 entry points in src/",
            "duration": 4200,
            "session_id": "sess-test",
            "conversation_id": "conv-test",
        }
        with patch.dict(os.environ, {"CURSOR_TT_EVENT": "postToolUse"}):
            with patch.object(mod, "append_event") as mock_append:
                with patch("sys.stdin", open(os.devnull)):
                    # Call _build_row directly
                    row = mod._build_row("postToolUse", json.dumps(payload), payload)

        self.assertEqual(row["event"], "subagentStop")
        self.assertEqual(row["subagent_stop_source"], "postToolUse_fallback")
        self.assertEqual(row["subagent_type"], "explore")
        self.assertGreater(row["subagent_summary_chars"], 0)


if __name__ == "__main__":
    unittest.main()
