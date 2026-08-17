#!/usr/bin/env python3
"""Tests for OTEL-shaped span context on telemetry events."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[3]
for sub in ["src/telemetry", "src/compaction", "src/bridge", "hub_files/src"]:
    p = PROJECT_ROOT / sub
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import telemetry_common as tc

import telemetry_db as db


class SpanContextTests(unittest.TestCase):
    def test_new_ids_shape(self) -> None:
        self.assertEqual(len(tc.new_trace_id()), 32)
        self.assertEqual(len(tc.new_span_id()), 16)
        self.assertTrue(int(tc.new_trace_id(), 16) >= 0)
        self.assertTrue(int(tc.new_span_id(), 16) >= 0)

    def test_turn_hierarchy_and_duration(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "events.jsonl"
            env = {"SCROOGE_TOKEN_TELEMETRY_LOG": str(log), "SCROOGE_SPAN_CONTEXT": "1"}
            with patch.dict("os.environ", env, clear=False):
                tc.append_event(
                    {
                        "event": "userPromptSubmit",
                        "conversation_id": "c1",
                        "ts": "2026-08-17T10:00:00Z",
                    }
                )
                tc.append_event(
                    {
                        "event": "postToolUse",
                        "tool": "Read",
                        "conversation_id": "c1",
                        "ts": "2026-08-17T10:00:01Z",
                    }
                )
                tc.append_event(
                    {
                        "event": "postToolUse",
                        "tool": "Task",
                        "conversation_id": "c1",
                        "ts": "2026-08-17T10:00:02Z",
                    }
                )
                tc.append_event(
                    {
                        "event": "subagentStop",
                        "tool": "Task",
                        "conversation_id": "c1",
                        "ts": "2026-08-17T10:00:05Z",
                        "task_duration_ms": 2500,
                    }
                )
                tc.append_event(
                    {
                        "event": "afterAgentResponse",
                        "conversation_id": "c1",
                        "ts": "2026-08-17T10:00:10Z",
                    }
                )

            rows = [json.loads(line) for line in log.read_text().splitlines()]
            self.assertEqual(len(rows), 5)

            prompt, tool, task, stop, resp = rows
            self.assertEqual(prompt["parent_span_id"], "")
            self.assertEqual(tool["parent_span_id"], prompt["span_id"])
            self.assertEqual(task["parent_span_id"], prompt["span_id"])
            self.assertEqual(stop["parent_span_id"], task["span_id"])
            self.assertEqual(resp["parent_span_id"], prompt["span_id"])

            trace_ids = {r["trace_id"] for r in rows}
            self.assertEqual(len(trace_ids), 1)
            self.assertEqual(len(next(iter(trace_ids))), 32)

            self.assertEqual(stop["duration_ms"], 2500)
            self.assertEqual(resp["duration_ms"], 10000)

            state_path = log.parent / "span_state.json"
            self.assertTrue(state_path.is_file())
            state = json.loads(state_path.read_text())
            self.assertEqual(state.get("turn_span_id"), "")

    def test_span_context_can_be_disabled(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "events.jsonl"
            env = {"SCROOGE_TOKEN_TELEMETRY_LOG": str(log), "SCROOGE_SPAN_CONTEXT": "0"}
            with patch.dict("os.environ", env, clear=False):
                tc.append_event({"event": "postToolUse", "tool": "Grep"})
            row = json.loads(log.read_text().splitlines()[0])
            self.assertNotIn("trace_id", row)
            self.assertNotIn("span_id", row)

    def test_preserves_explicit_ids(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "events.jsonl"
            env = {"SCROOGE_TOKEN_TELEMETRY_LOG": str(log), "SCROOGE_SPAN_CONTEXT": "1"}
            with patch.dict("os.environ", env, clear=False):
                tc.append_event(
                    {
                        "event": "userPromptSubmit",
                        "conversation_id": "c2",
                        "trace_id": "a" * 32,
                        "span_id": "b" * 16,
                        "parent_span_id": "",
                    }
                )
            row = json.loads(log.read_text().splitlines()[0])
            self.assertEqual(row["trace_id"], "a" * 32)
            self.assertEqual(row["span_id"], "b" * 16)
            self.assertEqual(row["parent_span_id"], "")


class SpanPersistenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / "t.db"
        self._orig = db.get_db_path
        db.get_db_path = lambda: self.db_path

    def tearDown(self) -> None:
        db.get_db_path = self._orig
        self.tmp.cleanup()

    def _write_turn(self, log: Path) -> None:
        env = {"SCROOGE_TOKEN_TELEMETRY_LOG": str(log), "SCROOGE_SPAN_CONTEXT": "1"}
        with patch.dict("os.environ", env, clear=False):
            tc.append_event(
                {"event": "userPromptSubmit", "session_id": "s9", "ts": "2026-08-17T09:00:00Z"}
            )
            tc.append_event(
                {
                    "event": "postToolUse",
                    "tool": "Task",
                    "session_id": "s9",
                    "ts": "2026-08-17T09:00:01Z",
                }
            )
            tc.append_event(
                {
                    "event": "subagentStop",
                    "tool": "Task",
                    "session_id": "s9",
                    "ts": "2026-08-17T09:00:04Z",
                    "task_duration_ms": 3000,
                }
            )
            tc.append_event(
                {"event": "afterAgentResponse", "session_id": "s9", "ts": "2026-08-17T09:00:08Z"}
            )

    def test_spans_are_queryable_from_sqlite(self) -> None:
        log = Path(self.tmp.name) / "events.jsonl"
        self._write_turn(log)
        self.assertEqual(db.sync_source("cursor", log), 4)

        traces = db.fetch_recent_traces(limit=10)
        self.assertEqual(len(traces), 1)
        self.assertEqual(traces[0]["spans"], 4)
        self.assertEqual(len(traces[0]["trace_id"]), 32)

        spans = db.fetch_trace_spans(traces[0]["trace_id"])
        self.assertEqual([s["event"] for s in spans][0], "userPromptSubmit")
        root = spans[0]
        task = next(s for s in spans if s["event"] == "postToolUse")
        stop = next(s for s in spans if s["event"] == "subagentStop")
        self.assertEqual(root["parent_span_id"], "")
        self.assertEqual(task["parent_span_id"], root["span_id"])
        self.assertEqual(stop["parent_span_id"], task["span_id"])
        self.assertEqual(stop["duration_ms"], 3000)
        self.assertEqual(task["tool"], "Task")

    def test_unknown_trace_returns_empty(self) -> None:
        log = Path(self.tmp.name) / "events.jsonl"
        self._write_turn(log)
        db.sync_source("cursor", log)
        self.assertEqual(db.fetch_trace_spans("f" * 32), [])


if __name__ == "__main__":
    unittest.main()
