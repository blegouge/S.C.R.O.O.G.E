#!/usr/bin/env python3
"""Tests for agent inspection and capabilities resolution in providers_config."""

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


class AgentInspectorTests(unittest.TestCase):
    def test_inspect_agent_status_unknown(self) -> None:
        res = pc.inspect_agent_status("nonexistent_provider")
        self.assertFalse(res["ok"])
        self.assertIn("Unknown provider", res["error"])

    def test_inspect_agent_status_valid_provider(self) -> None:
        res = pc.inspect_agent_status("antigravity")
        self.assertTrue(res["ok"])
        self.assertEqual(res["source"], "antigravity")
        self.assertEqual(res["label"], "Antigravity")
        self.assertIn("items", res)
        self.assertIsInstance(res["items"], list)
        self.assertGreater(len(res["items"]), 0)

        # Verify item keys
        item_ids = [item["id"] for item in res["items"]]
        for expected in ["telemetry", "hooks", "rtk", "rules", "skills", "compactor", "mcp"]:
            self.assertIn(expected, item_ids)

    def test_get_home_dir_resolution(self) -> None:
        home_antigravity = pc.get_home_dir("antigravity")
        self.assertEqual(home_antigravity, Path.home() / ".gemini" / "antigravity")

        home_cursor = pc.get_home_dir("cursor")
        self.assertEqual(home_cursor, Path.home() / ".cursor")

        with patch.dict("os.environ", {"ANTIGRAVITY_HOME": "/tmp/custom_ag"}, clear=False):
            self.assertEqual(pc.get_home_dir("antigravity"), Path("/tmp/custom_ag"))

    def test_install_agent_component_unknown(self) -> None:
        res = pc.install_agent_component("nonexistent_provider")
        self.assertFalse(res["ok"])
        self.assertIn("Unknown provider", res["error"])

    def test_install_agent_component_valid(self) -> None:
        res = pc.install_agent_component("antigravity", "rules")
        self.assertTrue(res["ok"])
        self.assertEqual(res["source"], "antigravity")
        self.assertIn("rules", res["installed"])
        self.assertIn("status", res)

    def test_install_agent_component_all_components(self) -> None:
        for comp in ["all", "telemetry", "hooks", "rtk", "skills", "compactor", "mcp"]:
            res = pc.install_agent_component("antigravity", comp)
            self.assertTrue(res["ok"])
            self.assertIn("status", res)

    def test_find_hub_files_root(self) -> None:
        root = pc.find_hub_files_root()
        self.assertTrue(isinstance(root, Path))

    def test_find_hub_files_root_frozen(self) -> None:
        with (
            patch.object(sys, "frozen", True, create=True),
            patch.object(sys, "_MEIPASS", "/tmp/fake_meipass", create=True),
        ):
            root = pc.find_hub_files_root()
            self.assertEqual(root, Path("/tmp/fake_meipass"))

    def test_parse_simple_yaml(self) -> None:
        sample_yaml = """
# Header comment
sources:
  cursor:
    env_enabled: TELEMETRY_CURSOR_ENABLED
    data_dir: ~/.cursor/token-telemetry
    active: true
    disabled: false
    none_val: null
    quoted: 'hello'
    double_quoted: "world"
"""
        parsed = pc._parse_simple_yaml(sample_yaml)
        self.assertIn("sources", parsed)
        cursor = parsed["sources"]["cursor"]
        self.assertEqual(cursor["env_enabled"], "TELEMETRY_CURSOR_ENABLED")
        self.assertTrue(cursor["active"])
        self.assertFalse(cursor["disabled"])
        self.assertIsNone(cursor["none_val"])
        self.assertEqual(cursor["quoted"], "hello")
        self.assertEqual(cursor["double_quoted"], "world")

    def test_find_rtk_binary_env(self) -> None:
        import tempfile

        with tempfile.NamedTemporaryFile() as tmp:
            with patch.dict("os.environ", {"RTK_BIN": tmp.name}):
                self.assertEqual(pc.find_rtk_binary(), tmp.name)

    def test_get_enabled_providers(self) -> None:
        with patch.dict("os.environ", {"TELEMETRY_CURSOR_ENABLED": "1"}):
            enabled = pc.get_enabled_providers()
            self.assertTrue(any(p["id"] == "cursor" for p in enabled))

    def test_inspect_agent_status_installed_states(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            (tmppath / "hooks.json").touch()
            (tmppath / "AGENTS.md").touch()
            (tmppath / ".cursorrules").touch()
            (tmppath / "mcp.json").touch()

            skills_dir = tmppath / "skills" / "test_skill"
            skills_dir.mkdir(parents=True)
            (skills_dir / "SKILL.md").touch()

            data_dir = tmppath / "token-telemetry"
            data_dir.mkdir()
            (data_dir / "claw_compactor_adapter.py").touch()

            with (
                patch("providers_config.get_home_dir", return_value=tmppath),
                patch("providers_config.get_data_dir", return_value=data_dir),
            ):
                status = pc.inspect_agent_status("antigravity")
                self.assertTrue(status["ok"])

                item_map = {item["id"]: item for item in status["items"]}
                self.assertIn(item_map["telemetry"]["status"], ("installed", "active"))
                self.assertIn(item_map["hooks"]["status"], ("installed", "active"))
                self.assertEqual(item_map["rules"]["status"], "active")
                self.assertEqual(item_map["skills"]["status"], "active")
                self.assertIn(item_map["compactor"]["status"], ("installed", "active"))
                self.assertEqual(item_map["mcp"]["status"], "active")

    def test_get_data_dir_overrides(self) -> None:
        with patch.dict("os.environ", {"ANTIGRAVITY_STATS_DIR": "/tmp/test_stats_dir"}):
            d = pc.get_data_dir("antigravity")
            self.assertEqual(d, Path("/tmp/test_stats_dir"))

        with (
            patch.dict("os.environ", {"ANTIGRAVITY_HOME": "/tmp/test_home"}, clear=False),
            patch.dict("os.environ", {"ANTIGRAVITY_STATS_DIR": ""}),
        ):
            d = pc.get_data_dir("antigravity")
            self.assertEqual(d, Path("/tmp/test_home/token-telemetry"))

        self.assertIsNone(pc.get_data_dir("nonexistent_provider"))

    def test_get_rtk_cwd_overrides(self) -> None:
        with patch.dict("os.environ", {"ANTIGRAVITY_HOME": "/tmp/test_ag_home"}):
            cwd = pc.get_rtk_cwd("antigravity")
            self.assertEqual(cwd, Path("/tmp/test_ag_home"))

        self.assertIsNone(pc.get_rtk_cwd("nonexistent_provider"))

    def test_get_all_providers(self) -> None:
        all_provs = pc.get_all_providers()
        self.assertIsInstance(all_provs, list)
        self.assertGreater(len(all_provs), 0)

    def test_inspect_agent_status_empty_dir_states(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            data_dir = tmppath / "token-telemetry"
            data_dir.mkdir()

            with (
                patch("providers_config.get_home_dir", return_value=tmppath),
                patch("providers_config.get_data_dir", return_value=data_dir),
                patch("providers_config.is_enabled", return_value=False),
                patch("providers_config.find_rtk_binary", return_value=None),
            ):
                status = pc.inspect_agent_status("antigravity")
                self.assertTrue(status["ok"])
                item_map = {item["id"]: item for item in status["items"]}
                self.assertIn(item_map["telemetry"]["status"], ("installed", "active"))

                self.assertEqual(item_map["hooks"]["status"], "missing")
                self.assertEqual(item_map["rules"]["status"], "missing")
                self.assertEqual(item_map["skills"]["status"], "missing")
                self.assertEqual(item_map["compactor"]["status"], "missing")
                self.assertEqual(item_map["mcp"]["status"], "missing")

    def test_install_agent_component_in_temp_dir(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            data_dir = tmppath / "token-telemetry"

            with (
                patch("providers_config.get_home_dir", return_value=tmppath),
                patch("providers_config.get_data_dir", return_value=data_dir),
            ):
                res = pc.install_agent_component("antigravity", "all")
                self.assertTrue(res["ok"])
                self.assertTrue((data_dir / "events.jsonl").exists())
                self.assertTrue((tmppath / "hooks.json").exists())
                self.assertTrue((tmppath / "AGENT.md").exists())
                self.assertTrue((tmppath / "mcp.json").exists())


if __name__ == "__main__":
    unittest.main()
