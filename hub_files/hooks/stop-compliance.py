#!/usr/bin/env python3
"""
Stop hook: enforce Consumption report on completed agent turns.
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
TOKEN_TELEMETRY_DIR = _HOME_PATH / "token-telemetry"

for path in (SRC_DIR, TOKEN_TELEMETRY_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from telemetry_common import append_event  # pylint: disable=import-error
from utils.consumption_report_validator import (  # pylint: disable=import-error
    analyze_consumption_report,
    build_consumption_followup,
)
from utils.diff_applier import extract_response_text  # pylint: disable=import-error
from utils.hook_utils import (
    load_stdin_json,
    hook_fail_safe,
)

DISABLE_ENV = (
    "CODEX_CONSUMPTION_ENFORCE_DISABLE"
    if os.getenv("CODEX_CONSUMPTION_ENFORCE_DISABLE")
    else "ANTIGRAVITY_CONSUMPTION_ENFORCE_DISABLE"
    if os.getenv("ANTIGRAVITY_CONSUMPTION_ENFORCE_DISABLE")
    else "CURSOR_CONSUMPTION_ENFORCE_DISABLE"
)
LAST_TEXT_CACHE = TOKEN_TELEMETRY_DIR / "diff-only-last-text.txt"
MAX_LOOPS = int(os.getenv("CONSUMPTION_REPORT_MAX_LOOPS", "2"))


def _gather_text(data: dict[str, Any]) -> str:
    text = extract_response_text(data)
    if text.strip():
        return text
    if LAST_TEXT_CACHE.is_file():
        try:
            return LAST_TEXT_CACHE.read_text(encoding="utf-8")
        except OSError:
            pass
    return ""


def _respond_followup(message: str) -> None:
    payload = {"followup_message": message}
    sys.stdout.write(json.dumps(payload, ensure_ascii=False))
    sys.stdout.flush()


def _log_compliance(*, present: bool, complete: bool, loop_count: int, enforced: bool) -> None:
    append_event(
        {
            "event": "consumptionReportCompliance",
            "consumption_present": present,
            "consumption_complete": complete,
            "consumption_enforced": enforced,
            "loop_count": loop_count,
        }
    )


@hook_fail_safe(fallback_json="{}")
def main() -> int:
    if os.environ.get(DISABLE_ENV, "").strip().lower() in {"1", "true", "yes"}:
        _log_compliance(present=True, complete=True, loop_count=0, enforced=False)
        return 0

    data = load_stdin_json()
    status_value = str(data.get("status") or "").strip().lower()
    if status_value and status_value not in {"completed", "success", "done"}:
        return 0

    text = _gather_text(data)
    if not text.strip():
        return 0

    status = analyze_consumption_report(text)
    loop_count = int(data.get("loop_count") or 0)

    if status.complete:
        _log_compliance(present=True, complete=True, loop_count=loop_count, enforced=False)
        return 0

    if loop_count >= MAX_LOOPS:
        _log_compliance(
            present=status.present, complete=False, loop_count=loop_count, enforced=False
        )
        sys.stderr.write(
            "[consumption-report] WARN: incomplete after "
            f"{loop_count} loops — giving up enforcement.\n"
        )
        return 0

    followup = build_consumption_followup(status)
    _log_compliance(present=status.present, complete=False, loop_count=loop_count, enforced=True)
    sys.stderr.write("[consumption-report] followup requested (missing compliance block).\n")
    _respond_followup(followup)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
