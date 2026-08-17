#!/usr/bin/env python3
"""
preToolUse hook: block Write on existing files and enforce targeted Diff-Only edits.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

_HOME_DIR = os.getenv("CODEX_HOME") or os.getenv("ANTIGRAVITY_HOME") or os.getenv("CURSOR_HOME")
if _HOME_DIR:
    _HOME_PATH = Path(_HOME_DIR).resolve()
else:
    _HOME_PATH = Path(__file__).resolve().parent.parent

SRC_DIR = _HOME_PATH / "src"
TOKEN_TELEMETRY_DIR = _HOME_PATH / "token-telemetry"
_LOCAL_ROOT = Path(__file__).resolve().parent.parent
for _path in (SRC_DIR, TOKEN_TELEMETRY_DIR, _LOCAL_ROOT / "src", _LOCAL_ROOT / "token-telemetry"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

try:
    from telemetry_common import append_event  # pylint: disable=import-error

    from utils.diff_applier import resolve_workspace_roots  # pylint: disable=import-error
    from utils.hook_utils import (
        extract_tool_input,
        extract_tool_name,
        hook_fail_safe,
        load_stdin_json,
    )
except ImportError as _exc:  # pragma: no cover - defensive: never block edits on a broken HUB
    sys.stderr.write(f"[diff-only] guard disabled: import failed from {SRC_DIR} ({_exc})\n")
    sys.stdout.write('{"permission": "allow"}')
    raise SystemExit(0) from None

_IS_CODEX_HOME = _HOME_PATH.name == ".codex" or os.getenv("CODEX_HOME")
DISABLE_ENV = "CODEX_DIFF_ONLY_DISABLE" if _IS_CODEX_HOME else "ANTIGRAVITY_DIFF_ONLY_DISABLE"
ALLOW_WRITE_ENV = (
    "CODEX_DIFF_ONLY_ALLOW_WRITE" if _IS_CODEX_HOME else "ANTIGRAVITY_DIFF_ONLY_ALLOW_WRITE"
)
# Legacy Cursor env aliases
_LEGACY_DISABLE = "CURSOR_DIFF_ONLY_DISABLE"
_LEGACY_ALLOW = "CURSOR_DIFF_ONLY_ALLOW_WRITE"
# Hard deny is opt-in through a per-HUB marker file, never through an inherited env var:
# an exported STRICT flag used to deny every edit in every agent sharing the environment.
STRICT_MARKER = _HOME_PATH / "diff-only-strict"


def _strict_mode() -> bool:
    """Hard deny requires the marker file; env flags alone only downgrade to a nudge."""
    return STRICT_MARKER.is_file()


def _extract_target_path(tool_input: dict[str, Any]) -> str:
    for key in ("path", "file_path", "filePath", "target", "file"):
        value = tool_input.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _looks_like_targeted_edit(tool_input: dict[str, Any]) -> bool:
    """Allow StrReplace/ApplyPatch-shaped payloads even if Cursor labels them Write."""
    targeted_pairs = (
        ("old_string", "new_string"),
        ("oldString", "newString"),
        ("search", "replace"),
        ("SEARCH", "REPLACE"),
    )
    for left, right in targeted_pairs:
        if left in tool_input and right in tool_input:
            return True

    for key in ("patch", "diff", "hunk", "edits", "changes"):
        value = tool_input.get(key)
        if isinstance(value, str) and value.strip():
            return True
        if isinstance(value, list) and value:
            return True
    return False


def _resolve_target_file(
    data: dict[str, Any], tool_input: dict[str, Any], rel_path: str
) -> Path | None:
    cleaned = rel_path.replace("file://", "").strip()
    candidate = Path(cleaned).expanduser()
    if candidate.is_absolute() and candidate.is_file():
        return candidate

    merged = {**data, **tool_input}
    roots = resolve_workspace_roots(merged)
    if not roots:
        roots = resolve_workspace_roots({})

    for root in roots:
        resolved = (root / cleaned).resolve()
        try:
            resolved.relative_to(root.resolve())
        except ValueError:
            continue
        if resolved.is_file():
            return resolved
    return None


def _respond(payload: dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(payload, ensure_ascii=False))
    sys.stdout.flush()


@hook_fail_safe(fallback_json='{"permission": "allow"}')
def main() -> None:
    if any(
        os.environ.get(k, "").strip().lower() in {"1", "true", "yes"}
        for k in (DISABLE_ENV, _LEGACY_DISABLE)
    ):
        _respond({"permission": "allow"})
        return
    if any(
        os.environ.get(k, "").strip().lower() in {"1", "true", "yes"}
        for k in (ALLOW_WRITE_ENV, _LEGACY_ALLOW)
    ):
        _respond({"permission": "allow"})
        return

    data = load_stdin_json()
    if extract_tool_name(data) != "Write":
        _respond({"permission": "allow"})
        return

    tool_input = extract_tool_input(data)
    rel_path = _extract_target_path(tool_input)
    if not rel_path:
        _respond({"permission": "allow"})
        return

    if _looks_like_targeted_edit(tool_input):
        try:
            append_event(
                {
                    "event": "diffOnlyWriteAllowedAsTargetedEdit",
                    "tool": "Write",
                    "file_hint": rel_path[-80:],
                }
            )
        except OSError:
            pass
        _respond({"permission": "allow"})
        return

    target = _resolve_target_file(data, tool_input, rel_path)
    if target is None:
        _respond({"permission": "allow"})
        return

    strict = _strict_mode()
    try:
        append_event(
            {
                "event": "diffOnlyWriteBlocked" if strict else "diffOnlyWriteSoftNudge",
                "tool": "Write",
                "file_hint": target.name[:200],
                "path": str(target)[:240],
                "strict": strict,
            }
        )
    except OSError:
        pass

    message = (
        f"Full-file Write on existing `{target.name}` (Diff-Only preference).\n"
        "Prefer a targeted edit (StrReplace/ApplyPatch/Edit) with a unique snippet; "
        "SEARCH/REPLACE hunks in the reply are the fallback.\n"
        f"Hard deny is opt-in: create the marker file {STRICT_MARKER}."
    )
    if strict:
        _respond(
            {
                "permission": "deny",
                "agent_message": message,
                "user_message": (
                    f"Write blocked on existing file: {target.name} — "
                    "use a targeted editor or exact SEARCH/REPLACE blocks."
                ),
            }
        )
        return

    # Soft mode: never brick StrReplace-as-Write; nudge toward Diff-Only.
    _respond({"permission": "allow", "agent_message": message})


if __name__ == "__main__":
    main()
