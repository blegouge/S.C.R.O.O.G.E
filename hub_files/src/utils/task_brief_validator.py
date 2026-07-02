#!/usr/bin/env python3
"""
Validate Task/subagent briefs before launch (idempotency + MCP routing compliance).
"""
from __future__ import annotations

import re
from dataclasses import dataclass


_PATH_EXCERPT_RE = re.compile(
    r"(?im)"
    r"(?:"
    r"[\w./~-]+\.(?:py|ts|tsx|js|jsx|go|rs|java|mdc|md|json|yaml|yml|sh):\d+-\d+"
    r"|path:\s*[\w./~-]+"
    r"|\bpath/start-end\b"
    r")"
)
_SKILL_RE = re.compile(r"(?im)^\s*Skill:\s*\S+")
_AC_RE = re.compile(r"\[AC\]", re.IGNORECASE)
_CONTEXT_RE = re.compile(r"\[CONTEXT\]", re.IGNORECASE)
_RESCAN_ALLOWED_RE = re.compile(r"RESCAN:\s*allowed", re.IGNORECASE)
_MCP_CLASS_RE = re.compile(r"MCP task class:\s*(LOCAL_CODE|HYBRID|INTEGRATION)", re.IGNORECASE)
_MCP_ALLOWLIST_RE = re.compile(r"\[MCP_ALLOWLIST\]", re.IGNORECASE)
_IDEMPOTENT_TAG = "[IDEMPOTENT_CONTEXT_INJECTED]"


@dataclass(frozen=True, slots=True)
class BriefValidationResult:
    ok: bool
    violations: tuple[str, ...] = ()
    subagent_type: str = ""
    is_explore: bool = False
    has_context_excerpts: bool = False
    idempotent_ready: bool = False


def _normalize_subagent_type(value: str) -> str:
    return (value or "generalPurpose").strip().lower()


def validate_task_brief(
    prompt: str,
    *,
    subagent_type: str = "",
    description: str = "",
) -> BriefValidationResult:
    """Return structural compliance for subagent Task prompts."""
    blob = f"{prompt}\n{description}".strip()
    stype = _normalize_subagent_type(subagent_type)
    is_explore = stype == "explore"

    violations: list[str] = []

    if not _SKILL_RE.search(blob):
        violations.append("Missing `Skill: <skill-name>` line (required for routing and telemetry).")

    if not _AC_RE.search(blob):
        violations.append("Missing `[AC]` acceptance criteria section.")

    has_context = bool(_CONTEXT_RE.search(blob))
    has_rescan = bool(_RESCAN_ALLOWED_RE.search(blob))
    has_excerpts = bool(_PATH_EXCERPT_RE.search(blob))

    if not is_explore:
        if not has_context:
            violations.append(
                "Missing `[CONTEXT]` section — embed parent triage excerpts (`path:start-end`) "
                "or set `RESCAN: allowed` with reason."
            )
        elif not has_excerpts and not has_rescan:
            violations.append(
                "`[CONTEXT]` present but no `path:start-end` excerpts and no `RESCAN: allowed`."
            )
    elif not has_context and not has_rescan:
        violations.append(
            "Explore Task: add `[CONTEXT]` with scope boundaries or `RESCAN: allowed`."
        )

    if not _MCP_CLASS_RE.search(blob) and not _MCP_ALLOWLIST_RE.search(blob):
        violations.append(
            "Missing MCP routing — add `MCP task class: LOCAL_CODE|HYBRID|INTEGRATION` "
            "and `[MCP_ALLOWLIST]` (plus `[MCP_DENYLIST]` when LOCAL_CODE)."
        )

    ok = len(violations) == 0
    idempotent_ready = ok and has_excerpts

    return BriefValidationResult(
        ok=ok,
        violations=tuple(violations),
        subagent_type=stype,
        is_explore=is_explore,
        has_context_excerpts=has_excerpts,
        idempotent_ready=idempotent_ready,
    )


def build_deny_message(result: BriefValidationResult) -> str:
    """Agent-facing message when Task launch is blocked."""
    bullets = "\n".join(f"- {v}" for v in result.violations)
    template = (
        "Task subagent brief rejected by hook validation. Fix the prompt, then retry Task.\n\n"
        f"Violations:\n{bullets}\n\n"
        "Required skeleton:\n"
        "```\n"
        "Skill: spec-driven-idempotency\n"
        "MCP task class: LOCAL_CODE\n"
        "[MCP_ALLOWLIST]: code-review-graph\n"
        "[MCP_DENYLIST]: datadog, grafana, atlassian, bong, oxy\n"
        "[CONTEXT]\n"
        "path/to/file.py:120-145\n"
        "<verbatim excerpt>\n"
        "[GOALS] …\n"
        "[SCOPE] …\n"
        "[CONSTRAINTS] …\n"
        "[AC]\n"
        "- …\n"
        "```\n"
        "For greenfield mapping only: subagent_type=explore + `RESCAN: allowed` + narrow scope."
    )
    return template


def inject_idempotent_tag(prompt: str, result: BriefValidationResult) -> str:
    """Mark valid idempotent handoffs for telemetry when tag not already present."""
    if _IDEMPOTENT_TAG in prompt:
        return prompt
    if result.ok and result.has_context_excerpts:
        return f"{prompt.rstrip()}\n\n{_IDEMPOTENT_TAG}\n"
    return prompt
