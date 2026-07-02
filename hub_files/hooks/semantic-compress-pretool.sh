#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOME_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Export Claude Code event marker for telemetry routing
export ANTIGRAVITY_TT_EVENT=preToolUse
export CURSOR_TT_EVENT=preToolUse
export CLAUDE_TT_EVENT=preToolUse

COMPRESSION_ENV="${HOME_DIR}/compression.env"
if [[ -f "${COMPRESSION_ENV}" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "${COMPRESSION_ENV}"
  set +a
fi

PYTHON_BIN="${HOME_DIR}/token-telemetry/.venv-desktop/bin/python"
HOOK_SCRIPT="${SCRIPT_DIR}/semantic-compress-pretool.py"

if [[ -x "${PYTHON_BIN}" ]]; then
  exec "${PYTHON_BIN}" "${HOOK_SCRIPT}"
fi

exec python3 "${HOOK_SCRIPT}"
