#!/usr/bin/env bash
# Run optimization stack verification (unit + hook integration).
# Usage: test-optimization-stack.sh [--quick]
set -euo pipefail

CURSOR_HOME="${CURSOR_HOME:-${HOME}/.cursor}"
QUICK=0

for arg in "$@"; do
  case "$arg" in
    --quick) QUICK=1 ;;
    -h|--help)
      cat <<'EOF'
test-optimization-stack.sh — verify Claw / Diff-Only / Adaptive Context stack

  test-optimization-stack.sh         Full: file checks + unittest + hook smoke
  test-optimization-stack.sh --quick  Unit tests only (no health-check --full)

Exit: 0 all pass | 1 failure
EOF
      exit 0
      ;;
  esac
done

FAIL=0
pass() { printf '  ✓ %s\n' "$1"; }
fail() { printf '  ✗ %s\n' "$1"; FAIL=1; }

echo "=== Cursor optimization stack tests ==="
echo "CURSOR_HOME=${CURSOR_HOME}"
echo

echo "--- Required files ---"
REQUIRED=(
  compression.env
  hooks.json
  hooks/semantic-compress-pretool.py
  hooks/diff-only-pretool-write.py
  hooks/diff-only-pretool-write.sh
  hooks/diff-only-apply.py
  src/utils/static_prompt_registry.py
  token-telemetry/telemetry_metrics.py
)
for rel in "${REQUIRED[@]}"; do
  if [[ -f "${CURSOR_HOME}/${rel}" ]]; then
    pass "${rel}"
  else
    fail "missing ${rel}"
  fi
done

echo
echo "--- compression.env (P0/P1) ---"
ENV_FILE="${CURSOR_HOME}/compression.env"
if grep -qE '^COMPRESSION_BACKEND=(claw|headroom)' "$ENV_FILE" 2>/dev/null; then
  pass "COMPRESSION_BACKEND=claw or headroom"
else
  fail "COMPRESSION_BACKEND not claw or headroom"
fi
if grep -q '^ADAPTIVE_CTX_STRUCTURE_MIN_INPUT_TOKENS=2500' "$ENV_FILE" 2>/dev/null; then
  pass "STRUCTURE_MIN_INPUT_TOKENS=2500"
else
  fail "missing STRUCTURE_MIN_INPUT_TOKENS"
fi

echo
echo "--- hooks.json matchers ---"
if python3 -c "
import json, sys
h = json.load(open('${CURSOR_HOME}/hooks.json'))
pre = h.get('hooks', {}).get('preToolUse', [])
m = {x.get('matcher') for x in pre if x.get('matcher')}
assert 'Task' in m and 'Write' in m
"; then
  pass "preToolUse: Task + Write"
else
  fail "hooks.json missing Task or Write matcher"
fi

echo
echo "--- Python unit + hook integration ---"
export CURSOR_HOME
export PYTHONPATH="${CURSOR_HOME}/src:${CURSOR_HOME}/token-telemetry"
if python3 -m unittest src.utils.test_optimization_stack -v 2>&1; then
  pass "unittest src.utils.test_optimization_stack"
else
  fail "unittest failed"
fi

if [[ "$QUICK" -eq 0 ]] && [[ -x "${CURSOR_HOME}/bin/health-check-hub.sh" ]]; then
  echo
  echo "--- health-check-hub (quick) ---"
  hc_out="$("${CURSOR_HOME}/bin/health-check-hub.sh" 2>&1)" || hc_ec=$?
  echo "$hc_out" | tail -8
  if echo "$hc_out" | grep -qE 'FAIL=0([^0-9]|$)'; then
    pass "health-check-hub.sh (FAIL=0; WARN ok)"
  else
    fail "health-check-hub.sh reported FAIL>0"
  fi
fi

echo
if [[ "$FAIL" -eq 0 ]]; then
  echo "All optimization stack checks passed."
  exit 0
fi
echo "Some checks failed."
exit 1
