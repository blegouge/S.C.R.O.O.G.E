#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOME_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

PYTHON_BIN="${HOME_DIR}/token-telemetry/.venv-desktop/bin/python"
HOOK_SCRIPT="${SCRIPT_DIR}/diff-only-pretool-write.py"

if [[ -x "${PYTHON_BIN}" ]]; then
  exec "${PYTHON_BIN}" "${HOOK_SCRIPT}"
fi

exec python3 "${HOOK_SCRIPT}"
