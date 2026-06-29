#!/usr/bin/env python3
"""
Deterministic static prompt block assembler for global rules and skills.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
import re
from typing import Iterable


@dataclass(frozen=True, slots=True)
class PromptRegistryPaths:
    """Filesystem locations used to build the static cache block."""

    cursor_home: Path = Path(os.getenv("ANTIGRAVITY_HOME") or os.getenv("CURSOR_HOME") or Path.home() / ".cursor")

    @property
    def rules_dir(self) -> Path:
        return self.cursor_home / "rules"

    @property
    def skills_dir(self) -> Path:
        return self.cursor_home / "skills"


def _iter_files_sorted(root: Path, pattern: str) -> Iterable[Path]:
    if not root.exists():
        return []
    return sorted(path for path in root.glob(pattern) if path.is_file())


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def _extract_skill_name(content: str, fallback: str) -> str:
    match = re.search(r"(?im)^\s*name:\s*(.+?)\s*$", content)
    if match:
        return match.group(1).strip()
    return fallback


def _extract_skill_description(content: str) -> str:
    match = re.search(r"(?im)^\s*description:\s*(.+?)\s*$", content)
    if match:
        return match.group(1).strip()
    return ""


def _extract_rule_scope(content: str) -> str:
    lowered = content.lower()
    if "alwaysapply: true" in lowered:
        return "always"
    if "alwaysapply: false" in lowered:
        return "selective"
    return "unspecified"


def build_global_static_block(paths: PromptRegistryPaths | None = None) -> str:
    """
    Build a deterministic static system block for prompt caching.

    The output order is stable:
    1) Caveman defaults
    2) Rule registry (file names + scope)
    3) Skill registry (name + short description)
    """
    registry_paths = paths or PromptRegistryPaths()

    rules_lines: list[str] = []
    for rule_file in _iter_files_sorted(registry_paths.rules_dir, "*.mdc"):
        content = _read_text(rule_file)
        scope = _extract_rule_scope(content)
        rules_lines.append(f"- {rule_file.name} (scope={scope})")

    skill_lines: list[str] = []
    for skill_file in _iter_files_sorted(registry_paths.skills_dir, "**/SKILL.md"):
        content = _read_text(skill_file)
        relative = skill_file.relative_to(registry_paths.skills_dir).as_posix()
        inferred_name = relative.replace("/SKILL.md", "")
        skill_name = _extract_skill_name(content, inferred_name)
        skill_lines.append(f"- {skill_name}")

    rules_blob = "\n".join(rules_lines) if rules_lines else "- none"
    skills_blob = "\n".join(skill_lines) if skill_lines else "- none"

    return (
        "[GLOBAL_SYSTEM_STATIC]\n"
        "CAVEMAN_DEFAULT=French concise unless detail/Jira deliverable requested.\n"
        "CONSUMPTION_REPORT=mandatory; enforced by stop hook stop-compliance.py.\n"
        "TASK_BRIEF=Skill+[CONTEXT] excerpts+[AC]+MCP class; enforced on Task preToolUse.\n"
        "TOKEN_BUDGET_GUARDRAIL=active; upstream report runs POST_BLOCK_1_STATIC on Task.\n"
        "ALWAYS_ON_RULES=subagent-usage,diff-only-protocol,token-budget-guardrail,mcp-availability-check\n"
        "SELECTIVE_RULES=consumption-report,caveman-default,subagent-skill-routing,code-review-graph,rtk-cli-tokens,jira-*\n"
        "GLOBAL_RULE_REGISTRY:\n"
        f"{rules_blob}\n"
        "GLOBAL_SKILL_REGISTRY:\n"
        f"{skills_blob}\n"
        "[/GLOBAL_SYSTEM_STATIC]"
    )
