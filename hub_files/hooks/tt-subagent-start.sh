#!/usr/bin/env bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export CODEX_TT_EVENT=subagentStart
exec python3 "${SCRIPT_DIR}/token-telemetry.py"
