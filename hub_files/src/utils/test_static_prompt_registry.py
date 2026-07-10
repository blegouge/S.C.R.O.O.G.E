#!/usr/bin/env python3
"""Tests for static prompt block assembler."""

from __future__ import annotations

import sys
from pathlib import Path

local_src = Path(__file__).resolve().parents[2]
if str(local_src) not in sys.path:
    sys.path.insert(0, str(local_src))

import tempfile
import unittest

from utils.static_prompt_registry import (
    PromptRegistryPaths,
    build_global_static_block,
)


class StaticPromptRegistryTests(unittest.TestCase):
    def test_paths_default(self) -> None:
        paths = PromptRegistryPaths()
        self.assertIsNotNone(paths.cursor_home)
        self.assertIsNotNone(paths.rules_dir)
        self.assertIsNotNone(paths.skills_dir)

    def test_build_global_static_block_empty(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            paths = PromptRegistryPaths(cursor_home=Path(tmpdir))
            block = build_global_static_block(paths)
            self.assertIn("[GLOBAL_SYSTEM_STATIC]", block)
            self.assertIn("GLOBAL_RULE_REGISTRY:\n- none", block)
            self.assertIn("GLOBAL_SKILL_REGISTRY:\n- none", block)

    def test_build_global_static_block_with_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            rules_dir = tmp_path / "rules"
            skills_dir = tmp_path / "skills"

            rules_dir.mkdir(parents=True)
            skills_dir.mkdir(parents=True)

            # Create a rule file
            rule_file = rules_dir / "test-rule.mdc"
            rule_file.write_text("alwaysApply: true\n", encoding="utf-8")

            # Create a skill file
            skill_subdir = skills_dir / "test-skill"
            skill_subdir.mkdir()
            skill_file = skill_subdir / "SKILL.md"
            skill_file.write_text("name: Test Skill\ndescription: A test skill\n", encoding="utf-8")

            paths = PromptRegistryPaths(cursor_home=tmp_path)
            block = build_global_static_block(paths)

            self.assertIn("test-rule.mdc (scope=always)", block)
            self.assertIn("- Test Skill", block)
            self.assertNotIn("- none", block)
