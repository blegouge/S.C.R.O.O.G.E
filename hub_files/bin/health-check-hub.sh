#!/usr/bin/env bash
# Health check for the global Cursor IA hub (~/.cursor).
# Usage: health-check-hub.sh [--json] [--full]
set -euo pipefail

CURSOR_HOME="${ANTIGRAVITY_HOME:-${CURSOR_HOME:-${HOME}/.gemini/antigravity}}"
JSON_MODE=0
FULL_MODE=0

for arg in "$@"; do
  case "$arg" in
    --json) JSON_MODE=1 ;;
    --full) FULL_MODE=1 ;;
    -h|--help)
      cat <<'EOF'
health-check-hub.sh — verify Cursor IA hub (RTK, venv, CRG, MCP, hooks)

Usage:
  health-check-hub.sh           Quick checks (default)
  health-check-hub.sh --full    + unit tests, claw benchmark smoke
  health-check-hub.sh --json    Machine-readable summary on stdout

Exit codes: 0 OK | 1 warnings | 2 failures
EOF
      exit 0
      ;;
  esac
done

PASS=0
WARN=0
FAIL=0
declare -a RESULTS=()

record() {
  local status="$1" id="$2" msg="$3"
  RESULTS+=("${status}|${id}|${msg}")
  case "$status" in
    PASS) PASS=$((PASS + 1)) ;;
    WARN) WARN=$((WARN + 1)) ;;
    FAIL) FAIL=$((FAIL + 1)) ;;
  esac
}

check_file() {
  local id="$1" path="$2" required="${3:-1}"
  if [[ -f "$path" ]]; then
    record PASS "$id" "present: $path"
    return 0
  fi
  if [[ "$required" == "1" ]]; then
    record FAIL "$id" "missing: $path"
  else
    record WARN "$id" "optional missing: $path"
  fi
  return 1
}

check_executable() {
  local id="$1" path="$2"
  if [[ -x "$path" ]]; then
    record PASS "$id" "executable: $path"
    return 0
  fi
  if [[ -f "$path" ]]; then
    record WARN "$id" "not executable: $path (chmod +x)"
  else
    record FAIL "$id" "missing: $path"
  fi
  return 1
}

check_cmd() {
  local id="$1" cmd="$2" required="${3:-1}"
  if command -v "$cmd" >/dev/null 2>&1; then
    record PASS "$id" "on PATH: $(command -v "$cmd")"
    return 0
  fi
  if [[ "$required" == "1" ]]; then
    record FAIL "$id" "not on PATH: $cmd"
  else
    record WARN "$id" "optional not on PATH: $cmd"
  fi
  return 1
}

# --- Hub layout ---
check_file hub_hooks_json "${CURSOR_HOME}/hooks.json" || true
check_file hub_agent "${CURSOR_HOME}/AGENT.md" 0 || true
check_file hub_compression_env "${CURSOR_HOME}/compression.env" 0 || true
check_file hub_compression_example "${CURSOR_HOME}/compression.env.example" || true
check_file hub_mcp "${CURSOR_HOME}/mcp.json" || true
check_file hub_mcp_secrets_example "${CURSOR_HOME}/mcp.secrets.env.example" || true
check_file hub_mcp_wrapper "${CURSOR_HOME}/bin/mcp-env-exec.sh" || true
check_executable mcp_wrapper_exec "${CURSOR_HOME}/bin/mcp-env-exec.sh" || true

if [[ -d "${CURSOR_HOME}/rules" ]]; then
  rule_count=$(find "${CURSOR_HOME}/rules" -maxdepth 1 -name '*.mdc' 2>/dev/null | wc -l | tr -d ' ')
  record PASS rules_dir "${rule_count} rule(s) in rules/"
else
  record FAIL rules_dir "missing rules/"
fi

if [[ -d "${CURSOR_HOME}/skills" ]]; then
  skill_count=$(find "${CURSOR_HOME}/skills" -name 'SKILL.md' 2>/dev/null | wc -l | tr -d ' ')
  record PASS skills_dir "${skill_count} skill(s) in skills/"
else
  record FAIL skills_dir "missing skills/"
fi

# --- Rules ↔ skills SSOT (stub must reference canonical file) ---
check_ssot_pair() {
  local id="$1" rule_file="$2" canonical="$3"
  local rule_path="${CURSOR_HOME}/rules/${rule_file}"
  local canon_path="${CURSOR_HOME}/${canonical}"
  if [[ ! -f "$rule_path" ]]; then
    record FAIL "$id" "missing rule: rules/${rule_file}"
    return 1
  fi
  if [[ ! -f "$canon_path" ]]; then
    record FAIL "$id" "missing canonical: ${canonical}"
    return 1
  fi
  if grep -qF "${canonical}" "$rule_path" 2>/dev/null; then
    record PASS "$id" "rules/${rule_file} → ${canonical}"
    return 0
  fi
  record FAIL "$id" "rules/${rule_file} does not reference ${canonical}"
  return 1
}

check_ssot_pair ssot_token_budget "token-budget-guardrail.mdc" "skills/token-budget-guardrail/SKILL.md" || true
check_ssot_pair ssot_code_review_graph "code-review-graph.mdc" "skills/code-review-graph/SKILL.md" || true
check_ssot_pair ssot_diff_only "diff-only-protocol.mdc" "src/rules/diff_protocol.md" || true
check_ssot_pair ssot_skills_routing "subagent-skill-routing.mdc" "src/rules/skills_routing.md" || true
check_file ssot_doc "${CURSOR_HOME}/docs/RULES-SKILLS-SSOT.md" || true
check_file ssot_routing_catalog "${CURSOR_HOME}/src/rules/skills_routing.md" || true

# --- hooks.json parse ---
if command -v python3 >/dev/null 2>&1 && [[ -f "${CURSOR_HOME}/hooks.json" ]]; then
  if python3 -c "import json; json.load(open('${CURSOR_HOME}/hooks.json'))" 2>/dev/null; then
    record PASS hooks_json_valid "hooks.json parses as JSON"
  else
    record FAIL hooks_json_valid "hooks.json invalid JSON"
  fi
fi

# Hook scripts (relative to CURSOR_HOME)
HOOK_SCRIPTS=(
  hooks/semantic-compress-pretool.sh
  hooks/stop-compliance.sh
  hooks/diff-only-after-response.sh
  hooks/tt-after-response.sh
  hooks/tt-posttool.sh
  hooks/token-telemetry.py
  hooks/stop-compliance.py
  hooks/semantic-compress-pretool.py
)
for rel in "${HOOK_SCRIPTS[@]}"; do
  base=$(basename "$rel")
  if [[ "$rel" == *.sh ]]; then
    check_executable "hook_${base}" "${CURSOR_HOME}/${rel}" || true
  else
    check_file "hook_${base}" "${CURSOR_HOME}/${rel}" || true
  fi
done

# --- RTK ---
check_cmd rtk rtk 0
if command -v rtk >/dev/null 2>&1; then
  if rtk gain >/dev/null 2>&1; then
    record PASS rtk_gain "rtk gain runs"
  else
    record WARN rtk_gain "rtk installed but 'rtk gain' failed"
  fi
else
  record WARN rtk "RTK not installed — Shell hook preToolUse may fail"
fi

# --- Python / compression venv ---
check_cmd python3 python3
VENV_PY="${CURSOR_HOME}/token-telemetry/.venv-desktop/bin/python"
check_file venv_desktop "$VENV_PY" 0 || true
if [[ -x "$VENV_PY" ]]; then
  if "$VENV_PY" -c "import claw_compactor" 2>/dev/null; then
    record PASS claw_import "claw-compactor import OK in .venv-desktop"
  else
    record WARN claw_import "claw-compactor not in .venv-desktop — run pip install -r requirements-desktop.txt"
  fi
fi

check_executable claw_cli "${CURSOR_HOME}/bin/claw-compactor" 0 || true

# --- Validators (src) ---
for mod in task_brief_validator consumption_report_validator; do
  if [[ -f "${CURSOR_HOME}/src/utils/${mod}.py" ]]; then
    record PASS "validator_${mod}" "present"
  else
    record FAIL "validator_${mod}" "missing src/utils/${mod}.py"
  fi
done

# --- MCP secrets ---
SECRETS="${CURSOR_HOME}/mcp.secrets.env"
if [[ -f "$SECRETS" ]]; then
  perms=$(stat -f '%OLp' "$SECRETS" 2>/dev/null || stat -c '%a' "$SECRETS" 2>/dev/null || echo "?")
  if [[ "$perms" == "600" || "$perms" == "0600" ]]; then
    record PASS mcp_secrets_perms "mcp.secrets.env mode 600"
  else
    record WARN mcp_secrets_perms "mcp.secrets.env should be chmod 600 (got ${perms})"
  fi
  # Warn if empty required keys
  empty_keys=0
  while IFS= read -r line; do
    [[ "$line" =~ ^export\ [A-Z_]+=\"\"$ ]] && empty_keys=$((empty_keys + 1))
  done < <(grep '^export ' "$SECRETS" 2>/dev/null || true)
  if [[ "$empty_keys" -gt 0 ]]; then
    record WARN mcp_secrets_empty "${empty_keys} empty export(s) in mcp.secrets.env"
  else
    record PASS mcp_secrets_filled "mcp.secrets.env has values"
  fi
else
  record WARN mcp_secrets "mcp.secrets.env missing — copy from mcp.secrets.env.example"
fi

# mcp.json must not contain obvious secrets
mcp_file=""
if [[ -f "${CURSOR_HOME}/mcp.json" ]]; then
  mcp_file="${CURSOR_HOME}/mcp.json"
elif [[ -f "${CURSOR_HOME}/mcp_config.json" ]]; then
  mcp_file="${CURSOR_HOME}/mcp_config.json"
fi

if [[ -n "$mcp_file" ]] && command -v python3 >/dev/null 2>&1; then
  if python3 - "$mcp_file" <<'PY' 2>/dev/null
import json, re, sys
from pathlib import Path
p = Path(sys.argv[1])
text = p.read_text()
data = json.loads(text)
blob = json.dumps(data)
patterns = [r'ghp_', r'glpat-', r'glsa_', r'password', r'api_key', r'api_token']
# Allow key names in env without values — crude check for literal secrets
for pat in patterns:
    if re.search(pat, blob, re.I) and re.search(pat + r'["\']?\s*:\s*["\'][^"\']{8,}', blob, re.I):
        sys.exit(1)
sys.exit(0)
PY
  then
    record PASS mcp_json_secrets "no obvious inline secrets in $(basename "$mcp_file")"
  else
    record FAIL mcp_json_secrets "possible secrets still in $(basename "$mcp_file") — move to mcp.secrets.env"
  fi
fi

# --- code-review-graph ---
check_cmd uvx uvx 0
check_cmd crg code-review-graph 0
if command -v code-review-graph >/dev/null 2>&1; then
  if code-review-graph status >/dev/null 2>&1; then
    record PASS crg_status "code-review-graph status OK (cwd may be empty graph)"
  else
    record WARN crg_status "code-review-graph status failed in $(pwd)"
  fi
fi

# --- Token telemetry ---
check_file telemetry_events "${CURSOR_HOME}/token-telemetry/events.jsonl" 0 || true
check_file telemetry_report "${CURSOR_HOME}/token-telemetry/report.py" || true
if [[ -f "${CURSOR_HOME}/token-telemetry/report.py" ]] && command -v python3 >/dev/null 2>&1; then
  if python3 "${CURSOR_HOME}/token-telemetry/report.py" >/dev/null 2>&1; then
    record PASS telemetry_report_run "report.py runs"
  else
    record WARN telemetry_report_run "report.py failed"
  fi
fi

# --- Node (MCP npx) ---
check_cmd node node 0
check_cmd npx npx 0

# --- compression.env TASK_BRIEF ---
if [[ -f "${CURSOR_HOME}/compression.env" ]]; then
  if grep -q 'TASK_BRIEF_ENFORCE' "${CURSOR_HOME}/compression.env" 2>/dev/null; then
    record PASS task_brief_env "TASK_BRIEF_ENFORCE set in compression.env"
  else
    record WARN task_brief_env "add TASK_BRIEF_ENFORCE=deny to compression.env"
  fi
fi

# --- Subagent stop telemetry ---
if [[ -f "${CURSOR_HOME}/bin/diagnose-subagent-telemetry.sh" ]]; then
  sub_diag=$(python3 - "${CURSOR_HOME}" <<'PY'
import json, sys
from pathlib import Path
p = Path(sys.argv[1]) / "token-telemetry" / "events.jsonl"
launches = stops = hook = fallback = 0
if p.is_file():
    for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            continue
        ev = r.get("event")
        if ev in ("subagentLaunch", "preToolUseCompression"):
            launches += 1
        if ev == "subagentStop":
            stops += 1
            src = r.get("subagent_stop_source")
            if src == "hook":
                hook += 1
            elif src == "postToolUse_fallback":
                fallback += 1
print(f"{launches}|{stops}|{hook}|{fallback}")
PY
)
  IFS='|' read -r sg_launch sg_stop sg_hook sg_fallback <<< "$sub_diag"
  if [[ "${sg_launch}" -eq 0 ]]; then
    record PASS subagent_telemetry "no Task launches yet (stop tracking ready)"
  elif [[ "${sg_stop}" -ge "${sg_launch}" ]]; then
    record PASS subagent_telemetry "stop coverage ${sg_stop}/${sg_launch} (hook=${sg_hook} fallback=${sg_fallback})"
  elif [[ "${sg_fallback}" -gt 0 || "${sg_stop}" -gt 0 ]]; then
    record WARN subagent_telemetry "partial stop coverage ${sg_stop}/${sg_launch} — run diagnose-subagent-telemetry.sh"
  else
    record WARN subagent_telemetry "0 stops for ${sg_launch} launches — hook inactive; fallback applies on next Task"
  fi
  check_executable diagnose_subagent "${CURSOR_HOME}/bin/diagnose-subagent-telemetry.sh" 0 || true
fi

# --- Full mode: unit tests ---
if [[ "$FULL_MODE" == "1" ]] && command -v python3 >/dev/null 2>&1; then
  if PYTHONPATH="${CURSOR_HOME}/src" python3 -m unittest discover -s "${CURSOR_HOME}/src/utils" -p 'test_*.py' -q 2>/dev/null; then
    record PASS unit_tests "src/utils tests pass"
  else
    record FAIL unit_tests "src/utils tests failed"
  fi
fi

# --- Output ---
EXIT=0
if [[ "$FAIL" -gt 0 ]]; then EXIT=2
elif [[ "$WARN" -gt 0 ]]; then EXIT=1
fi

if [[ "$JSON_MODE" == "1" ]]; then
  python3 - <<PY
import json
results = """$(printf '%s\n' "${RESULTS[@]}")""".strip().splitlines()
rows = []
for line in results:
    if not line: continue
    status, id_, msg = line.split('|', 2)
    rows.append({"status": status, "id": id_, "message": msg})
print(json.dumps({
    "cursor_home": "${CURSOR_HOME}",
    "pass": ${PASS},
    "warn": ${WARN},
    "fail": ${FAIL},
    "exit_code": ${EXIT},
    "checks": rows,
}, indent=2))
PY
  exit "$EXIT"
fi

echo "════════════════════════════════════════════════════════════"
echo " Cursor IA hub health check"
echo " Home: ${CURSOR_HOME}"
echo "════════════════════════════════════════════════════════════"
for line in "${RESULTS[@]}"; do
  status=${line%%|*}
  rest=${line#*|}
  id=${rest%%|*}
  msg=${rest#*|}
  case "$status" in
    PASS) icon="✓" ;;
    WARN) icon="!" ;;
    FAIL) icon="✗" ;;
  esac
  printf " %s %-28s %s\n" "$icon" "$id" "$msg"
done
echo "────────────────────────────────────────────────────────────"
echo " PASS=${PASS}  WARN=${WARN}  FAIL=${FAIL}  → exit ${EXIT}"
echo ""
echo "Next: docs/ONBOARDING-RUNBOOK.md · rtk gain · token-telemetry/report.py"
exit "$EXIT"
