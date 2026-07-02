#!/usr/bin/env python3
"""
Deterministic upstream token-budget guardrail report (no LLM).
Injected after BLOCK_1_STATIC in the Task compression pipeline.
"""
from __future__ import annotations

import re
from typing import Any

GUARDRAIL_VERSION = "1"
LARGE_FILE_LINE_THRESHOLD = 500
LARGE_PROMPT_CHAR_THRESHOLD = 8000
LARGE_PROMPT_TOKEN_THRESHOLD = 2000


def estimate_tokens(text: str) -> int:
    if not text:
        return 0
    return max(1, (len(text) + 3) // 4)


def _normalize_streak(value: Any) -> int:
    try:
        streak = int(value)
    except (TypeError, ValueError):
        return 0
    return max(0, min(streak, 9))


def _extract_guardrail_state(tool_input: dict[str, Any]) -> tuple[int, str]:
    raw = tool_input.get("guardrail_state")
    if not isinstance(raw, dict):
        return 0, ""
    streak = _normalize_streak(raw.get("failure_streak"))
    kind = str(raw.get("last_failure_kind") or "").strip().lower()[:40]
    return streak, kind


def _prompt_signals(prompt: str, description: str) -> dict[str, bool]:
    blob = f"{prompt}\n{description}".lower()
    return {
        "mentions_explore": "subagent_type" in blob and "explore" in blob,
        "mentions_large_read": bool(
            re.search(r"\b(read|open|load)\b.{0,40}\b(file|entire|whole)\b", blob)
        ),
        "mentions_test_retry": bool(re.search(r"\b(pytest|jest|cargo test|npm test|retry)\b", blob)),
        "mentions_diff_only": "diff-only" in blob or "search/replace" in blob,
        "has_file_paths": bool(re.search(r"[\w./-]+\.(py|ts|tsx|js|go|rs|java|mdc|md)\b", blob)),
    }


def _risk_level(
    *,
    subagent_type: str,
    prompt_tokens: int,
    signals: dict[str, bool],
    failure_streak: int,
) -> str:
    if failure_streak >= 2:
        return "high"
    agent_type = subagent_type.strip().lower()
    if agent_type == "explore" or prompt_tokens >= LARGE_PROMPT_TOKEN_THRESHOLD:
        return "high"
    if agent_type in {"generalpurpose", "shell"} or signals["mentions_large_read"]:
        return "medium"
    return "low"


def build_upstream_guardrail_report(
    *,
    subagent_type: str = "",
    prompt: str = "",
    description: str = "",
    tool_input: dict[str, Any] | None = None,
) -> str:
    """
    Build a compact deterministic guardrail block for subagent prompts.
    """
    tool_input = tool_input or {}
    failure_streak, last_failure_kind = _extract_guardrail_state(tool_input)
    prompt_tokens = estimate_tokens(prompt)
    signals = _prompt_signals(prompt, description)
    agent_type = str(
        subagent_type
        or tool_input.get("subagent_type")
        or tool_input.get("subagentType")
        or tool_input.get("type")
        or ""
    ).strip()
    risk = _risk_level(
        subagent_type=agent_type,
        prompt_tokens=prompt_tokens,
        signals=signals,
        failure_streak=failure_streak,
    )
    roi_gate = (
        agent_type.lower() == "explore"
        or signals["mentions_large_read"]
        or len(prompt) >= LARGE_PROMPT_CHAR_THRESHOLD
    )
    loop_halt = failure_streak >= 2

    lines = [
        "[TOKEN_BUDGET_GUARDRAIL_REPORT]",
        f"version={GUARDRAIL_VERSION}",
        "phase=POST_BLOCK_1_STATIC",
        f"subagent_type={agent_type or 'unspecified'}",
        f"prompt_tokens_est={prompt_tokens}",
        f"risk={risk}",
        f"roi_gate_required={'yes' if roi_gate else 'no'}",
        f"loop_halt_active={'yes' if loop_halt else 'no'}",
        f"failure_streak={failure_streak}",
    ]
    if last_failure_kind:
        lines.append(f"last_failure_kind={last_failure_kind}")

    lines.extend(
        [
            "",
            "MANDATORY_GATES:",
            "1. ROI: Before Read>500 lines or explore Task — prove rtk grep/find or scoped read failed.",
            "2. LOOP: failure_streak>=2 → STOP; summarize impasse; ask human (no auto 3rd try).",
            "4. OUTPUT: code edits → StrReplace or SEARCH/REPLACE blocks; Write blocked on existing files.",
        ]
    )
    if loop_halt:
        lines.append("3. HALT_NOW: loop_halt_active=yes — do not retry; return impasse to parent.")
    else:
        lines.append(
            "3. RETRY: At most one more attempt on same track if streak==1 and hypothesis changed."
        )

    lines.extend(
        [
            "",
            "POLICY_REF: rules/token-budget-guardrail.mdc | skills/token-budget-guardrail/SKILL.md",
            "[/TOKEN_BUDGET_GUARDRAIL_REPORT]",
        ]
    )
    return "\n".join(lines)


def analyze_guardrail_launch(
    *,
    subagent_type: str = "",
    prompt: str = "",
    description: str = "",
    tool_input: dict[str, Any] | None = None,
    after_tokens: int = 0,
) -> dict[str, Any]:
    """
    Telemetry snapshot for token-budget-guardrail on a Task launch.
    """
    tool_input = tool_input or {}
    failure_streak, last_failure_kind = _extract_guardrail_state(tool_input)
    prompt_tokens = estimate_tokens(prompt)
    signals = _prompt_signals(prompt, description)
    agent_type = str(
        subagent_type
        or tool_input.get("subagent_type")
        or tool_input.get("subagentType")
        or tool_input.get("type")
        or ""
    ).strip()
    risk = _risk_level(
        subagent_type=agent_type,
        prompt_tokens=prompt_tokens,
        signals=signals,
        failure_streak=failure_streak,
    )
    roi_gate = (
        agent_type.lower() == "explore"
        or signals["mentions_large_read"]
        or len(prompt) >= LARGE_PROMPT_CHAR_THRESHOLD
    )
    loop_halt = failure_streak >= 2
    intercepted = loop_halt or (roi_gate and risk == "high")

    avoided_tokens = 0
    if loop_halt:
        extra_cycles = max(1, 4 - failure_streak)
        per_cycle = prompt_tokens + max(after_tokens, prompt_tokens // 3)
        avoided_tokens = extra_cycles * per_cycle
    elif intercepted and roi_gate:
        avoided_tokens = int(prompt_tokens * 0.35 + max(after_tokens, prompt_tokens // 4))

    return {
        "guardrail_intercepted": intercepted,
        "guardrail_loop_halt": loop_halt,
        "guardrail_roi_gate": roi_gate,
        "guardrail_risk": risk,
        "guardrail_failure_streak": failure_streak,
        "guardrail_last_failure_kind": last_failure_kind,
        "guardrail_avoided_tokens": avoided_tokens,
        "guardrail_prompt_tokens_est": prompt_tokens,
    }
