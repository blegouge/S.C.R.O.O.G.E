#!/usr/bin/env python3
"""
preToolUse hook: block Write on existing files — enforce StrReplace / Diff-Only.
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
for _path in (SRC_DIR, TOKEN_TELEMETRY_DIR):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from telemetry_common import append_event  # pylint: disable=import-error
from utils.diff_applier import resolve_workspace_roots  # pylint: disable=import-error

_IS_CODEX_HOME = _HOME_PATH.name == ".codex" or os.getenv("CODEX_HOME")
DISABLE_ENV = "CODEX_DIFF_ONLY_DISABLE" if _IS_CODEX_HOME else "ANTIGRAVITY_DIFF_ONLY_DISABLE"
ALLOW_WRITE_ENV = (
    "CODEX_DIFF_ONLY_ALLOW_WRITE" if _IS_CODEX_HOME else "ANTIGRAVITY_DIFF_ONLY_ALLOW_WRITE"
)
# Legacy Cursor env aliases
_LEGACY_DISABLE = "CURSOR_DIFF_ONLY_DISABLE"
_LEGACY_ALLOW = "CURSOR_DIFF_ONLY_ALLOW_WRITE"


def _load_stdin() -> dict[str, Any]:
    raw = sys.stdin.read()
    if not raw.strip():
        return {}
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        return {}


def _tool_name(data: dict[str, Any]) -> str:
    for key in ("tool_name", "name"):
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    tool = data.get("tool")
    if isinstance(tool, dict):
        nested = tool.get("name")
        if isinstance(nested, str) and nested.strip():
            return nested.strip()
    if isinstance(tool, str) and tool.strip():
        return tool.strip()
    return ""


def _tool_input(data: dict[str, Any]) -> dict[str, Any]:
    value = data.get("tool_input")
    if isinstance(value, dict):
        return value
    value = data.get("input")
    return value if isinstance(value, dict) else {}


def _extract_target_path(tool_input: dict[str, Any]) -> str:
    for key in ("path", "file_path", "filePath", "target", "file"):
        value = tool_input.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


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


from telemetry_common import hook_fail_safe


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

    data = _load_stdin()
    if _tool_name(data) != "Write":
        _respond({"permission": "allow"})
        return

    tool_input = _tool_input(data)
    rel_path = _extract_target_path(tool_input)
    if not rel_path:
        _respond({"permission": "allow"})
        return

    target = _resolve_target_file(data, tool_input, rel_path)
    if target is None:
        _respond({"permission": "allow"})
        return

    append_event(
        {
            "event": "diffOnlyWriteBlocked",
            "tool": "Write",
            "file_hint": target.name[:200],
            "path": str(target)[:240],
        }
    )
    message = (
        f"Write blocked on existing file `{target.name}` (Diff-Only policy).\n"
        "Use StrReplace with a unique SEARCH snippet, or emit SEARCH/REPLACE blocks in chat.\n"
        "Override: set CODEX_DIFF_ONLY_ALLOW_WRITE=1, ANTIGRAVITY_DIFF_ONLY_ALLOW_WRITE=1, "
        "or CURSOR_DIFF_ONLY_ALLOW_WRITE=1."
    )
    _respond(
        {
            "permission": "deny",
            "agent_message": message,
            "user_message": f"Write refusé sur fichier existant : {target.name} — utiliser StrReplace.",
        }
    )


if __name__ == "__main__":
    main()
