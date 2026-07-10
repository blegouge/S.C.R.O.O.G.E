#!/usr/bin/env python3
"""Tests for telemetry_common token estimation and tokenizer routing."""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

# Setup path so telemetry_common can be imported from local project root
project_root = Path(__file__).resolve().parents[4]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import telemetry_common


class TelemetryCommonTokenTests(unittest.TestCase):
    def test_estimate_tokens_empty(self) -> None:
        self.assertEqual(telemetry_common.estimate_tokens(""), 0)
        self.assertEqual(telemetry_common.estimate_tokens_with_source("")[0], 0)

    def test_estimate_tokens_tiktoken_openai(self) -> None:
        # GPT-4 / GPT-3.5 models should use cl100k_base
        count, source = telemetry_common.estimate_tokens_with_source("Hello world!", "gpt-4")
        self.assertEqual(source, "tokenizer")
        # cl100k_base for "Hello world!" is 3 tokens
        self.assertEqual(count, 3)

        # GPT-4o / o1 models should use o200k_base
        count_4o, source_4o = telemetry_common.estimate_tokens_with_source("Hello world!", "gpt-4o")
        self.assertEqual(source_4o, "tokenizer")
        # o200k_base for "Hello world!" is 3 tokens
        self.assertEqual(count_4o, 3)

    def test_estimate_tokens_claude_tokenizer(self) -> None:
        # Claude models should use Claude tokenizer from file
        count, source = telemetry_common.estimate_tokens_with_source("Hello world!", "claude-3-5-sonnet")
        # Since tokenizer.json is present in dev context, it should load and return 3 tokens
        self.assertEqual(source, "tokenizer")
        self.assertEqual(count, 3)

    def test_estimate_tokens_claude_fallback_when_file_missing(self) -> None:
        # Mock _resolve_claude_tokenizer_path to return None to simulate missing file
        with patch("telemetry_common._resolve_claude_tokenizer_path", return_value=None):
            # Temporarily clear cached _claude_tokenizer
            with patch("telemetry_common._claude_tokenizer", None):
                count, source = telemetry_common.estimate_tokens_with_source("Hello world!", "claude-3-5-sonnet")
                # Should fallback to tiktoken (which is a tokenizer)
                self.assertEqual(source, "tokenizer")
                self.assertEqual(count, 3)

    def test_estimate_tokens_fallback_to_proxy(self) -> None:
        # Mock _get_tiktoken_encoding and _get_claude_tokenizer to return False/None
        with patch("telemetry_common._get_tiktoken_encoding", return_value=False):
            with patch("telemetry_common._get_claude_tokenizer", return_value=False):
                count, source = telemetry_common.estimate_tokens_with_source("Hello world!", "unknown-model")
                self.assertEqual(source, "proxy")
                # "Hello world!" length is 12. (12 + 3) // 4 = 3
                self.assertEqual(count, 3)


if __name__ == "__main__":
    unittest.main()
