#!/usr/bin/env bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export ANTIGRAVITY_TT_EVENT=afterFileEdit
export CURSOR_TT_EVENT=afterFileEdit
export CODEX_TT_EVENT=afterFileEdit
exec python3 "${SCRIPT_DIR}/token-telemetry.py"
