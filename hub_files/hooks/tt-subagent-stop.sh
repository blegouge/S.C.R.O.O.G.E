#!/usr/bin/env bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export ANTIGRAVITY_TT_EVENT=subagentStop
export CURSOR_TT_EVENT=subagentStop
exec python3 "${SCRIPT_DIR}/token-telemetry.py"

