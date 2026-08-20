#!/usr/bin/env python3
"""Unit tests for hook_utils.py."""

from __future__ import annotations

import io
import unittest
from pathlib import Path
from unittest.mock import patch

from utils.hook_utils import (
    extract_tool_input,
    extract_tool_name,
    fail_safe,
    hook_fail_safe,
    load_stdin_json,
    resolve_home_path,
)


class HookUtilsTests(unittest.TestCase):
    @patch.dict(
        "os.environ",
        {
            "CLAUDE_HOME": "/dummy/claude",
            "GEMINI_HOME": "",
            "ANTIGRAVITY_HOME": "",
            "HERMES_HOME": "",
            "CODEX_HOME": "",
            "CURSOR_HOME": "",
        },
    )
    def test_resolve_home_path_claude(self):
        self.assertEqual(resolve_home_path(), Path("/dummy/claude").resolve())

    @patch.dict(
        "os.environ",
        {
            "CLAUDE_HOME": "",
            "GEMINI_HOME": "/dummy/gemini",
            "ANTIGRAVITY_HOME": "",
            "HERMES_HOME": "",
            "CODEX_HOME": "",
            "CURSOR_HOME": "",
        },
    )
    def test_resolve_home_path_gemini(self):
        self.assertEqual(resolve_home_path(), Path("/dummy/gemini").resolve())

    @patch.dict(
        "os.environ",
        {
            "CLAUDE_HOME": "",
            "GEMINI_HOME": "",
            "ANTIGRAVITY_HOME": "/dummy/antigravity",
            "HERMES_HOME": "",
            "CODEX_HOME": "",
            "CURSOR_HOME": "",
        },
    )
    def test_resolve_home_path_antigravity(self):
        self.assertEqual(resolve_home_path(), Path("/dummy/antigravity").resolve())

    @patch.dict(
        "os.environ",
        {
            "CLAUDE_HOME": "",
            "GEMINI_HOME": "",
            "ANTIGRAVITY_HOME": "",
            "HERMES_HOME": "",
            "CODEX_HOME": "/dummy/codex",
            "CURSOR_HOME": "",
        },
    )
    def test_resolve_home_path_codex(self):
        self.assertEqual(resolve_home_path(), Path("/dummy/codex").resolve())

    @patch.dict(
        "os.environ",
        {
            "CLAUDE_HOME": "",
            "GEMINI_HOME": "",
            "ANTIGRAVITY_HOME": "",
            "HERMES_HOME": "",
            "CODEX_HOME": "",
            "CURSOR_HOME": "/dummy/cursor",
        },
    )
    def test_resolve_home_path_cursor(self):
        self.assertEqual(resolve_home_path(), Path("/dummy/cursor").resolve())

    @patch.dict("os.environ", {}, clear=True)
    def test_resolve_home_path_fallback(self):
        resolved = resolve_home_path()
        self.assertTrue(isinstance(resolved, Path))

    def test_load_stdin_json_valid(self):
        with patch("sys.stdin", io.StringIO('{"key": "value"}')):
            self.assertEqual(load_stdin_json(), {"key": "value"})

    def test_load_stdin_json_empty(self):
        with patch("sys.stdin", io.StringIO("")):
            self.assertEqual(load_stdin_json(), {})

    def test_load_stdin_json_invalid(self):
        with patch("sys.stdin", io.StringIO("invalid json")):
            self.assertEqual(load_stdin_json(), {"_raw": "invalid json"})

    def test_extract_tool_name_direct(self):
        self.assertEqual(extract_tool_name({"tool_name": "git_grep"}), "git_grep")
        self.assertEqual(extract_tool_name({"toolName": "git_grep"}), "git_grep")
        self.assertEqual(extract_tool_name({"name": "git_grep"}), "git_grep")

    def test_extract_tool_name_nested(self):
        self.assertEqual(extract_tool_name({"tool": {"name": "git_grep"}}), "git_grep")
        self.assertEqual(extract_tool_name({"tool": "git_grep"}), "git_grep")

    def test_extract_tool_name_calls(self):
        data = {"tool_calls": [{"function": {"name": "git_grep"}}]}
        self.assertEqual(extract_tool_name(data), "git_grep")

    def test_extract_tool_input_direct(self):
        self.assertEqual(extract_tool_input({"tool_input": {"path": "foo"}}), {"path": "foo"})
        self.assertEqual(extract_tool_input({"input": {"path": "foo"}}), {"path": "foo"})

    def test_extract_tool_input_nested(self):
        self.assertEqual(extract_tool_input({"tool": {"input": {"path": "foo"}}}), {"path": "foo"})

    def test_fail_safe_decorator(self):
        @fail_safe(fallback_value="safe")
        def buggy_func():
            raise ValueError("boom")

        with patch("sys.stderr", new_callable=io.StringIO) as mock_stderr:
            res = buggy_func()
            self.assertEqual(res, "safe")
            self.assertIn("boom", mock_stderr.getvalue())

    def test_hook_fail_safe_decorator(self):
        @hook_fail_safe(fallback_json='{"err": true}')
        def buggy_main():
            raise RuntimeError("critical")

        with patch("sys.stderr", new_callable=io.StringIO) as mock_stderr:
            with patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
                res = buggy_main()
                self.assertEqual(res, 0)
                self.assertEqual(mock_stdout.getvalue(), '{"err": true}')
                self.assertIn("critical", mock_stderr.getvalue())
