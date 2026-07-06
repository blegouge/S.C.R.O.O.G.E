#!/usr/bin/env python3
"""Codex PreToolUse hook: rewrite Bash commands to RTK compact wrappers.

The hook is intentionally fail-open. If RTK is missing, returns an unexpected
payload, or declines a rewrite, Codex receives permission to run the original
command.
"""

from __future__ import annotations

import datetime as _dt
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

_HOME_DIR = os.getenv("CODEX_HOME") or os.getenv("ANTIGRAVITY_HOME") or os.getenv("CURSOR_HOME")
if _HOME_DIR:
    _HOME_PATH = Path(_HOME_DIR).resolve()
else:
    _HOME_PATH = Path(__file__).resolve().parent.parent

for _path in (_HOME_PATH / "token-telemetry", _HOME_PATH / "src"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

try:
    from telemetry_common import append_event, enrich_correlation, hook_fail_safe
except Exception:  # pragma: no cover - last-ditch fail-open when runtime is incomplete

    def append_event(row: dict[str, Any]) -> None:
        return None

    def enrich_correlation(
        hook_data: dict[str, Any], tool_input: dict[str, Any] | None = None
    ) -> dict[str, str]:
        return {}

    def hook_fail_safe(fallback_json: str = '{"permission": "allow"}'):
        def decorator(func):
            def wrapper(*args, **kwargs):
                try:
                    return func(*args, **kwargs)
                except Exception:
                    sys.stdout.write(fallback_json)

            return wrapper

        return decorator


def _respond(payload: dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(payload, ensure_ascii=False))


def _load_stdin_json() -> dict[str, Any]:
    raw = sys.stdin.read()
    if not raw.strip():
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {"_parse_error": True, "_raw_len": len(raw)}
    return parsed if isinstance(parsed, dict) else {}


def _tool_name(data: dict[str, Any]) -> str:
    for key in ("tool_name", "tool", "toolName", "name"):
        value = data.get(key)
        if isinstance(value, str):
            return value.strip()
        if isinstance(value, dict):
            nested = value.get("name") or value.get("tool")
            if isinstance(nested, str):
                return nested.strip()
    return ""


def _tool_input(data: dict[str, Any]) -> dict[str, Any]:
    value = data.get("tool_input")
    return value if isinstance(value, dict) else {}


def _command_from_tool_input(tool_input: dict[str, Any]) -> tuple[str, str]:
    for key in ("cmd", "command", "script"):
        value = tool_input.get(key)
        if isinstance(value, str) and value.strip():
            return key, value
    return "", ""


def _rtk_bin() -> str:
    configured = os.environ.get("RTK_BIN", "").strip()
    if configured:
        return configured
    compression_env = _HOME_PATH / "compression.env"
    if compression_env.is_file():
        for raw in compression_env.read_text(encoding="utf-8", errors="replace").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            if key.strip() == "RTK_BIN":
                return value.strip().strip('"').strip("'")
    return shutil.which("rtk") or str(Path.home() / ".local" / "bin" / "rtk")


def _rewrite_command(command: str) -> tuple[str, str]:
    rtk = _rtk_bin()
    if not rtk or not Path(rtk).expanduser().exists() and shutil.which(rtk) is None:
        return command, "rtk_missing"

    proc = subprocess.run(
        [rtk, "rewrite", command],
        capture_output=True,
        text=True,
        timeout=3,
        check=False,
    )
    rewritten = (proc.stdout or "").strip()
    if not rewritten:
        return command, "empty"
    if rewritten == command:
        return command, "unchanged"
    # RTK uses non-zero return codes for "rewritten" in some versions; stdout is
    # the source of truth for the replacement.
    return rewritten, "rewritten"


def _append_row(
    *,
    hook_data: dict[str, Any],
    tool_input: dict[str, Any],
    original: str,
    rewritten: str,
    status: str,
) -> None:
    before = (len(original) + 3) // 4
    after = (len(rewritten) + 3) // 4
    row: dict[str, Any] = {
        "ts": _dt.datetime.now(_dt.UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "event": "rtkShellRewrite",
        "tool": "Bash",
        "rtk_rewrite_status": status,
        "rtk_original_command": original[:240],
        "rtk_rewritten_command": rewritten[:240],
        "rtk_before_tokens": before,
        "rtk_after_tokens": after,
        "rtk_saved_tokens": max(0, before - after),
        "approx_tokens": 0,
        "text_chars": 0,
        "raw_chars": 0,
    }
    row.update(enrich_correlation(hook_data, tool_input))
    append_event(row)


@hook_fail_safe(fallback_json='{"permission": "allow"}')
def main() -> None:
    data = _load_stdin_json()
    if _tool_name(data) != "Bash":
        _respond({"permission": "allow"})
        return

    tool_input = _tool_input(data)
    command_key, command = _command_from_tool_input(tool_input)
    if not command_key:
        _respond({"permission": "allow"})
        return

    rewritten, status = _rewrite_command(command)
    if rewritten == command:
        _append_row(
            hook_data=data,
            tool_input=tool_input,
            original=command,
            rewritten=rewritten,
            status=status,
        )
        _respond({"permission": "allow"})
        return

    updated_input = dict(tool_input)
    updated_input[command_key] = rewritten
    _append_row(
        hook_data=data,
        tool_input=tool_input,
        original=command,
        rewritten=rewritten,
        status=status,
    )
    sys.stderr.write(f"[codex-rtk] Bash command rewritten: {command!r} -> {rewritten!r}\n")
    _respond({"permission": "allow", "updated_input": updated_input})


if __name__ == "__main__":
    main()
