#!/usr/bin/env bash
# Shared helper: resolve the active telemetry provider for a hook wrapper.
#
# Every agent receives its own deployment root (~/.cursor, ~/.claude, ~/.codex,
# ~/.gemini, ~/.gemini/antigravity, ~/.hermes), so the location of the running
# hook is the only unambiguous signal of who triggered it.
#
# Hook wrappers broadcast several *_TT_EVENT variables so a single script can be
# deployed to every agent. Those variables carry the event name only and must
# never be used to attribute an event to an agent.

# shellcheck shell=bash

scrooge_resolve_source() {
  # Nested roots first: ~/.gemini/antigravity lives inside ~/.gemini.
  case "${1:-}" in
    */.gemini/antigravity) printf 'antigravity' ;;
    */.claude) printf 'claude' ;;
    */.codex) printf 'codex' ;;
    */.hermes) printf 'hermes' ;;
    */.gemini) printf 'gemini' ;;
    */.cursor) printf 'cursor' ;;
    *) printf 'cursor' ;;
  esac
}

# Export SCROOGE_TELEMETRY_SOURCE unless the caller already pinned it.
scrooge_export_source() {
  if [[ -z "${SCROOGE_TELEMETRY_SOURCE:-}" ]]; then
    SCROOGE_TELEMETRY_SOURCE="$(scrooge_resolve_source "${1:-}")"
    export SCROOGE_TELEMETRY_SOURCE
  fi
}
