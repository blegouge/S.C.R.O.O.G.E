#!/usr/bin/env python3
"""Tests for smart_crusher anomaly detection and JSON/log compression."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[4]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import smart_crusher as sc


class IsAnomalyTests(unittest.TestCase):
    def test_none(self) -> None:
        self.assertFalse(sc._is_anomaly(None))

    def test_ok_false(self) -> None:
        self.assertTrue(sc._is_anomaly({"ok": False}))
        self.assertTrue(sc._is_anomaly({"success": "fail"}))

    def test_status_codes(self) -> None:
        self.assertTrue(sc._is_anomaly({"status": 500}))
        self.assertTrue(sc._is_anomaly({"status_code": "404"}))
        self.assertFalse(sc._is_anomaly({"status": 200}))

    def test_status_string_keyword(self) -> None:
        self.assertTrue(sc._is_anomaly({"code": "an error occurred"}))

    def test_text_keywords(self) -> None:
        self.assertTrue(sc._is_anomaly("Traceback (most recent call last)"))
        self.assertTrue(sc._is_anomaly("connection failed"))
        self.assertFalse(sc._is_anomaly("everything nominal"))

    def test_list_serialized_keyword(self) -> None:
        self.assertTrue(sc._is_anomaly(["line one", "exception here"]))


class CompressJsonDataTests(unittest.TestCase):
    def test_small_list_unchanged(self) -> None:
        data = [1, 2]
        out, modified = sc._compress_json_data(data, n=1, m=1)
        self.assertEqual(out, [1, 2])
        self.assertFalse(modified)

    def test_large_list_prunes_middle(self) -> None:
        data = [{"i": i} for i in range(10)]
        out, modified = sc._compress_json_data(data, n=1, m=1)
        self.assertTrue(modified)
        # First + pruned marker + last
        self.assertEqual(out[0], {"i": 0})
        self.assertEqual(out[-1], {"i": 9})
        self.assertTrue(any(isinstance(x, dict) and "_pruned_count" in x for x in out))

    def test_large_list_keeps_anomalies(self) -> None:
        data = [{"i": i} for i in range(5)] + [{"status": 500}] + [{"i": i} for i in range(5)]
        out, modified = sc._compress_json_data(data, n=1, m=1)
        self.assertTrue(modified)
        self.assertTrue(any(isinstance(x, dict) and x.get("status") == 500 for x in out))

    def test_dict_recursion(self) -> None:
        data = {"logs": [{"i": i} for i in range(10)]}
        out, modified = sc._compress_json_data(data, n=1, m=1)
        self.assertTrue(modified)
        self.assertIn("logs", out)


class CompressTextLinesTests(unittest.TestCase):
    def test_few_lines_unchanged(self) -> None:
        text = "a\nb\nc"
        self.assertEqual(sc._compress_text_lines(text, n=2, m=2), text)

    def test_many_lines_prunes(self) -> None:
        lines = [f"line {i}" for i in range(20)]
        text = "\n".join(lines)
        out = sc._compress_text_lines(text, n=1, m=1)
        self.assertIn("PRUNED", out)
        self.assertTrue(out.startswith("line 0"))
        self.assertTrue(out.rstrip().endswith("line 19"))

    def test_many_lines_keeps_error(self) -> None:
        lines = [f"info {i}" for i in range(10)] + ["ERROR boom"] + [f"info {i}" for i in range(10)]
        text = "\n".join(lines)
        out = sc._compress_text_lines(text, n=1, m=1)
        self.assertIn("ERROR boom", out)


class SmartCrusherCompressTests(unittest.TestCase):
    def setUp(self) -> None:
        self.crusher = sc.SmartCrusher(sc.SmartCrusherConfig(n=1, m=1))

    def test_empty(self) -> None:
        self.assertEqual(self.crusher.compress(""), "")

    def test_small_json_unchanged(self) -> None:
        payload = json.dumps({"a": 1})
        # Not modified -> returns original text.
        self.assertEqual(self.crusher.compress(payload), payload)

    def test_large_json_array_compressed(self) -> None:
        payload = json.dumps([{"i": i} for i in range(10)])
        out = self.crusher.compress(payload)
        self.assertIn("_pruned_count", out)

    def test_json_lines_compressed(self) -> None:
        lines = "\n".join(json.dumps({"i": i}) for i in range(10))
        out = self.crusher.compress(lines)
        self.assertIn("_pruned_count", out)

    def test_raw_text_compressed(self) -> None:
        text = "\n".join(f"line {i}" for i in range(20))
        out = self.crusher.compress(text)
        self.assertIn("PRUNED", out)

    def test_config_defaults_from_telemetry_config(self) -> None:
        # Exercise the default-config branch (no explicit n/m).
        crusher = sc.SmartCrusher()
        self.assertIsInstance(crusher.config.n, int)
        self.assertIsInstance(crusher.config.m, int)


if __name__ == "__main__":
    unittest.main()
