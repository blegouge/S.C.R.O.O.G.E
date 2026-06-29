#!/usr/bin/env bash
# Load MCP secrets then exec the real server command (Cursor hooks do not inherit shell exports).
set -euo pipefail
ACTIVE_HOME="${ANTIGRAVITY_HOME:-${CURSOR_HOME:-${HOME}/.gemini/antigravity}}"
SECRETS="${ACTIVE_HOME}/mcp.secrets.env"
if [[ -f "${SECRETS}" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "${SECRETS}"
  set +a
fi
exec "$@"
