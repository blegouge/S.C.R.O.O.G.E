#!/usr/bin/env bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export ANTIGRAVITY_DIFF_HOOK_EVENT=afterAgentResponse
export CURSOR_DIFF_HOOK_EVENT=afterAgentResponse
export CODEX_DIFF_HOOK_EVENT=afterAgentResponse
exec python3 "${SCRIPT_DIR}/diff-only-apply.py"
