#!/usr/bin/env bash
# Diagnose subagent launch/stop telemetry gap (hook vs postToolUse fallback).
set -euo pipefail

CURSOR_HOME="${CURSOR_HOME:-${HOME}/.cursor}"
EVENTS="${CURSOR_HOME}/token-telemetry/events.jsonl"

echo "════════════════════════════════════════════════════════════"
echo " Subagent telemetry diagnostic"
echo " Log: ${EVENTS}"
echo "════════════════════════════════════════════════════════════"

python3 <<'PY'
import json
from pathlib import Path

home = Path.home() / ".cursor"
events_path = home / "token-telemetry" / "events.jsonl"
hooks = home / "hooks.json"

rows = []
if events_path.is_file():
    for line in events_path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            pass

launches = [r for r in rows if r.get("event") in ("subagentLaunch", "preToolUseCompression")]
stops = [r for r in rows if r.get("event") == "subagentStop"]
hook_stops = [r for r in stops if r.get("subagent_stop_source") == "hook"]
fallback_stops = [r for r in stops if r.get("subagent_stop_source") == "postToolUse_fallback"]
legacy_post = [r for r in rows if r.get("event") == "subagentPostToolUse"]

print(f"Launches (subagentLaunch):     {len(launches)}")
print(f"Stops (subagentStop):          {len(stops)}")
print(f"  via hook subagentStop:       {len(hook_stops)}")
print(f"  via postToolUse fallback:    {len(fallback_stops)}")
print(f"Legacy subagentPostToolUse:    {len(legacy_post)}")
if launches:
    pct = 100 * len(stops) // len(launches)
    print(f"Coverage launch→stop:          {pct}%")
print()

if hooks.is_file():
    data = json.loads(hooks.read_text())
    stop_hooks = data.get("hooks", {}).get("subagentStop", [])
    print(f"hooks.json subagentStop entries: {len(stop_hooks)}")
    for h in stop_hooks:
        print(f"  - {h.get('command', '?')}")
else:
    print("hooks.json: MISSING")

tt_stop = home / "hooks" / "tt-subagent-stop.sh"
if tt_stop.is_file():
    import os
    mode = oct(tt_stop.stat().st_mode)[-3:]
    print(f"tt-subagent-stop.sh: present mode={mode} executable={os.access(tt_stop, os.X_OK)}")
else:
    print("tt-subagent-stop.sh: MISSING")

print()
if len(launches) > 0 and len(hook_stops) == 0:
    print("DIAGNOSIS:")
    print("  • Cursor hook 'subagentStop' ne semble pas émettre d'événements sur cette install.")
    print("  • Mitigation active: postToolUse Task → subagentStop (fallback) après fix tool_name.")
    print("  • Vérifier Cursor → Output → Hooks après un vrai Task subagent.")
elif len(stops) == 0 and len(launches) == 0:
    print("DIAGNOSIS: aucun subagent Task enregistré — lancer un Task puis relancer ce script.")
else:
    print("DIAGNOSIS: télémétrie subagent OK ou partiellement couverte.")
PY

echo ""
echo "Simulate postToolUse Task (dry-run):"
echo '{"tool_name":"Task","tool_input":{"subagent_type":"explore","prompt":"Skill: test"},"tool_output":"done"}' \
  | CURSOR_TT_EVENT=postToolUse python3 "${CURSOR_HOME}/hooks/token-telemetry.py" 2>/dev/null || true
echo "(check last line of events.jsonl for subagentStop + postToolUse_fallback)"
