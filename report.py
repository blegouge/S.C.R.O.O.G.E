#!/usr/bin/env python3
"""Résumé terminal des évènements sans serveur."""

from __future__ import annotations

import argparse
import json
import os
import pathlib

from telemetry_metrics import summarize_report, summarize_stack_kpis
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
    p = argparse.ArgumentParser(description="Résumé events.jsonl (proxy tokens)")
    p.add_argument(
        "--source",
        type=str,
        choices=["cursor", "antigravity", "claude"],
        default="cursor",
        help="Source des données de télémétrie",
    )
    p.add_argument(
        "--file",
        type=pathlib.Path,
        default=None,
        help="chemin du jsonl (par défaut résolu via --source)",
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
        else:
            args.file = resolve_log_file()
    rows = load_rows(args.file)
    if not rows:
        print("Pas de données — fichier absent ou vide:", args.file)
        return

    by_evt: dict[str, int] = {}
    total_approx = 0
    for r in rows:
        e = str(r.get("event", "?"))
        by_evt[e] = by_evt.get(e, 0) + int(r.get("approx_tokens") or 0)
        total_approx += int(r.get("approx_tokens") or 0)

    s = summarize_report(rows)
    stack = summarize_stack_kpis(rows)
    edit = s["edit"]
    hook = s["hook_compression"]
    sub = s["subagents"]
    billed = s["parent_billed"]
    cov = s["consumption_coverage"]

    print("Fichier:", args.file)
    print("Évènements:", s["event_count"])
    print("Somme proxy approx_tokens:", total_approx)
    print("Par event (proxy):", ", ".join(f"{k}: {v}" for k, v in sorted(by_evt.items())))
    print("Coverage report conso (afterAgentResponse):", f"{cov['with_report']}/{cov['responses']}")
    print("Coverage report complet (5 champs):", f"{cov.get('complete', 0)}/{cov['responses']}")
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
    print("Stack optimisations (Task launches):")
    print(
        "  Git cache hit:",
        f"{stack['git_cache_hits']}/{stack['subagent_launches']}",
        f"· BLOCK_2 préservé≈{stack['git_cache_block2_tokens_preserved']} tok",
    )
    print(
        "  Guardrail disjoncteur:",
        f"intercepts={stack['guardrail_intercepts']}",
        f"loop_halts={stack['guardrail_loop_halts']}",
        f"· coût évité≈{stack['guardrail_avoided_tokens']} tok",
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
        f"complet {conso.get('complete', 0)}/{conso.get('responses', 0)}",
        f"({conso.get('complete_pct', 0)}%)",
        f"· présent {conso.get('present', 0)}/{conso.get('responses', 0)}",
        f"({conso.get('present_pct', 0)}%)",
    )
    print(
        "  Hook stop followups:",
        f"{conso.get('hook_followups', 0)}",
        f"· ok {conso.get('hook_ok', 0)}",
        f"· abandon {conso.get('hook_giveups', 0)}",
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
    print("Édition (hooks):")
    print(
        f"  afterFileEdit  ΔL+={edit['lines_added']}  ΔL−={edit['lines_removed']}  "
        f"passes={edit['passes']}"
    )
    print(
        f"  afterTabFileEdit  acceptés={edit['tab_accepted']}  "
        f"ΔL+ (Tab)≈{edit['tab_lines_added']}"
    )


if __name__ == "__main__":
    main()
