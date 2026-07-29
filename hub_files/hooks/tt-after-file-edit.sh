#!/usr/bin/env bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOME_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

# shellcheck source=scrooge-source.sh
source "${SCRIPT_DIR}/scrooge-source.sh"
scrooge_export_source "${HOME_DIR}"

export ANTIGRAVITY_TT_EVENT=afterFileEdit
export CURSOR_TT_EVENT=afterFileEdit
export CLAUDE_TT_EVENT=afterFileEdit
export CODEX_TT_EVENT=afterFileEdit

PYTHON_BIN="${HOME_DIR}/token-telemetry/.venv-desktop/bin/python"
if [[ -x "${PYTHON_BIN}" ]]; then
  exec "${PYTHON_BIN}" "${SCRIPT_DIR}/token-telemetry.py"
fi
exec python3 "${SCRIPT_DIR}/token-telemetry.py"
