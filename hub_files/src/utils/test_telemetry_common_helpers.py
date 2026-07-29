#!/usr/bin/env python3
"""Coverage for telemetry_common helpers: sources, correlation, tool parsing, IO."""

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


class DetectSourceTests(unittest.TestCase):
    def test_returns_nonempty_string(self) -> None:
        self.assertTrue(tc._detect_source())

    def test_legacy_fallback_claude(self) -> None:
        with patch.dict(sys.modules, {"providers": None}):
            with patch.dict("os.environ", {"CLAUDE_HOME": "/x"}, clear=True):
                with patch("telemetry_paths._path_is_relative_to", return_value=True):
                    self.assertEqual(tc._detect_source(), "claude")

    def test_legacy_fallback_default_cursor(self) -> None:
        with patch.dict(sys.modules, {"providers": None}):
            with patch.dict("os.environ", {}, clear=True):
                self.assertEqual(tc._detect_source(), "cursor")


class ResolveDirTests(unittest.TestCase):
    def test_resolve_log_file_override(self) -> None:
        with patch.dict(
            "os.environ", {"SCROOGE_TOKEN_TELEMETRY_LOG": "/tmp/log.jsonl"}, clear=False
        ):
            self.assertEqual(tc.resolve_log_file(), Path("/tmp/log.jsonl"))

    def test_resolve_skills_dir_hub(self) -> None:
        with patch.dict("os.environ", {"HUB": "/tmp/hub"}, clear=True):
            self.assertEqual(tc.resolve_skills_dir(), Path("/tmp/hub/skills"))

    def test_resolve_skills_dir_default(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            self.assertEqual(tc.resolve_skills_dir(), Path.home() / ".cursor" / "skills")

    def test_resolve_skills_dir_skills_override(self) -> None:
        with patch.dict("os.environ", {"SKILLS_DIR": "/tmp/s"}, clear=True):
            self.assertEqual(tc.resolve_skills_dir(), Path("/tmp/s"))


class TimestampTests(unittest.TestCase):
    def test_utc_ts_format(self) -> None:
        ts = tc.utc_ts()
        self.assertTrue(ts.endswith("Z"))

    def test_parse_ts_seconds(self) -> None:
        self.assertIsNone(tc._parse_ts_seconds(""))
        self.assertIsNone(tc._parse_ts_seconds("not-a-date"))
        self.assertIsInstance(tc._parse_ts_seconds("2026-07-24T10:00:00Z"), float)


class AppendEventTests(unittest.TestCase):
    def test_append_event_writes_line(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "events.jsonl"
            with patch.dict("os.environ", {"SCROOGE_TOKEN_TELEMETRY_LOG": str(log)}, clear=False):
                tc.append_event({"event": "test", "value": 1})
            rows = [json.loads(x) for x in log.read_text().splitlines()]
            self.assertEqual(rows[0]["event"], "test")
            self.assertIn("ts", rows[0])


class CorrelationTests(unittest.TestCase):
    def test_correlation_fields_filters(self) -> None:
        data = {"session_id": "s1", "model": "gpt-4", "other": 123, "empty": "  "}
        out = tc.correlation_fields(data)
        self.assertEqual(out["session_id"], "s1")
        self.assertEqual(out["model"], "gpt-4")
        self.assertNotIn("other", out)
        self.assertNotIn("empty", out)

    def test_enrich_correlation_from_tool_input(self) -> None:
        out = tc.enrich_correlation({}, {"session_id": "s2"})
        self.assertEqual(out["session_id"], "s2")

    def test_enrich_correlation_infers_when_missing(self) -> None:
        with patch.object(tc, "infer_correlation_from_log", return_value={"session_id": "s3"}):
            out = tc.enrich_correlation({}, {})
        self.assertEqual(out["session_id"], "s3")

    def test_infer_correlation_no_log(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(tc, "LOG_FILE", Path(tmp) / "absent.jsonl"):
                self.assertEqual(tc.infer_correlation_from_log(), {})

    def test_infer_correlation_reads_recent_row(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "events.jsonl"
            row = {"ts": tc.utc_ts(), "session_id": "sX", "model": "m"}
            log.write_text(json.dumps(row) + "\n", encoding="utf-8")
            with patch.object(tc, "LOG_FILE", log):
                out = tc.infer_correlation_from_log()
            self.assertEqual(out["session_id"], "sX")


class FieldParsingTests(unittest.TestCase):
    def test_int_field(self) -> None:
        self.assertEqual(tc.int_field({"a": 5}, "a"), 5)
        self.assertEqual(tc.int_field({"a": 2.7}, "a"), 2)
        self.assertIsNone(tc.int_field({"a": True}, "a"))
        self.assertIsNone(tc.int_field({}, "a", "b"))

    def test_extract_tool_label_variants(self) -> None:
        self.assertEqual(tc.extract_tool_label({"tool_name": "Read"}), "Read")
        self.assertEqual(tc.extract_tool_label({"tool": {"name": "Shell"}}), "Shell")
        self.assertEqual(
            tc.extract_tool_label({"tool_calls": [{"function": {"name": "Grep"}}]}), "Grep"
        )
        self.assertEqual(tc.extract_tool_label({}), "")

    def test_tool_output_text(self) -> None:
        self.assertEqual(tc.tool_output_text("hi"), "hi")
        self.assertEqual(tc.tool_output_text({"text": "t"}), "t")
        self.assertIn("k", tc.tool_output_text({"k": "v"}))
        self.assertEqual(tc.tool_output_text(None), "")
        self.assertEqual(tc.tool_output_text(42), "42")

    def test_is_subagent_launch_event(self) -> None:
        self.assertTrue(tc.is_subagent_launch_event("subagentLaunch"))
        self.assertFalse(tc.is_subagent_launch_event("postToolUse"))


class SkillHintTests(unittest.TestCase):
    def test_extract_skill_hint_explicit(self) -> None:
        self.assertEqual(tc.extract_skill_hint("Skill: my-skill"), "my-skill")

    def test_extract_skill_hint_empty(self) -> None:
        self.assertEqual(tc.extract_skill_hint("", "   "), "")

    def test_extract_skill_hint_known_name(self) -> None:
        with patch.object(tc, "_load_known_skills", return_value={"refactor"}):
            self.assertEqual(tc.extract_skill_hint("please refactor this"), "refactor")


class FailSafeTests(unittest.TestCase):
    def test_fail_safe_returns_fallback(self) -> None:
        @tc.fail_safe(fallback_value="safe")
        def boom() -> str:
            raise RuntimeError("x")

        self.assertEqual(boom(), "safe")

    def test_fail_safe_passthrough(self) -> None:
        @tc.fail_safe(fallback_value=None)
        def ok() -> int:
            return 7

        self.assertEqual(ok(), 7)


class EstimateTokensProxyTests(unittest.TestCase):
    def test_proxy_fallback(self) -> None:
        with patch.object(tc, "_get_tiktoken_encoding", return_value=False):
            with patch.object(tc, "_get_claude_tokenizer", return_value=False):
                count, source = tc.estimate_tokens_with_source("abcd efgh", "unknown")
        self.assertEqual(source, "proxy")

    def test_estimate_tokens_wrapper(self) -> None:
        self.assertGreater(tc.estimate_tokens("hello world", "gpt-4"), 0)


if __name__ == "__main__":
    unittest.main()
