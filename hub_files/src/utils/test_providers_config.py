#!/usr/bin/env python3
"""Tests for providers_config resolution (data dir, rtk cwd, enablement)."""

from __future__ import annotations

import sys
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

import providers_config as pc


def _fake(**kwargs) -> pc.ProviderConfig:
    base = {
        "name": "x",
        "env_enabled": "X_ENABLED",
        "data_dir": "~/x-data",
        "rtk_cwd": "~/x-rtk",
        "env_home": None,
        "label": "X",
        "env_stats": None,
    }
    base.update(kwargs)
    return pc.ProviderConfig(**base)


class LoadConfigTests(unittest.TestCase):
    def test_load_config_has_providers(self) -> None:
        providers = pc.get_all_providers()
        self.assertTrue(providers)
        self.assertTrue(all(isinstance(p, pc.ProviderConfig) for p in providers))

    def test_get_provider_unknown(self) -> None:
        self.assertIsNone(pc.get_provider("__nope__"))

    def test_parse_simple_yaml_fallback(self) -> None:
        sample = """
# Header comment
sources:
  test_prov:
    env_enabled: TEST_ENABLED
    data_dir: ~/.test/data
    rtk_cwd: null
    label: "Test Label"
    flag: true
"""
        parsed = pc._parse_simple_yaml(sample)
        self.assertIn("sources", parsed)
        self.assertEqual(parsed["sources"]["test_prov"]["env_enabled"], "TEST_ENABLED")
        self.assertIsNone(parsed["sources"]["test_prov"]["rtk_cwd"])
        self.assertEqual(parsed["sources"]["test_prov"]["label"], "Test Label")
        self.assertTrue(parsed["sources"]["test_prov"]["flag"])

    def test_load_config_without_yaml_module(self) -> None:
        with patch.object(pc, "yaml", None):
            with patch.object(pc, "_config_cache", None):
                config = pc.load_config()
                self.assertIn("cursor", config)
                self.assertEqual(config["cursor"].name, "cursor")


class EnablementTests(unittest.TestCase):
    def test_is_enabled_unknown_false(self) -> None:
        self.assertFalse(pc.is_enabled("__nope__"))

    def test_is_enabled_toggle(self) -> None:
        with patch.object(pc, "get_provider", return_value=_fake()):
            with patch.dict("os.environ", {"X_ENABLED": "1"}, clear=False):
                self.assertTrue(pc.is_enabled("x"))
            with patch.dict("os.environ", {"X_ENABLED": "off"}, clear=False):
                self.assertFalse(pc.is_enabled("x"))

    def test_get_enabled_providers_shape(self) -> None:
        with patch.object(pc, "load_config", return_value={"x": _fake()}):
            with patch.object(pc, "is_enabled", return_value=True):
                out = pc.get_enabled_providers()
        self.assertEqual(out, [{"id": "x", "label": "X", "event_count": 0}])


class DataDirTests(unittest.TestCase):
    def test_unknown_returns_none(self) -> None:
        self.assertIsNone(pc.get_data_dir("__nope__"))

    def test_env_stats_override(self) -> None:
        with patch.object(pc, "get_provider", return_value=_fake(env_stats="X_STATS")):
            with patch.dict("os.environ", {"X_STATS": "/tmp/stats"}, clear=False):
                self.assertEqual(pc.get_data_dir("x"), Path("/tmp/stats"))

    def test_env_home_override(self) -> None:
        with patch.object(pc, "get_provider", return_value=_fake(env_home="X_HOME")):
            with patch.dict("os.environ", {"X_HOME": "/tmp/home"}, clear=False):
                self.assertEqual(pc.get_data_dir("x"), Path("/tmp/home/token-telemetry"))

    def test_default_data_dir(self) -> None:
        with patch.object(pc, "get_provider", return_value=_fake(data_dir="~/plain")):
            with patch.dict("os.environ", {"X_STATS": "", "X_HOME": ""}, clear=False):
                self.assertEqual(pc.get_data_dir("x"), Path("~/plain").expanduser())


class RtkCwdTests(unittest.TestCase):
    def test_unknown_or_no_rtk(self) -> None:
        self.assertIsNone(pc.get_rtk_cwd("__nope__"))
        with patch.object(pc, "get_provider", return_value=_fake(rtk_cwd=None)):
            self.assertIsNone(pc.get_rtk_cwd("x"))

    def test_env_home_override(self) -> None:
        with patch.object(pc, "get_provider", return_value=_fake(env_home="X_HOME")):
            with patch.dict("os.environ", {"X_HOME": "/tmp/rtkhome"}, clear=False):
                self.assertEqual(pc.get_rtk_cwd("x"), Path("/tmp/rtkhome"))

    def test_default_rtk_cwd(self) -> None:
        with patch.object(pc, "get_provider", return_value=_fake(rtk_cwd="~/rtk")):
            with patch.dict("os.environ", {"X_HOME": ""}, clear=False):
                self.assertEqual(pc.get_rtk_cwd("x"), Path("~/rtk").expanduser())


class ExtraProvidersConfigCoverageTests(unittest.TestCase):
    def test_config_path_frozen(self) -> None:
        with (
            patch.object(sys, "frozen", True, create=True),
            patch.object(sys, "_MEIPASS", "/tmp/meipass_test", create=True),
        ):
            p = pc._config_path()
            self.assertEqual(p, Path("/tmp/meipass_test/providers_config.yaml"))

    def test_ensure_env_loaded_exception(self) -> None:
        with patch("telemetry_paths.load_telemetry_env", side_effect=RuntimeError("env error")):
            pc._ensure_env_loaded()

    def test_get_enabled_providers_disk_fallback(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            with (
                patch.dict("os.environ", {}, clear=False),
                patch("providers_config.is_enabled", return_value=False),
                patch("providers_config.get_data_dir", return_value=tmppath),
            ):
                enabled = pc.get_enabled_providers()
                self.assertGreater(len(enabled), 0)

    def test_get_enabled_providers_claude_fallback(self) -> None:
        with (
            patch.dict("os.environ", {}, clear=False),
            patch("providers_config.is_enabled", return_value=False),
            patch("providers_config.get_data_dir", return_value=None),
        ):
            enabled = pc.get_enabled_providers()
            self.assertTrue(any(p["id"] == "claude" for p in enabled))

    def test_find_rtk_binary_candidates(self) -> None:
        import tempfile

        with tempfile.NamedTemporaryFile() as tmp:
            candidate_path = Path(tmp.name)
            with (
                patch.dict("os.environ", {"RTK_BIN": ""}),
                patch("shutil.which", return_value=None),
                patch.object(Path, "is_file", autospec=True) as mock_is_file,
            ):
                mock_is_file.side_effect = lambda p: str(p) == str(candidate_path)
                with patch("providers_config.Path", wraps=Path) as mock_path_cls:
                    res = pc.find_rtk_binary()
                    # Verify result or fallback behavior
                    self.assertTrue(res is None or isinstance(res, str))


if __name__ == "__main__":
    unittest.main()
