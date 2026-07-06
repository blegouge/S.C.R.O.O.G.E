#!/usr/bin/env python3
"""Unit tests for the fail-safe decorators."""

from __future__ import annotations

import io
import sys
import unittest
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from telemetry_common import fail_safe, hook_fail_safe


class FailsafeTests(unittest.TestCase):
    def test_fail_safe_decorator(self) -> None:
        @fail_safe(fallback_value="fallback_ok")
        def crashing_function():
            raise RuntimeError("Dummy crash")

        # Capture stderr to avoid polluting outputs
        original_stderr = sys.stderr
        sys.stderr = io.StringIO()
        try:
            res = crashing_function()
            self.assertEqual(res, "fallback_ok")
            self.assertIn("[telemetry-failsafe]", sys.stderr.getvalue())
        finally:
            sys.stderr = original_stderr

    def test_hook_fail_safe_decorator(self) -> None:
        @hook_fail_safe(fallback_json='{"fallback": true}')
        def crashing_hook():
            raise ValueError("Dummy hook crash")

        # Capture stdout and stderr
        original_stdout = sys.stdout
        original_stderr = sys.stderr
        sys.stdout = io.StringIO()
        sys.stderr = io.StringIO()
        try:
            res = crashing_hook()
            self.assertEqual(res, 0)
            self.assertEqual(sys.stdout.getvalue(), '{"fallback": true}')
            self.assertIn("[hook-failsafe]", sys.stderr.getvalue())
        finally:
            sys.stdout = original_stdout
            sys.stderr = original_stderr


if __name__ == "__main__":
    unittest.main()
