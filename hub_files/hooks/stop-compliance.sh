#!/usr/bin/env bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOME_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

COMPRESSION_ENV="${HOME_DIR}/compression.env"
if [[ -f "${COMPRESSION_ENV}" ]]; then
  set -a
  source "${COMPRESSION_ENV}"
  set +a
fi

export ANTIGRAVITY_COMPLIANCE_HOOK_EVENT=stop
export CURSOR_COMPLIANCE_HOOK_EVENT=stop
export CODEX_COMPLIANCE_HOOK_EVENT=stop

PYTHON_BIN="${HOME_DIR}/token-telemetry/.venv-desktop/bin/python"
if [[ -x "${PYTHON_BIN}" ]]; then
  exec "${PYTHON_BIN}" "${SCRIPT_DIR}/stop-compliance.py"
fi
exec python3 "${SCRIPT_DIR}/stop-compliance.py"
