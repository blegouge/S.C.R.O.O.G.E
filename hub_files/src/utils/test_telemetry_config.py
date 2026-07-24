#!/usr/bin/env python3
"""Unit tests for the ConfigManager class."""

from __future__ import annotations

import os

# Add project root to sys.path
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from telemetry_config import ConfigManager


class TelemetryConfigTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.cursor_home = Path(self.temp_dir.name)

        # Save environment variables
        self.original_env = dict(os.environ)

        # Mock load_telemetry_env to prevent loading development .env
        from unittest.mock import patch

        self.patcher = patch("telemetry_paths.load_telemetry_env")
        self.mock_load_env = self.patcher.start()

        # Clean config environment variables to ensure test isolation
        config_keys = [
            "COMPRESSION_BACKEND",
            "TASK_BRIEF_ENFORCE",
            "LLMLINGUA_HOOK_RATE",
            "LLMLINGUA_HOOK_MIN_CHARS",
            "ADAPTIVE_CTX_TOKEN_THRESHOLD",
            "ADAPTIVE_CTX_MESSAGE_THRESHOLD",
            "ADAPTIVE_CTX_STRUCTURE_MIN_INPUT_TOKENS",
            "CCR_ENABLED",
            "CCR_THRESHOLD_CHARS",
            "SMART_CRUSHER_N",
            "SMART_CRUSHER_M",
            "LLMLINGUA_BLOCKING_INIT",
            "CURSOR_TOKEN_TELEMETRY_DATA_DIR",
            "CURSOR_TOKEN_TELEMETRY_LOG",
        ]
        for key in config_keys:
            os.environ.pop(key, None)

    def tearDown(self) -> None:
        self.patcher.stop()
        self.temp_dir.cleanup()
        # Restore environment variables
        os.environ.clear()
        os.environ.update(self.original_env)

    def test_default_values(self) -> None:
        # Create empty environment/config
        config = ConfigManager(cursor_home=self.cursor_home)
        self.assertEqual(config.compression_backend, "claw")
        self.assertEqual(config.task_brief_enforce, "deny")
        self.assertEqual(config.llmlingua_hook_rate, 0.6)
        self.assertEqual(config.llmlingua_hook_min_chars, 1200)
        self.assertEqual(config.adaptive_ctx_token_threshold, 4000)
        self.assertEqual(config.adaptive_ctx_message_threshold, 10)
        self.assertEqual(config.adaptive_ctx_structure_min_input_tokens, 2500)
        self.assertTrue(config.ccr_enabled)
        self.assertEqual(config.ccr_threshold_chars, 4000)
        self.assertEqual(config.ccr_similarity_threshold, 0.85)
        self.assertEqual(config.smart_crusher_n, 10)
        self.assertEqual(config.smart_crusher_m, 10)
        self.assertFalse(config.llmlingua_blocking_init)

    def test_custom_values_from_env(self) -> None:
        # Test override via os.environ
        os.environ["COMPRESSION_BACKEND"] = "headroom"
        os.environ["TASK_BRIEF_ENFORCE"] = "allow"
        os.environ["LLMLINGUA_HOOK_RATE"] = "0.75"
        os.environ["LLMLINGUA_HOOK_MIN_CHARS"] = "3000"
        os.environ["CCR_ENABLED"] = "0"
        os.environ["CCR_SIMILARITY_THRESHOLD"] = "0.95"

        try:
            config = ConfigManager(cursor_home=self.cursor_home)
            self.assertEqual(config.compression_backend, "headroom")
            self.assertEqual(config.task_brief_enforce, "allow")
            self.assertEqual(config.llmlingua_hook_rate, 0.75)
            self.assertEqual(config.llmlingua_hook_min_chars, 3000)
            self.assertFalse(config.ccr_enabled)
            self.assertEqual(config.ccr_similarity_threshold, 0.95)
        finally:
            # Clean up env
            for k in (
                "COMPRESSION_BACKEND",
                "TASK_BRIEF_ENFORCE",
                "LLMLINGUA_HOOK_RATE",
                "LLMLINGUA_HOOK_MIN_CHARS",
                "CCR_ENABLED",
                "CCR_SIMILARITY_THRESHOLD",
            ):
                os.environ.pop(k, None)

    def test_values_from_file(self) -> None:
        # Write custom settings to compression.env
        env_file = self.cursor_home / "compression.env"
        env_file.write_text(
            "COMPRESSION_BACKEND=both\n"
            "TASK_BRIEF_ENFORCE=warn\n"
            "LLMLINGUA_HOOK_RATE=0.3\n"
            "# Comment line\n"
            "ADAPTIVE_CTX_TOKEN_THRESHOLD=5000\n"
            "CCR_SIMILARITY_THRESHOLD=0.92\n",
            encoding="utf-8",
        )

        config = ConfigManager(cursor_home=self.cursor_home)
        self.assertEqual(config.compression_backend, "both")
        self.assertEqual(config.task_brief_enforce, "warn")
        self.assertEqual(config.llmlingua_hook_rate, 0.3)
        self.assertEqual(config.adaptive_ctx_token_threshold, 5000)
        self.assertEqual(config.ccr_similarity_threshold, 0.92)


if __name__ == "__main__":
    unittest.main()
