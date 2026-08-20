#!/usr/bin/env bash
# Load MCP secrets then exec the real server command (Cursor hooks do not inherit shell exports).
set -euo pipefail
# Prefer explicit hub env vars; otherwise use the hub that owns this script
# (…/<hub>/bin/mcp-env-exec.sh → …/<hub>/mcp.secrets.env).
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ACTIVE_HOME="${CLAUDE_HOME:-${GEMINI_HOME:-${ANTIGRAVITY_HOME:-${HERMES_HOME:-${CODEX_HOME:-${CURSOR_HOME:-${HUB_FROM_SCRIPT}}}}}}}"
SECRETS="${ACTIVE_HOME}/mcp.secrets.env"
if [[ -f "${SECRETS}" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "${SECRETS}"
  set +a
fi

# IDEs often launch MCP with a minimal PATH. npx uses `#!/usr/bin/env node`,
# so ensure common Node locations are searchable.
_mcp_path_prepend=()
if [[ -n "${MCP_NODE_BIN:-}" && -d "${MCP_NODE_BIN}" ]]; then
  _mcp_path_prepend+=("${MCP_NODE_BIN}")
fi
# nvm: pick the highest installed version bin if present
if [[ -d "${HOME}/.nvm/versions/node" ]]; then
  _nvm_latest="$(ls -1d "${HOME}/.nvm/versions/node"/v* 2>/dev/null | sort -V | tail -1 || true)"
  if [[ -n "${_nvm_latest}" && -d "${_nvm_latest}/bin" ]]; then
    _mcp_path_prepend+=("${_nvm_latest}/bin")
  fi
fi
for _d in /opt/homebrew/bin /usr/local/bin; do
  if [[ -d "${_d}" ]]; then
    _mcp_path_prepend+=("${_d}")
  fi
done
if ((${#_mcp_path_prepend[@]})); then
  export PATH="$(IFS=:; echo "${_mcp_path_prepend[*]}"):${PATH}"
fi

exec "$@"
