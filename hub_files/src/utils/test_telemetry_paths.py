#!/usr/bin/env python3
"""Tests for telemetry_paths source inference and directory resolution."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[4]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import telemetry_paths as tp


class PathRelativeTests(unittest.TestCase):
    def test_relative_true(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            child = Path(tmp) / "a" / "b"
            child.mkdir(parents=True)
            self.assertTrue(tp._path_is_relative_to(child, Path(tmp)))

    def test_relative_false(self) -> None:
        self.assertFalse(tp._path_is_relative_to(Path("/usr"), Path("/opt")))


class InferSourceTests(unittest.TestCase):
    def test_explicit_source(self) -> None:
        with patch.dict("os.environ", {"SCROOGE_TELEMETRY_SOURCE": "Codex"}, clear=True):
            self.assertEqual(tp.infer_source(), "codex")

    def test_event_hint(self) -> None:
        with patch.dict("os.environ", {"ANTIGRAVITY_TT_EVENT": "1"}, clear=True):
            self.assertEqual(tp.infer_source(), "antigravity")

    def test_runtime_hint(self) -> None:
        with patch.dict("os.environ", {"CODEX_THREAD_ID": "t1"}, clear=True):
            self.assertEqual(tp.infer_source(), "codex")

    def test_home_hint(self) -> None:
        with patch.dict("os.environ", {"CURSOR_HOME": "/some/home"}, clear=True):
            with patch.object(tp, "_path_is_relative_to", return_value=True):
                self.assertEqual(tp.infer_source(), "cursor")

    def test_default_cursor(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            with patch.object(tp, "_path_is_relative_to", return_value=False):
                self.assertEqual(tp.infer_source(), "cursor")


class ResolveDataDirTests(unittest.TestCase):
    def test_env_override(self) -> None:
        with patch.dict(
            "os.environ", {"SCROOGE_TOKEN_TELEMETRY_DATA_DIR": "/tmp/data"}, clear=True
        ):
            self.assertEqual(tp.resolve_data_dir(), Path("/tmp/data"))

    def test_uses_provider_data_dir(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            with patch.object(tp, "get_data_dir", return_value=Path("/tmp/prov")):
                self.assertEqual(tp.resolve_data_dir("cursor"), Path("/tmp/prov"))

    def test_fallback_cursor_when_none(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            with patch.object(tp, "get_data_dir", return_value=None):
                with patch.object(tp, "infer_source", return_value="unknown"):
                    self.assertEqual(
                        tp.resolve_data_dir(), Path.home() / ".cursor" / "token-telemetry"
                    )

    def test_fallback_codex_when_none(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            with patch.object(tp, "get_data_dir", return_value=None):
                with patch.object(tp, "infer_source", return_value="codex"):
                    self.assertEqual(
                        tp.resolve_data_dir(), Path.home() / ".codex" / "token-telemetry"
                    )

    def test_resolve_log_file(self) -> None:
        with patch.object(tp, "resolve_data_dir", return_value=Path("/tmp/d")):
            self.assertEqual(tp.resolve_log_file(), Path("/tmp/d/events.jsonl"))


class ResolveAppDirTests(unittest.TestCase):
    def test_override(self) -> None:
        with patch.dict("os.environ", {"CURSOR_TOKEN_TELEMETRY_APP": "/tmp/app"}, clear=True):
            self.assertEqual(tp.resolve_app_dir(), Path("/tmp/app"))

    def test_default(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            self.assertEqual(tp.resolve_app_dir(), tp.DEFAULT_APP_DIR)

    def test_venv_paths(self) -> None:
        with patch.object(tp, "resolve_app_dir", return_value=Path("/tmp/app")):
            self.assertEqual(tp.resolve_venv_python(), Path("/tmp/app/.venv-desktop/bin/python"))
            self.assertEqual(
                tp.resolve_venv_claw_compactor(),
                Path("/tmp/app/.venv-desktop/bin/claw-compactor"),
            )


class LoadTelemetryEnvTests(unittest.TestCase):
    def test_loads_env_from_app_override(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / ".env").write_text(
                "SCROOGE_TEST_UNIQUE_KEY=hello\n# comment\n", encoding="utf-8"
            )
            env = {"SCROOGE_TOKEN_TELEMETRY_APP": tmp}
            with patch.dict("os.environ", env, clear=True):
                tp.load_telemetry_env()
                self.assertEqual(__import__("os").environ.get("SCROOGE_TEST_UNIQUE_KEY"), "hello")


if __name__ == "__main__":
    unittest.main()
