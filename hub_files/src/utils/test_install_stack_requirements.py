#!/usr/bin/env python3
"""Tests for install_stack dependency lock selection."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from install_stack import select_desktop_requirements  # noqa: E402


class DesktopRequirementsSelectionTests(unittest.TestCase):
    def test_linux_prefers_linux_lock_when_present(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "requirements-desktop.txt").write_text("portable\n", encoding="utf-8")
            (root / "requirements-desktop-linux.lock").write_text("linux\n", encoding="utf-8")

            with patch("install_stack.sys.platform", "linux"):
                self.assertEqual(
                    select_desktop_requirements(root).name,
                    "requirements-desktop-linux.lock",
                )

    def test_linux_falls_back_to_portable_requirements(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "requirements-desktop.txt").write_text("portable\n", encoding="utf-8")

            with patch("install_stack.sys.platform", "linux"):
                self.assertEqual(
                    select_desktop_requirements(root).name,
                    "requirements-desktop.txt",
                )

    def test_darwin_uses_portable_requirements(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "requirements-desktop.txt").write_text("portable\n", encoding="utf-8")

            with patch("install_stack.sys.platform", "darwin"):
                self.assertEqual(
                    select_desktop_requirements(root).name,
                    "requirements-desktop.txt",
                )

    def test_windows_uses_windows_lock_when_present(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "requirements-desktop.txt").write_text("portable\n", encoding="utf-8")
            (root / "requirements-desktop-windows.lock").write_text("windows\n", encoding="utf-8")

            with patch("install_stack.sys.platform", "win32"):
                self.assertEqual(
                    select_desktop_requirements(root).name,
                    "requirements-desktop-windows.lock",
                )


if __name__ == "__main__":
    unittest.main()
