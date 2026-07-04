#!/usr/bin/env bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export ANTIGRAVITY_DIFF_HOOK_EVENT=subagentStop
export CURSOR_DIFF_HOOK_EVENT=subagentStop
export CODEX_DIFF_HOOK_EVENT=subagentStop
exec python3 "${SCRIPT_DIR}/diff-only-apply.py"
