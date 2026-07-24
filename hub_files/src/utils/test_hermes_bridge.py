#!/usr/bin/env python3
"""Tests for hermes_telemetry_bridge parsing, normalization and emission."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[4]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import hermes_telemetry_bridge as bridge


class ParsingTests(unittest.TestCase):
    def test_parse_int_variants(self) -> None:
        self.assertEqual(bridge._parse_int(5), 5)
        self.assertEqual(bridge._parse_int(5.9), 5)
        self.assertEqual(bridge._parse_int("1,234"), 1234)
        self.assertEqual(bridge._parse_int(""), 0)
        self.assertEqual(bridge._parse_int("bad"), 0)
        self.assertEqual(bridge._parse_int(None), 0)

    def test_estimate_tokens_from_text_token_pattern(self) -> None:
        self.assertEqual(bridge._estimate_tokens_from_text("saved 1,500 tokens"), 1500)

    def test_estimate_tokens_from_text_size_pattern(self) -> None:
        self.assertEqual(bridge._estimate_tokens_from_text("payload 400 bytes"), 100)

    def test_estimate_tokens_from_text_empty(self) -> None:
        self.assertEqual(bridge._estimate_tokens_from_text(""), 0)

    def test_estimate_tokens_from_text_falls_back_to_estimator(self) -> None:
        # No token/size pattern -> uses estimate_tokens (real tokenizer).
        self.assertGreater(bridge._estimate_tokens_from_text("hello world"), 0)


class NormalizationTests(unittest.TestCase):
    def test_missing_event_returns_none(self) -> None:
        self.assertIsNone(bridge._normalize_hermes_event({}))

    def test_subagent_stop(self) -> None:
        out = bridge._normalize_hermes_event(
            {"event": "subagent_stop", "summary": "300 tokens saved", "session_id": "s1"}
        )
        self.assertEqual(out["source"], "hermes")
        self.assertEqual(out["event"], "subagent_stop")
        self.assertEqual(out["approx_tokens"], 300)
        self.assertEqual(out["subagent_status"], "completed")
        self.assertEqual(out["session_id"], "s1")

    def test_after_agent_response(self) -> None:
        out = bridge._normalize_hermes_event({"event": "after_agent_response", "text_len": "800"})
        self.assertEqual(out["approx_tokens"], 200)
        self.assertEqual(out["text_chars"], 800)

    def test_post_tool_use(self) -> None:
        out = bridge._normalize_hermes_event({"event": "post_tool_use", "output_len": 40})
        self.assertEqual(out["approx_tokens"], 10)

    def test_launch_family(self) -> None:
        out = bridge._normalize_hermes_event({"event": "subagent_launch", "text_len": 4})
        self.assertEqual(out["approx_tokens"], 1)

    def test_unknown_event_generic_branch(self) -> None:
        out = bridge._normalize_hermes_event({"event": "custom_thing", "text_len": 0})
        self.assertEqual(out["approx_tokens"], 0)


class EmitEventsTests(unittest.TestCase):
    def test_no_input_when_log_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            missing = Path(tmp) / "missing.log"
            target = Path(tmp) / "events.jsonl"
            with patch.object(bridge, "HERMES_LOG", missing):
                result = bridge.emit_events(target=target)
            self.assertTrue(result["ok"])
            self.assertEqual(result["mode"], "no-input")

    def test_emit_events_writes_normalized_rows(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "compression.log"
            target = Path(tmp) / "events.jsonl"
            lines = [
                json.dumps({"event": "post_tool_use", "output_len": 40}),
                "not-json",
                json.dumps({"event": "subagent_stop", "summary": "10 tokens"}),
                json.dumps([1, 2, 3]),  # not a dict -> skipped
            ]
            log.write_text("\n".join(lines) + "\n", encoding="utf-8")
            with patch.object(bridge, "HERMES_LOG", log):
                result = bridge.emit_events(target=target)
            self.assertTrue(result["ok"])
            self.assertEqual(result["emitted"], 2)
            emitted = [json.loads(x) for x in target.read_text().splitlines()]
            self.assertEqual({e["event"] for e in emitted}, {"post_tool_use", "subagent_stop"})

    def test_already_emitted_dedupes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "events.jsonl"
            payload = json.dumps({"source": "hermes", "event": "x"}, ensure_ascii=False)
            target.write_text(payload + "\n", encoding="utf-8")
            self.assertTrue(bridge._already_emitted(target, payload))
            self.assertFalse(bridge._already_emitted(target, "other"))
            self.assertFalse(bridge._already_emitted(Path(tmp) / "none", payload))


if __name__ == "__main__":
    unittest.main()
