#!/usr/bin/env python3
"""Tests for providers_config resolution (data dir, rtk cwd, enablement)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[4]
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
        self.assertEqual(out, [{"id": "x", "label": "X"}])


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
            with patch.dict("os.environ", {}, clear=True):
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
            with patch.dict("os.environ", {}, clear=True):
                self.assertEqual(pc.get_rtk_cwd("x"), Path("~/rtk").expanduser())


if __name__ == "__main__":
    unittest.main()
