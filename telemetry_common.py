#!/usr/bin/env python3
"""Shared helpers for S.C.R.O.O.G.E. events.jsonl logging."""

from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from telemetry_paths import resolve_log_file as _path_log_file


def _detect_source() -> str:
    """Detect telemetry source from environment variables."""
    if os.environ.get("CLAUDE_TT_EVENT") or os.environ.get("CLAUDE_HOME"):
        return "claude"
    if os.environ.get("ANTIGRAVITY_TT_EVENT") or os.environ.get("ANTIGRAVITY_HOME"):
        return "antigravity"
    if os.environ.get("GEMINI_TT_EVENT") or os.environ.get("GEMINI_HOME"):
        return "gemini"
    if os.environ.get("HERMES_TT_EVENT") or os.environ.get("HERMES_HOME"):
        return "hermes"
    # Default to cursor
    return "cursor"


def resolve_log_file() -> Path:
    """Telemetry log path (auto-detects source from environment)."""
    override = os.environ.get("CURSOR_TOKEN_TELEMETRY_LOG", "").strip()
    if override:
        return Path(override).expanduser()
    return _path_log_file(source=_detect_source())


def resolve_skills_dir() -> Path:
    override = os.environ.get("SKILLS_DIR", "").strip()
    if override:
        return Path(override).expanduser()
    hub = os.environ.get("HUB", "").strip()
    if hub:
        return Path(hub).expanduser() / "skills"
    c_home = os.environ.get("CURSOR_HOME", "").strip()
    if c_home:
        return Path(c_home).expanduser() / "skills"
    return Path.home() / ".cursor" / "skills"


LOG_FILE = resolve_log_file()  # default at import; append_event resolves live
SKILLS_DIR = resolve_skills_dir()

_SKILL_LINE = re.compile(r"(?im)^\s*Skill:\s*([a-z0-9][a-z0-9_-]*)\s*$")
_KNOWN_SKILLS: set[str] | None = None


def utc_ts() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def append_event(row: dict[str, Any]) -> None:
    row.setdefault("ts", utc_ts())
    log_file = resolve_log_file()
    log_file.parent.mkdir(parents=True, exist_ok=True)
    with log_file.open("a", encoding="utf-8") as fh:
        locked = False
        pos = 0
        try:
            import fcntl
            fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
            locked = True
        except (ImportError, OSError):
            try:
                import msvcrt
                pos = fh.tell()
                msvcrt.locking(fh.fileno(), msvcrt.LK_LOCK, 1)
                locked = True
            except (ImportError, OSError):
                pass

        try:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
            fh.flush()
        finally:
            if locked:
                try:
                    import fcntl
                    fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
                except (ImportError, OSError):
                    try:
                        import msvcrt
                        fh.seek(pos)
                        msvcrt.locking(fh.fileno(), msvcrt.LK_UNLCK, 1)
                    except (ImportError, OSError):
                        pass


def _load_known_skills() -> set[str]:
    global _KNOWN_SKILLS  # noqa: PLW0603
    if _KNOWN_SKILLS is not None:
        return _KNOWN_SKILLS
    names: set[str] = set()
    if SKILLS_DIR.is_dir():
        for skill_md in SKILLS_DIR.glob("*/SKILL.md"):
            names.add(skill_md.parent.name)
    _KNOWN_SKILLS = names
    return names


def extract_skill_hint(*texts: str) -> str:
    blob = "\n".join(t for t in texts if isinstance(t, str) and t.strip())
    if not blob:
        return ""
    match = _SKILL_LINE.search(blob)
    if match:
        return match.group(1).strip()[:120]
    known = _load_known_skills()
    for name in sorted(known, key=len, reverse=True):
        if re.search(rf"(?i)\b{re.escape(name)}\b", blob):
            return name
    return ""


def correlation_fields(data: dict[str, Any]) -> dict[str, str]:
    out: dict[str, str] = {}
    for key in ("conversation_id", "session_id", "generation_id", "transcript_path", "model"):
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            out[key] = value.strip()[:240]
    return out


def _parse_ts_seconds(ts: str) -> float | None:
    if not isinstance(ts, str) or not ts.strip():
        return None
    try:
        from datetime import datetime

        normalized = ts.strip().replace("Z", "+00:00")
        return datetime.fromisoformat(normalized).timestamp()
    except ValueError:
        return None


def infer_correlation_from_log(max_age_seconds: int = 300, tail_lines: int = 80) -> dict[str, str]:
    """Best-effort session ids when preToolUse payload omits them (e.g. Task launch)."""
    if not LOG_FILE.is_file():
        return {}
    now = _parse_ts_seconds(utc_ts())
    if now is None:
        return {}
    try:
        lines = LOG_FILE.read_text(encoding="utf-8", errors="replace").splitlines()[-tail_lines:]
    except OSError:
        return {}
    for line in reversed(lines):
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(row, dict):
            continue
        fields = correlation_fields(row)
        if not fields.get("session_id") and not fields.get("conversation_id"):
            continue
        row_ts = _parse_ts_seconds(str(row.get("ts") or ""))
        if row_ts is not None and now - row_ts > max_age_seconds:
            continue
        return fields
    return {}


def enrich_correlation(hook_data: dict[str, Any], tool_input: dict[str, Any] | None = None) -> dict[str, str]:
    """Merge hook stdin, tool_input, and recent log context for session correlation."""
    merged: dict[str, Any] = dict(hook_data)
    if tool_input:
        for key in ("conversation_id", "session_id", "generation_id", "transcript_path", "model"):
            value = tool_input.get(key)
            if isinstance(value, str) and value.strip():
                merged[key] = value.strip()
    out = correlation_fields(merged)
    if out.get("session_id") or out.get("conversation_id"):
        return out
    inferred = infer_correlation_from_log()
    if inferred:
        out.update(inferred)
    return out


def int_field(data: dict[str, Any], *keys: str) -> int | None:
    for key in keys:
        value = data.get(key)
        if isinstance(value, bool):
            continue
        if isinstance(value, (int, float)):
            return int(value)
    return None


def extract_tool_label(data: dict[str, Any]) -> str:
    """Resolve tool name from Cursor hook payloads (postToolUse / preToolUse)."""
    for key in ("tool_name", "tool", "toolName", "name"):
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()[:240]
        if isinstance(value, dict):
            nested = value.get("name") or value.get("tool")
            if isinstance(nested, str) and nested.strip():
                return nested.strip()[:240]
    tool_calls = data.get("tool_calls")
    if isinstance(tool_calls, list) and tool_calls:
        first = tool_calls[0]
        if isinstance(first, dict):
            fn = first.get("function") or {}
            if isinstance(fn, dict) and isinstance(fn.get("name"), str):
                return fn["name"].strip()[:240]
    return ""


def tool_output_text(tool_output: object) -> str:
    """Normalize Task tool_output to a string for size proxy."""
    if isinstance(tool_output, str):
        return tool_output
    if isinstance(tool_output, dict):
        for key in ("text", "content", "result", "output", "message"):
            value = tool_output.get(key)
            if isinstance(value, str):
                return value
        try:
            import json

            return json.dumps(tool_output, ensure_ascii=False)
        except (TypeError, ValueError):
            return str(tool_output)
    if tool_output is None:
        return ""
    return str(tool_output)


def is_subagent_launch_event(event: str) -> bool:
    return event in {"subagentLaunch", "preToolUseCompression"}


def fail_safe(fallback_value: Any = None):
    """Decorator to catch all exceptions in a function, log to stderr, and return fallback."""
    def decorator(func):
        import functools
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as exc:
                sys.stderr.write(f"[telemetry-failsafe] Error in {func.__name__}: {exc}\n")
                return fallback_value
        return wrapper
    return decorator


def hook_fail_safe(fallback_json: str = '{"permission": "allow"}'):
    """Decorator for hook main() functions to output a safe JSON response and exit 0 on crash."""
    def decorator(func):
        import functools
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as exc:
                sys.stderr.write(f"[hook-failsafe] Critical error in {func.__name__}: {exc}\n")
                sys.stdout.write(fallback_json)
                sys.stdout.flush()
                return 0
        return wrapper
    return decorator
