#!/usr/bin/env python3
"""Tests for rtk_resolver binary discovery and probing (subprocess mocked)."""

from __future__ import annotations

import subprocess
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

import rtk_resolver


class _Proc:
    def __init__(self, returncode: int = 0, stdout: str = "", stderr: str = "") -> None:
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


class RtkEnvAndCandidateTests(unittest.TestCase):
    def test_read_env_file_value_parses_quotes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            env_file = Path(tmp) / "compression.env"
            env_file.write_text('# comment\nRTK_BIN="/opt/rtk"\nOTHER=ignored\n', encoding="utf-8")
            with patch.object(rtk_resolver, "_compression_env_paths", return_value=[env_file]):
                self.assertEqual(rtk_resolver._read_env_file_value("RTK_BIN"), "/opt/rtk")
                self.assertEqual(rtk_resolver._read_env_file_value("MISSING"), "")

    def test_patched_env_appends_common_paths(self) -> None:
        with patch.dict("os.environ", {"PATH": "/custom/bin"}, clear=False):
            env = rtk_resolver._patched_env()
        self.assertIn("/custom/bin", env["PATH"])
        self.assertIn("/usr/bin", env["PATH"])

    def test_candidate_bins_respects_env_bin_first(self) -> None:
        with patch.dict("os.environ", {"RTK_BIN": "/env/rtk"}, clear=False):
            with patch.object(rtk_resolver, "_read_env_file_value", return_value=""):
                with patch("shutil.which", return_value=None):
                    with patch.object(
                        rtk_resolver, "resolve_data_dir", return_value=Path("/nonexistent")
                    ):
                        bins = rtk_resolver.rtk_candidate_bins()
        self.assertEqual(bins[0], str(Path("/env/rtk").expanduser()))
        # Always ends with a bare "rtk" fallback.
        self.assertIn("rtk", bins)


class RtkProbeTests(unittest.TestCase):
    def test_probe_success_writes_cache(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(rtk_resolver, "resolve_data_dir", return_value=Path(tmp)):
                with patch(
                    "subprocess.run",
                    return_value=_Proc(0, stdout='{"summary": {"total_saved": 10}}'),
                ):
                    result = rtk_resolver.probe_rtk_bin("/opt/rtk")
            self.assertTrue(result["ok"])
            self.assertTrue((Path(tmp) / rtk_resolver._CACHE_NAME).is_file())

    def test_probe_nonzero_returncode(self) -> None:
        with patch("subprocess.run", return_value=_Proc(1, stderr="not found")):
            result = rtk_resolver.probe_rtk_bin("/opt/rtk")
        self.assertFalse(result["ok"])
        self.assertEqual(result["returncode"], 1)

    def test_probe_timeout(self) -> None:
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="rtk", timeout=1)):
            result = rtk_resolver.probe_rtk_bin("/opt/rtk")
        self.assertFalse(result["ok"])

    def test_probe_invalid_json(self) -> None:
        with patch("subprocess.run", return_value=_Proc(0, stdout="not-json")):
            result = rtk_resolver.probe_rtk_bin("/opt/rtk")
        self.assertFalse(result["ok"])

    def test_probe_json_not_object(self) -> None:
        with patch("subprocess.run", return_value=_Proc(0, stdout="[1, 2, 3]")):
            result = rtk_resolver.probe_rtk_bin("/opt/rtk")
        self.assertFalse(result["ok"])


class RtkResolveTests(unittest.TestCase):
    def test_resolve_returns_first_working(self) -> None:
        with patch.object(rtk_resolver, "rtk_candidate_bins", return_value=["/a/rtk", "/b/rtk"]):
            fail = {"ok": False, "rtk_bin": "/a/rtk", "error": "x"}
            with patch.object(
                rtk_resolver,
                "probe_rtk_bin",
                side_effect=[fail, {"ok": True, "rtk_bin": "/b/rtk"}],
            ):
                cmd, attempts = rtk_resolver.resolve_rtk_command()
        self.assertEqual(cmd, ["/b/rtk"])
        self.assertEqual(len(attempts), 2)

    def test_resolve_returns_none_when_all_fail(self) -> None:
        with patch.object(rtk_resolver, "rtk_candidate_bins", return_value=["/a/rtk"]):
            with patch.object(
                rtk_resolver, "probe_rtk_bin", return_value={"ok": False, "rtk_bin": "/a/rtk"}
            ):
                cmd, attempts = rtk_resolver.resolve_rtk_command()
        self.assertIsNone(cmd)
        self.assertEqual(len(attempts), 1)

    def test_diagnose_ok(self) -> None:
        with patch.object(
            rtk_resolver, "resolve_rtk_command", return_value=(["/b/rtk"], [{"ok": True}])
        ):
            with patch.object(rtk_resolver, "rtk_candidate_bins", return_value=["/b/rtk"]):
                diag = rtk_resolver.diagnose_rtk(frozen=False)
        self.assertTrue(diag["ok"])
        self.assertEqual(diag["resolved"], "/b/rtk")
        self.assertIsNone(diag["hint"])

    def test_diagnose_failure_gives_hint(self) -> None:
        with patch.object(rtk_resolver, "resolve_rtk_command", return_value=(None, [])):
            with patch.object(rtk_resolver, "rtk_candidate_bins", return_value=[]):
                diag = rtk_resolver.diagnose_rtk(frozen=True)
        self.assertFalse(diag["ok"])
        self.assertIsNotNone(diag["hint"])


if __name__ == "__main__":
    unittest.main()
