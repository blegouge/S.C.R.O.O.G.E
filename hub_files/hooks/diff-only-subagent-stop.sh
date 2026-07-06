#!/usr/bin/env bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOME_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

export ANTIGRAVITY_DIFF_HOOK_EVENT=subagentStop
export CURSOR_DIFF_HOOK_EVENT=subagentStop
export CODEX_DIFF_HOOK_EVENT=subagentStop

PYTHON_BIN="${HOME_DIR}/token-telemetry/.venv-desktop/bin/python"
if [[ -x "${PYTHON_BIN}" ]]; then
  exec "${PYTHON_BIN}" "${SCRIPT_DIR}/diff-only-apply.py"
fi
exec python3 "${SCRIPT_DIR}/diff-only-apply.py"
