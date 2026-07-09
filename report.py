#!/usr/bin/env python3
"""Terminal summary of events without server."""

from __future__ import annotations

import argparse
import json
import json as _json
import os
import pathlib

from rtk_resolver import resolve_rtk_command
from telemetry_metrics import summarize_layer_kpis, summarize_report, summarize_stack_kpis
from telemetry_paths import resolve_log_file


def load_rows(path: pathlib.Path) -> list[dict]:
    if not path.is_file():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def main() -> None:
    p = argparse.ArgumentParser(description="Summary of events.jsonl (proxy tokens)")
    p.add_argument(
        "--source",
        type=str,
        choices=["cursor", "antigravity", "claude", "gemini", "hermes", "codex"],
        default="cursor",
        help="Telemetry data source",
    )
    p.add_argument(
        "--file",
        type=pathlib.Path,
        default=None,
        help="JSONL path (resolved via --source by default)",
    )
    args = p.parse_args()

    if args.file is None:
        if args.source == "antigravity":
            home = os.getenv("ANTIGRAVITY_HOME")
            if home:
                base = pathlib.Path(home)
            else:
                base = pathlib.Path.home() / ".gemini" / "antigravity"
            args.file = base / "token-telemetry" / "events.jsonl"
        elif args.source == "claude":
            home = os.getenv("CLAUDE_HOME")
            if home:
                base = pathlib.Path(home)
            else:
                base = pathlib.Path.home() / ".claude"
            args.file = base / "token-telemetry" / "events.jsonl"
        elif args.source == "codex":
            home = os.getenv("CODEX_HOME")
            if home:
                base = pathlib.Path(home)
            else:
                base = pathlib.Path.home() / ".codex"
            args.file = base / "token-telemetry" / "events.jsonl"
        else:
            args.file = resolve_log_file(source=args.source)
    rows = load_rows(args.file)
    if not rows:
        print("No data — file missing or empty:", args.file)
        return

    by_evt: dict[str, int] = {}
    total_approx = 0
    for r in rows:
        e = str(r.get("event", "?"))
        by_evt[e] = by_evt.get(e, 0) + int(r.get("approx_tokens") or 0)
        total_approx += int(r.get("approx_tokens") or 0)

    s = summarize_report(rows)
    rtk_gain = {"ok": False}
    rtk_cmd, _ = resolve_rtk_command()
    if rtk_cmd:
        import subprocess as _sp

        proc = _sp.run(
            [rtk_cmd[0], "gain", "-d", "--format", "json"], capture_output=True, text=True, timeout=8
        )
        if proc.returncode == 0:
            try:
                rtk_gain = _json.loads(proc.stdout)
                rtk_gain["ok"] = True
            except _json.JSONDecodeError:
                pass
    layers = summarize_layer_kpis(rows, rtk_gain=rtk_gain)
    blend = layers.get("blended", {})
    legacy = layers.get("legacy_global", {})
    print(
        "Score per layer (blend excluding chat):",
        f"saved≈{blend.get('savings_tokens', 0)} observed≈{blend.get('observed_tokens', 0)} pct={blend.get('pct', 0)}%",
    )
    print("Legacy global (including chat):", f"pct={legacy.get('pct', 0)}%")
    for key, label in [
        ("rtk_shell", "RTK"),
        ("task_compression", "Task compression"),
        ("guardrail_read", "Guardrail Read"),
        ("guardrail_task", "Guardrail Task"),
    ]:
        L = layers.get("layers", {}).get(key, {})
        print(f"  {label}: saved≈{L.get('savings_tokens', 0)} pct={L.get('pct', 0)}%")

    stack = summarize_stack_kpis(rows)
    edit = s["edit"]
    hook = s["hook_compression"]
    sub = s["subagents"]
    billed = s["parent_billed"]
    cov = s["consumption_coverage"]

    print("File:", args.file)
    print("Events:", s["event_count"])
    print("Sum proxy approx_tokens:", total_approx)
    print("Per event (proxy):", ", ".join(f"{k}: {v}" for k, v in sorted(by_evt.items())))
    print("Conso report coverage (afterAgentResponse):", f"{cov['with_report']}/{cov['responses']}")
    print("Complete report coverage (5 fields):", f"{cov.get('complete', 0)}/{cov['responses']}")
    print(
        "Hook compression (Task preToolUse):",
        f"runs={hook['runs']} saved≈{hook['saved_tokens']} claw={hook['claw']} llmlingua={hook['llmlingua']}",
    )
    print(
        "Subagents:",
        f"launch={sub['launch']} stop={sub['stop']} "
        f"(hook={sub.get('stop_hook', 0)} fallback={sub.get('stop_post_tool_fallback', 0)}) "
        f"coverage={sub.get('coverage_pct', 0)}% "
        f"prompt_proxy≈{sub['prompt_proxy_tokens']} out_proxy≈{sub['out_proxy_tokens']}",
    )
    if billed["count"]:
        print(
            "Parent billed (afterAgentResponse rows):",
            f"sum={billed['sum']} avg={billed['avg']}",
        )
    print("Stack optimizations (Task launches):")
    print(
        "  Git cache hit:",
        f"{stack['git_cache_hits']}/{stack['subagent_launches']}",
        f"· BLOCK_2 preserved≈{stack['git_cache_block2_tokens_preserved']} tok",
    )
    print(
        "  Guardrail circuit breaker:",
        f"intercepts={stack['guardrail_intercepts']}",
        f"loop_halts={stack['guardrail_loop_halts']}",
        f"· avoided cost≈{stack['guardrail_avoided_tokens']} tok",
    )
    idem = stack["idempotent_context_injected"]
    launches = stack["subagent_launches"]
    idem_pct = (100 * idem // launches) if launches else 0

    comp = s.get("compliance") or {}
    conso = comp.get("consumption") or {}
    brief = comp.get("task_brief") or {}

    print("Compliance (hooks):")
    print(
        "  Consumption report:",
        f"complete {conso.get('complete', 0)}/{conso.get('responses', 0)}",
        f"({conso.get('complete_pct', 0)}%)",
        f"· present {conso.get('present', 0)}/{conso.get('responses', 0)}",
        f"({conso.get('present_pct', 0)}%)",
    )
    print(
        "  Hook stop followups:",
        f"{conso.get('hook_followups', 0)}",
        f"· ok {conso.get('hook_ok', 0)}",
        f"· giveup {conso.get('hook_giveups', 0)}",
    )
    print(
        "  Task brief:",
        f"pass {brief.get('launches', 0)}/{brief.get('attempts', 0)}",
        f"({brief.get('pass_rate_pct', 0)}%)",
        f"· denied {brief.get('denied', 0)}",
    )
    print(
        "  Idempotence [IDEMPOTENT_CONTEXT_INJECTED]:",
        f"{idem}/{launches} ({idem_pct}%)",
    )
    print("Editing (hooks):")
    print(
        f"  afterFileEdit  ΔL+={edit['lines_added']}  ΔL−={edit['lines_removed']}  "
        f"passes={edit['passes']}"
    )
    print(
        f"  afterTabFileEdit  accepted={edit['tab_accepted']}  ΔL+ (Tab)≈{edit['tab_lines_added']}"
    )


if __name__ == "__main__":
    main()
