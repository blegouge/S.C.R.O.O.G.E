#!/usr/bin/env bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOME_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

export ANTIGRAVITY_TT_EVENT=afterTabFileEdit
export CURSOR_TT_EVENT=afterTabFileEdit
export CLAUDE_TT_EVENT=afterTabFileEdit

PYTHON_BIN="${HOME_DIR}/token-telemetry/.venv-desktop/bin/python"
if [[ -x "${PYTHON_BIN}" ]]; then
  exec "${PYTHON_BIN}" "${SCRIPT_DIR}/token-telemetry.py"
fi
exec python3 "${SCRIPT_DIR}/token-telemetry.py"

