#!/usr/bin/env python3
"""Shared KPI aggregation for events.jsonl (report.py + dashboard parity)."""

from __future__ import annotations

from typing import Any

SUBAGENT_LAUNCH_EVENTS = frozenset({"subagentLaunch", "preToolUseCompression"})
SUBAGENT_STOP_EVENT = "subagentStop"


def is_subagent_stop(row: dict[str, Any]) -> bool:
    return str(row.get("event", "")) == SUBAGENT_STOP_EVENT


def subagent_stop_breakdown(rows: list[dict[str, Any]]) -> dict[str, int]:
    """Count subagentStop rows by source (hook vs postToolUse fallback)."""
    stops = [r for r in rows if is_subagent_stop(r)]
    hook = sum(1 for r in stops if r.get("subagent_stop_source") == "hook")
    fallback = sum(1 for r in stops if r.get("subagent_stop_source") == "postToolUse_fallback")
    unknown = len(stops) - hook - fallback
    return {
        "stop_total": len(stops),
        "stop_hook": hook,
        "stop_post_tool_fallback": fallback,
        "stop_unknown_source": unknown,
    }


def is_subagent_launch(row: dict[str, Any]) -> bool:
    return str(row.get("event", "")) in SUBAGENT_LAUNCH_EVENTS


def hook_saved_tokens(row: dict[str, Any]) -> int:
    """Saved tokens for Task compression (end-to-end with legacy fallback)."""
    legacy = int(row.get("compression_saved_tokens") or 0)
    input_tok = int(row.get("compression_input_tokens") or 0)
    after_tok = int(row.get("compression_after_tokens") or row.get("approx_tokens") or 0)
    if input_tok > 0:
        return max(legacy, max(0, input_tok - after_tok))
    return legacy


def hook_overhead_tokens(row: dict[str, Any]) -> int:
    """Structural overhead from BLOCK_* wrapping (0 when light mode or net savings)."""
    explicit = row.get("compression_overhead_tokens")
    if isinstance(explicit, (int, float)):
        return max(0, int(explicit))
    input_tok = int(row.get("compression_input_tokens") or 0)
    after_tok = int(row.get("compression_after_tokens") or row.get("approx_tokens") or 0)
    return max(0, after_tok - input_tok)


def row_git_cache_hit(row: dict[str, Any]) -> bool:
    if row.get("compression_git_cache_hit") is True:
        return True
    return row.get("git_cache_hit") is True


def row_git_cache_tokens_preserved(row: dict[str, Any]) -> int:
    for key in (
        "git_cache_block2_tokens_preserved",
        "compression_block2_tokens_preserved",
        "block2_tokens_preserved",
    ):
        value = row.get(key)
        if isinstance(value, (int, float)) and value > 0:
            return int(value)
    if row_git_cache_hit(row):
        after = int(row.get("compression_after_tokens") or row.get("approx_tokens") or 0)
        return max(0, int(after * 0.12)) if after else 0
    return 0


def row_guardrail_loop_halt(row: dict[str, Any]) -> bool:
    return row.get("guardrail_loop_halt") is True


def row_guardrail_intercepted(row: dict[str, Any]) -> bool:
    if row.get("guardrail_intercepted") is True:
        return True
    if row_guardrail_loop_halt(row):
        return True
    if (
        row.get("guardrail_roi_gate") is True
        and str(row.get("guardrail_risk", "")).lower() == "high"
    ):
        return True
    return False


def row_guardrail_avoided_tokens(row: dict[str, Any]) -> int:
    value = row.get("guardrail_avoided_tokens")
    if isinstance(value, (int, float)):
        return max(0, int(value))
    if not row_guardrail_intercepted(row):
        return 0
    input_tok = int(row.get("compression_input_tokens") or 0)
    after_tok = int(row.get("compression_after_tokens") or row.get("approx_tokens") or 0)
    if row_guardrail_loop_halt(row):
        streak = int(row.get("guardrail_failure_streak") or 2)
        cycles = max(1, 4 - streak)
        return cycles * (input_tok + max(after_tok, input_tok // 3))
    return int(input_tok * 0.35 + max(after_tok, input_tok // 4))


def row_idempotent_context_injected(row: dict[str, Any]) -> bool:
    return row.get("idempotent_context_injected") is True


def summarize_stack_kpis(rows: list[dict[str, Any]]) -> dict[str, int]:
    """Aggregate Git cache, guardrail, and idempotency KPIs from launch events."""
    launches = [r for r in rows if is_subagent_launch(r)]
    light_launches = sum(1 for r in launches if str(r.get("compression_mode") or "") == "light")
    total_overhead = sum(hook_overhead_tokens(r) for r in launches)
    git_hits = sum(1 for r in launches if row_git_cache_hit(r))
    git_preserved = sum(row_git_cache_tokens_preserved(r) for r in launches if row_git_cache_hit(r))
    guardrail_intercepts = sum(1 for r in launches if row_guardrail_intercepted(r))
    guardrail_halts = sum(1 for r in launches if row_guardrail_loop_halt(r))
    guardrail_avoided = sum(row_guardrail_avoided_tokens(r) for r in launches)
    idem_injected = sum(1 for r in launches if row_idempotent_context_injected(r))
    launch_count = len(launches)
    return {
        "subagent_launches": launch_count,
        "compression_light_launches": light_launches,
        "compression_overhead_tokens": total_overhead,
        "git_cache_hits": git_hits,
        "git_cache_block2_tokens_preserved": git_preserved,
        "guardrail_intercepts": guardrail_intercepts,
        "guardrail_loop_halts": guardrail_halts,
        "guardrail_avoided_tokens": guardrail_avoided,
        "idempotent_context_injected": idem_injected,
    }


def summarize_compliance_kpis(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Compliance KPIs for Task brief validation and Consumption report."""
    responses = [r for r in rows if r.get("event") == "afterAgentResponse"]
    resp_n = len(responses)
    with_report = sum(1 for r in responses if r.get("consumption_present") is True)
    complete = sum(1 for r in responses if r.get("consumption_complete") is True)

    brief_events = [r for r in rows if r.get("event") == "taskBriefValidation"]
    brief_denied = sum(1 for r in brief_events if r.get("brief_valid") is False)
    brief_pass_logged = sum(1 for r in brief_events if r.get("brief_valid") is True)

    launches = sum(1 for r in rows if is_subagent_launch(r))
    brief_attempts = launches + brief_denied
    brief_pass_rate = (100 * launches // brief_attempts) if brief_attempts else 0

    conso_hook_events = [r for r in rows if r.get("event") == "consumptionReportCompliance"]
    conso_followups = sum(1 for r in conso_hook_events if r.get("consumption_enforced") is True)
    conso_giveups = sum(
        1
        for r in conso_hook_events
        if r.get("consumption_complete") is False and int(r.get("loop_count") or 0) >= 2
    )
    conso_ok_hook = sum(1 for r in conso_hook_events if r.get("consumption_complete") is True)

    stack = summarize_stack_kpis(rows)
    idem = stack["idempotent_context_injected"]
    launch_n = stack["subagent_launches"]
    idem_pct = (100 * idem // launch_n) if launch_n else 0

    return {
        "consumption": {
            "responses": resp_n,
            "present": with_report,
            "complete": complete,
            "present_pct": (100 * with_report // resp_n) if resp_n else 0,
            "complete_pct": (100 * complete // resp_n) if resp_n else 0,
            "hook_checks": len(conso_hook_events),
            "hook_followups": conso_followups,
            "hook_ok": conso_ok_hook,
            "hook_giveups": conso_giveups,
        },
        "task_brief": {
            "launches": launches,
            "denied": brief_denied,
            "attempts": brief_attempts,
            "pass_rate_pct": brief_pass_rate,
            "pass_logged": brief_pass_logged,
        },
        "idempotency": {
            "injected": idem,
            "launches": launch_n,
            "pct": idem_pct,
        },
    }


GUARDRAIL_READ_EVENTS = frozenset(
    {"guardrailReadBlocked", "guardrailReadScoped", "guardrailReadAllowed"}
)


def _layer_pct(savings: int, observed: int) -> float:
    total = savings + observed
    if total <= 0:
        return 0.0
    return round(100.0 * savings / total, 2)


def _rtk_daily_total(rtk_gain: dict[str, Any] | None, log_days: set[str]) -> tuple[int, bool]:
    if not rtk_gain or rtk_gain.get("ok") is not True:
        return 0, False
    daily = rtk_gain.get("daily")
    if not isinstance(daily, list):
        summary = rtk_gain.get("summary")
        if isinstance(summary, dict):
            return int(summary.get("total_saved") or 0), True
        return 0, True
    total = 0
    for row in daily:
        if not isinstance(row, dict):
            continue
        day = str(row.get("date") or "").strip()
        if log_days and day and day not in log_days:
            continue
        total += int(row.get("saved_tokens") or 0)
    return total, True


def rtk_hook_saved_tokens(row: dict[str, Any]) -> int:
    if str(row.get("event", "")) != "rtkShellRewrite":
        return 0
    value = row.get("rtk_saved_tokens")
    if isinstance(value, (int, float)):
        return max(0, int(value))
    before = int(row.get("rtk_before_tokens") or 0)
    after = int(row.get("rtk_after_tokens") or 0)
    return max(0, before - after)


def diff_only_saved_tokens(row: dict[str, Any]) -> int:
    if not str(row.get("event", "")).startswith("diffOnlyApply"):
        return 0
    diff = row.get("diff_only")
    if isinstance(diff, dict):
        return max(0, (int(diff.get("estimated_chars_saved") or 0) + 3) // 4)
    return max(0, (int(row.get("diff_only_chars_saved") or 0) + 3) // 4)


def guardrail_read_saved_tokens(row: dict[str, Any]) -> int:
    if str(row.get("event", "")) not in GUARDRAIL_READ_EVENTS:
        return 0
    return int(row.get("guardrail_avoided_tokens") or 0)


def _parse_log_days(rows: list[dict[str, Any]]) -> set[str]:
    days: set[str] = set()
    for row in rows:
        ts = str(row.get("ts") or "").strip()
        if len(ts) >= 10:
            days.add(ts[:10])
    return days


def summarize_layer_kpis(
    rows: list[dict[str, Any]],
    *,
    rtk_gain: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Per-layer savings vs layer-relevant observed volume (excludes parent chat)."""
    log_days = _parse_log_days(rows)

    shell_observed = 0
    read_observed = 0
    task_input_observed = 0
    task_compression_saved = 0
    diff_saved = 0
    guardrail_read_saved = 0
    guardrail_read_blocks = 0
    guardrail_task_saved = 0
    crg_saved = 0
    rtk_hook_saved = 0
    chat_observed = 0

    for row in rows:
        ev = str(row.get("event", ""))
        tool = str(row.get("tool") or row.get("tool_name") or "").strip()

        if ev == "postToolUse":
            tok = int(row.get("approx_tokens") or 0)
            if tool in {"Shell", "Bash"}:
                shell_observed += tok
            elif tool == "Read":
                read_observed += tok

        rtk_hook_saved += rtk_hook_saved_tokens(row)

        if ev == "afterAgentResponse":
            billed = int(row.get("billed_total_tokens") or 0)
            if billed > 0:
                chat_observed += billed
            else:
                inp = int(row.get("input_tokens") or 0)
                out = int(row.get("output_tokens") or 0)
                if inp or out:
                    chat_observed += inp + out
                else:
                    chat_observed += int(row.get("approx_tokens") or 0)

        if is_subagent_launch(row):
            task_compression_saved += hook_saved_tokens(row)
            task_input_observed += int(row.get("compression_input_tokens") or 0)
            guardrail_task_saved += row_guardrail_avoided_tokens(row)

        if ev == "codeReviewGraph":
            crg_saved += int(row.get("saved_tokens") or 0)

        diff_saved += diff_only_saved_tokens(row)
        guardrail_read_saved += guardrail_read_saved_tokens(row)
        if ev == "guardrailReadBlocked":
            guardrail_read_blocks += 1

    rtk_daily_saved, rtk_ok = _rtk_daily_total(rtk_gain, log_days)
    rtk_saved = max(rtk_daily_saved, rtk_hook_saved)
    rtk_ok = rtk_ok or rtk_hook_saved > 0

    layers: dict[str, dict[str, Any]] = {
        "rtk_shell": {
            "savings_tokens": rtk_saved,
            "observed_tokens": shell_observed,
            "pct": _layer_pct(rtk_saved, shell_observed),
            "available": rtk_ok,
            "events": sum(
                1
                for r in rows
                if (
                    r.get("event") == "postToolUse"
                    and str(r.get("tool") or "") in {"Shell", "Bash"}
                )
                or r.get("event") == "rtkShellRewrite"
            ),
            "hook_savings_tokens": rtk_hook_saved,
            "daily_savings_tokens": rtk_daily_saved,
        },
        "task_compression": {
            "savings_tokens": task_compression_saved,
            "observed_tokens": task_input_observed,
            "pct": _layer_pct(task_compression_saved, task_input_observed),
            "events": sum(1 for r in rows if is_subagent_launch(r)),
        },
        "guardrail_read": {
            "savings_tokens": guardrail_read_saved,
            "observed_tokens": read_observed,
            "pct": _layer_pct(guardrail_read_saved, read_observed),
            "blocked": guardrail_read_blocks,
        },
        "guardrail_task": {
            "savings_tokens": guardrail_task_saved,
            "observed_tokens": task_input_observed,
            "pct": _layer_pct(guardrail_task_saved, task_input_observed),
        },
        "diff_only": {
            "savings_tokens": diff_saved,
            "observed_tokens": 0,
            "pct": 0.0,
            "events": sum(1 for r in rows if str(r.get("event", "")).startswith("diffOnlyApply")),
        },
        "code_review_graph": {
            "savings_tokens": crg_saved,
            "observed_tokens": 0,
            "pct": 0.0,
            "events": sum(1 for r in rows if r.get("event") == "codeReviewGraph"),
        },
    }

    blended_savings = (
        rtk_saved
        + task_compression_saved
        + diff_saved
        + guardrail_read_saved
        + guardrail_task_saved
        + crg_saved
    )
    blended_observed = shell_observed + task_input_observed + read_observed

    legacy_observed = 0
    legacy_savings = blended_savings
    for row in rows:
        ev = str(row.get("event", ""))
        if ev in ("afterFileEdit", "afterTabFileEdit"):
            continue
        if ev.startswith("diffOnlyApply"):
            continue
        if ev == "afterAgentResponse":
            billed = int(row.get("billed_total_tokens") or 0)
            if billed > 0:
                legacy_observed += billed
            else:
                legacy_observed += int(row.get("approx_tokens") or 0)
        elif ev == "postToolUse":
            legacy_observed += int(row.get("approx_tokens") or 0)
        elif is_subagent_launch(row):
            legacy_observed += int(
                row.get("compression_after_tokens") or row.get("approx_tokens") or 0
            )
        elif ev == "subagentStop":
            legacy_observed += int(row.get("approx_tokens") or 0)

    return {
        "layers": layers,
        "blended": {
            "savings_tokens": blended_savings,
            "observed_tokens": blended_observed,
            "pct": _layer_pct(blended_savings, blended_observed),
            "note": "Parent chat excluded; measures tool/subagent surfaces only.",
        },
        "chat_parent": {
            "observed_tokens": chat_observed,
            "note": "afterAgentResponse proxy — not in blended pct (session history dominates).",
        },
        "legacy_global": {
            "savings_tokens": legacy_savings,
            "observed_tokens": legacy_observed,
            "pct": _layer_pct(legacy_savings, legacy_observed),
            "note": "Old KPI (includes chat) — often shows <1% when RTK missing.",
        },
    }


def summarize_report(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Single source of truth for report.py and dashboard /api/report-summary."""
    agent_la = agent_lr = agent_pass = tab_n = tab_la = 0
    hook_runs = hook_saved = hook_claw = hook_llm = 0
    sub_launch = sub_stop = sub_prompt_tok = sub_out_tok = 0
    sub_stop_hook = sub_stop_fallback = 0
    resp_n = resp_with_report = resp_complete = 0
    billed_sum = 0
    billed_n = 0
    latest_billed: int | None = None
    latest_in = latest_out = 0

    responses = [r for r in rows if r.get("event") == "afterAgentResponse"]
    if responses:
        latest = max(responses, key=lambda r: str(r.get("ts") or ""))
        billed = latest.get("billed_total_tokens")
        if isinstance(billed, int):
            latest_billed = billed
            latest_in = int(latest.get("input_tokens") or 0)
            latest_out = int(latest.get("output_tokens") or 0)

    crg_runs = crg_saved = 0
    crg_risk_sum = 0.0

    for r in rows:
        if r.get("event") == "afterFileEdit":
            agent_la += int(r.get("lines_added") or 0)
            agent_lr += int(r.get("lines_removed") or 0)
            agent_pass += 1
        if r.get("event") == "afterTabFileEdit":
            tab_n += 1
            tab_la += int(r.get("lines_added") or 0)
        if r.get("event") == "afterAgentResponse":
            resp_n += 1
            if r.get("consumption_present") is True:
                resp_with_report += 1
            if r.get("consumption_complete") is True:
                resp_complete += 1
            billed = r.get("billed_total_tokens")
            if isinstance(billed, int):
                billed_sum += billed
                billed_n += 1
        ev = str(r.get("event", ""))
        if ev == "codeReviewGraph":
            crg_runs += 1
            crg_saved += int(r.get("saved_tokens") or 0)
            crg_risk_sum += float(r.get("risk_score") or 0.0)
        if ev in SUBAGENT_LAUNCH_EVENTS:
            hook_runs += 1
            hook_saved += hook_saved_tokens(r)
            if r.get("compression_used_claw_compactor") is True:
                hook_claw += 1
            if r.get("compression_used_llmlingua") is True:
                hook_llm += 1
            sub_launch += 1
            sub_prompt_tok += int(r.get("compression_after_tokens") or r.get("approx_tokens") or 0)
        if ev == "subagentStop":
            sub_stop += 1
            sub_out_tok += int(r.get("approx_tokens") or 0)
            src = str(r.get("subagent_stop_source") or "")
            if src == "hook":
                sub_stop_hook += 1
            elif src == "postToolUse_fallback":
                sub_stop_fallback += 1

    stack = summarize_stack_kpis(rows)
    launches = stack["subagent_launches"]
    idem = stack["idempotent_context_injected"]
    idem_pct = (100 * idem // launches) if launches else 0

    return {
        "event_count": len(rows),
        "edit": {
            "lines_added": agent_la,
            "lines_removed": agent_lr,
            "passes": agent_pass,
            "tab_accepted": tab_n,
            "tab_lines_added": tab_la,
        },
        "consumption_coverage": {
            "with_report": resp_with_report,
            "complete": resp_complete,
            "responses": resp_n,
        },
        "hook_compression": {
            "runs": hook_runs,
            "saved_tokens": hook_saved,
            "claw": hook_claw,
            "llmlingua": hook_llm,
        },
        "code_review_graph": {
            "runs": crg_runs,
            "saved_tokens": crg_saved,
            "avg_risk": crg_risk_sum / crg_runs if crg_runs > 0 else 0.0,
        },
        "subagents": {
            "launch": sub_launch,
            "stop": sub_stop,
            "stop_hook": sub_stop_hook,
            "stop_post_tool_fallback": sub_stop_fallback,
            "prompt_proxy_tokens": sub_prompt_tok,
            "out_proxy_tokens": sub_out_tok,
            "coverage_pct": (100 * sub_stop // sub_launch) if sub_launch else 0,
        },
        "parent_billed": {
            "sum": billed_sum,
            "avg": billed_sum // billed_n if billed_n else 0,
            "count": billed_n,
            "latest": latest_billed,
            "latest_input": latest_in,
            "latest_output": latest_out,
        },
        "stack": {**stack, "idempotent_pct": idem_pct},
        "compliance": summarize_compliance_kpis(rows),
    }
