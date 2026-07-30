#!/usr/bin/env python3
"""
Global Cursor hook: apply Diff-Only SEARCH/REPLACE blocks from agent output.

Events:
  - afterAgentResponse (field `text`)
  - subagentStop (`summary` + optional transcript file)
  - stop (re-scan last response file if configured — optional)

Writes files on disk as a side effect. On subagentStop/stop failures, may return
`followup_message` so the agent can fix SEARCH mismatches.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

# Resolve home directory dynamically based on environment or script path
_HOME_DIR = os.getenv("CODEX_HOME") or os.getenv("ANTIGRAVITY_HOME") or os.getenv("CURSOR_HOME")
if _HOME_DIR:
    _HOME_PATH = Path(_HOME_DIR).resolve()
else:
    _HOME_PATH = Path(__file__).resolve().parent.parent

SRC_DIR = _HOME_PATH / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from utils.diff_applier import (  # pylint: disable=import-error
    append_telemetry,
    apply_text,
    extract_response_text,
    log_savings,
    parse_blocks,
    resolve_workspace_roots,
)
from utils.hook_utils import (
    hook_fail_safe,
    load_stdin_json,
)

DISABLE_ENV = (
    "CODEX_DIFF_ONLY_DISABLE"
    if os.environ.get("CODEX_DIFF_ONLY_DISABLE")
    else "ANTIGRAVITY_DIFF_ONLY_DISABLE"
    if os.environ.get("ANTIGRAVITY_DIFF_ONLY_DISABLE")
    else "CURSOR_DIFF_ONLY_DISABLE"
)
LAST_TEXT_CACHE = _HOME_PATH / "token-telemetry" / "diff-only-last-text.txt"


def _hook_event(data: dict[str, Any]) -> str:
    env_event = (
        os.environ.get("CODEX_DIFF_HOOK_EVENT")
        or os.environ.get("ANTIGRAVITY_DIFF_HOOK_EVENT")
        or os.environ.get("CURSOR_DIFF_HOOK_EVENT", "")
    ).strip()
    if env_event:
        return env_event
    name = data.get("hook_event_name")
    return name if isinstance(name, str) else ""


def _gather_text(data: dict[str, Any], event: str) -> str:
    text = extract_response_text(data)
    if text.strip():
        return text

    if event == "subagentStop":
        transcript = data.get("agent_transcript_path")
        if isinstance(transcript, str) and transcript.strip():
            path = Path(transcript).expanduser()
            if path.is_file():
                try:
                    return path.read_text(encoding="utf-8")
                except OSError:
                    pass
    return ""


def _cache_text(text: str) -> None:
    if not text.strip():
        return
    LAST_TEXT_CACHE.parent.mkdir(parents=True, exist_ok=True)
    try:
        LAST_TEXT_CACHE.write_text(text, encoding="utf-8")
    except OSError:
        pass


def _safe_append_telemetry(stats: Any, event: str, errors: list[str]) -> None:
    try:
        append_telemetry(stats, event, errors)
    except OSError as exc:
        sys.stderr.write(f"[diff-only] telemetry skip: {exc}\n")


def _emit_skip(reason: str, event: str, **extra: Any) -> None:
    try:
        append_telemetry(
            type(
                "S",
                (),
                {
                    "to_log_dict": lambda self: {
                        "blocks_parsed": 0,
                        "blocks_applied": 0,
                        "files_touched": 0,
                        "original_file_chars": 0,
                        "patch_output_chars": 0,
                        "replace_line_count": 0,
                        "estimated_chars_saved": 0,
                    }
                },
            )(),
            f"diffOnlySkip:{event or 'unknown'}:{reason}",
            [f"{k}={v}" for k, v in extra.items()][:8],
        )
    except Exception:
        sys.stderr.write(f"[diff-only] skip reason={reason} event={event or 'unknown'} {extra}\n")


def _respond_followup(message: str) -> None:
    payload = {"followup_message": message}
    sys.stdout.write(json.dumps(payload, ensure_ascii=False))
    sys.stdout.flush()


@hook_fail_safe(fallback_json="{}")
def main() -> int:
    if os.environ.get(DISABLE_ENV, "").strip().lower() in {"1", "true", "yes"}:
        return 0

    data = load_stdin_json()
    event = _hook_event(data)

    text = _gather_text(data, event)
    # stop is the safety net: re-apply from last assistant text if payload is empty
    if not text.strip() and event == "stop":
        if LAST_TEXT_CACHE.is_file():
            try:
                text = LAST_TEXT_CACHE.read_text(encoding="utf-8")
            except OSError:
                text = ""

    if not text.strip():
        _emit_skip("empty_text", event)
        return 0

    blocks = parse_blocks(text)
    if not blocks:
        _cache_text(text)
        _emit_skip("no_blocks", event, text_chars=len(text))
        return 0

    roots = resolve_workspace_roots(data)
    if not roots:
        sys.stderr.write(
            "[diff-only] WARN: no workspace_roots in hook payload; "
            "using cwd — set workspace_roots for reliable paths.\n"
        )
        roots = resolve_workspace_roots({})

    result = apply_text(text, roots)
    try:
        log_savings(result.stats)
    except OSError:
        pass

    telemetry_event = f"diffOnlyApply:{event or 'unknown'}"
    _safe_append_telemetry(result.stats, telemetry_event, result.errors)

    if result.errors:
        err_blob = "\n".join(f"- {e}" for e in result.errors[:12])
        sys.stderr.write(f"[diff-only] APPLY FAILED:\n{err_blob}\n")
        followup = (
            "Diff-Only apply failed. Fix SEARCH blocks (verbatim match, unique context) "
            "and resend only the failed hunks (do not retry full-file Write):\n"
            f"{err_blob}"
        )
        if event in {"afterAgentResponse", "subagentStop", "stop"}:
            status = data.get("status")
            if status in (None, "completed", "success", "ok") or event == "afterAgentResponse":
                loop_count = int(data.get("loop_count") or 0)
                if loop_count < 3:
                    _respond_followup(followup)
        return 0

    if result.stats.blocks_applied:
        sys.stderr.write(
            f"[diff-only] applied {result.stats.blocks_applied} block(s) "
            f"to {result.stats.files_touched} file(s)\n"
        )

    _cache_text(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
