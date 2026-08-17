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

import hashlib
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

# Resolve home directory dynamically based on environment or script path
_HOME_DIR = os.getenv("CODEX_HOME") or os.getenv("ANTIGRAVITY_HOME") or os.getenv("CURSOR_HOME")
if _HOME_DIR:
    _HOME_PATH = Path(_HOME_DIR).resolve()
else:
    _HOME_PATH = Path(__file__).resolve().parent.parent

SRC_DIR = _HOME_PATH / "src"
# Fall back to the sibling src/ of this script: a misresolved HUB must never make the hook
# crash, because a crashing hook can starve the rest of the event chain.
_LOCAL_SRC = Path(__file__).resolve().parent.parent / "src"
for _candidate in (SRC_DIR, _LOCAL_SRC):
    if str(_candidate) not in sys.path:
        sys.path.insert(0, str(_candidate))

try:
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
except ImportError as _exc:  # pragma: no cover - defensive: degraded HUB layout
    sys.stderr.write(f"[diff-only] disabled: cannot import applier from {SRC_DIR} ({_exc})\n")
    raise SystemExit(0) from None

DISABLE_ENV = (
    "CODEX_DIFF_ONLY_DISABLE"
    if os.environ.get("CODEX_DIFF_ONLY_DISABLE")
    else "ANTIGRAVITY_DIFF_ONLY_DISABLE"
    if os.environ.get("ANTIGRAVITY_DIFF_ONLY_DISABLE")
    else "CURSOR_DIFF_ONLY_DISABLE"
)
LAST_TEXT_CACHE = _HOME_PATH / "token-telemetry" / "diff-only-last-text.txt"
# Fingerprints of responses already applied, so the `stop` safety net never replays a
# response that `afterAgentResponse` already wrote (which used to surface as SEARCH errors).
APPLIED_LEDGER = _HOME_PATH / "token-telemetry" / "diff-only-applied.txt"
APPLIED_LEDGER_MAX = 50
# Dedupe only inside one turn's event fan-out; a later turn resending the same hunks
# (other workspace, reverted file) must still be applied.
DEDUPE_TTL_SECONDS = int(os.environ.get("DIFF_ONLY_DEDUPE_TTL", "900") or 900)


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


def _fingerprint(text: str, roots: list[Path]) -> str:
    seed = text.strip() + "\n" + "\n".join(sorted(str(root) for root in roots))
    return hashlib.sha256(seed.encode("utf-8", "replace")).hexdigest()


def _ledger_entries() -> list[tuple[str, float]]:
    if not APPLIED_LEDGER.is_file():
        return []
    entries: list[tuple[str, float]] = []
    try:
        raw = APPLIED_LEDGER.read_text(encoding="utf-8")
    except OSError:
        return []
    for line in raw.splitlines():
        parts = line.split()
        if not parts:
            continue
        try:
            stamp = float(parts[1]) if len(parts) > 1 else 0.0
        except ValueError:
            stamp = 0.0
        entries.append((parts[0], stamp))
    return entries


def _already_processed(fingerprint: str) -> bool:
    now = time.time()
    return any(
        fp == fingerprint and now - stamp < DEDUPE_TTL_SECONDS for fp, stamp in _ledger_entries()
    )


def _record_processed(fingerprint: str) -> None:
    APPLIED_LEDGER.parent.mkdir(parents=True, exist_ok=True)
    now = time.time()
    fresh = [(fp, stamp) for fp, stamp in _ledger_entries() if now - stamp < DEDUPE_TTL_SECONDS]
    fresh.append((fingerprint, now))
    try:
        APPLIED_LEDGER.write_text(
            "\n".join(f"{fp} {stamp:.0f}" for fp, stamp in fresh[-APPLIED_LEDGER_MAX:]) + "\n",
            encoding="utf-8",
        )
    except OSError:
        pass


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
                        "blocks_already_applied": 0,
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

    fingerprint = _fingerprint(text, roots)
    if _already_processed(fingerprint):
        _emit_skip("already_processed", event, blocks=len(blocks))
        return 0

    # Cache before applying: if this event never fires again, `stop` can still replay it.
    _cache_text(text)

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
    if result.stats.blocks_already_applied:
        sys.stderr.write(
            f"[diff-only] {result.stats.blocks_already_applied} block(s) already on disk — no-op\n"
        )

    _record_processed(fingerprint)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
