#!/usr/bin/env python3
"""Shared helpers for S.C.R.O.O.G.E. events.jsonl logging."""

from __future__ import annotations

import functools
import json
import os
import re
import secrets
import sys
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from telemetry_paths import infer_source as _path_infer_source, resolve_log_file as _path_log_file

# Add hub_files to sys.path for providers module (dev context), or parent dir (installed context)
_SCRIPT_DIR = Path(__file__).resolve().parent
_HUB_FILES = _SCRIPT_DIR / "hub_files"
if _HUB_FILES.exists():
    if str(_HUB_FILES) not in sys.path:
        sys.path.insert(0, str(_HUB_FILES))
else:
    _parent_dir = _SCRIPT_DIR.parent
    if (_parent_dir / "providers").is_dir() and str(_parent_dir) not in sys.path:
        sys.path.insert(0, str(_parent_dir))


def _detect_source() -> str:
    """Detect the telemetry source from the execution context.

    Uses the providers module when available and otherwise defers to
    infer_source(), which applies the same install-path-first rules.
    """
    explicit = os.environ.get("SCROOGE_TELEMETRY_SOURCE", "").strip().lower()
    if explicit:
        return explicit
    try:
        from providers import detect_provider

        return detect_provider().name
    except Exception:
        return _path_infer_source()


def _source_from_row(row: dict[str, Any]) -> str | None:
    """Best-effort source attribution directly from event payload fields."""
    payload_keys = row.get("payload_keys")
    if isinstance(payload_keys, list) and "cursor_version" in payload_keys:
        return "cursor"

    for key in ("transcript_path", "session_path", "hook_home"):
        value = row.get(key)
        if not isinstance(value, str) or not value:
            continue
        if "/.claude/" in value:
            return "claude"
        if "/.gemini/antigravity/" in value:
            return "antigravity"
        if "/.gemini/" in value:
            return "gemini"
        if "/.hermes/" in value:
            return "hermes"
        if "/.codex/" in value:
            return "codex"
        if "/.cursor/" in value:
            return "cursor"
    return None


def resolve_log_file(row: dict[str, Any] | None = None) -> Path:
    """Telemetry log path (override with *_TOKEN_TELEMETRY_LOG for tests)."""
    override = (
        os.environ.get("SCROOGE_TOKEN_TELEMETRY_LOG", "").strip()
        or os.environ.get("CLAUDE_TOKEN_TELEMETRY_LOG", "").strip()
        or os.environ.get("CODEX_TOKEN_TELEMETRY_LOG", "").strip()
        or os.environ.get("CURSOR_TOKEN_TELEMETRY_LOG", "").strip()
    )
    if override:
        return Path(override).expanduser()

    source = _source_from_row(row or {}) or _detect_source()
    return _path_log_file(source=source)


def resolve_skills_dir() -> Path:
    override = os.environ.get("SKILLS_DIR", "").strip()
    if override:
        return Path(override).expanduser()
    hub = os.environ.get("HUB", "").strip()
    if hub:
        return Path(hub).expanduser() / "skills"
    claude_home = os.environ.get("CLAUDE_HOME", "").strip()
    if claude_home:
        return Path(claude_home).expanduser() / "skills"
    gemini_home = os.environ.get("GEMINI_HOME", "").strip()
    if gemini_home:
        return Path(gemini_home).expanduser() / "skills"
    ag_home = os.environ.get("ANTIGRAVITY_HOME", "").strip()
    if ag_home:
        return Path(ag_home).expanduser() / "skills"
    hermes_home = os.environ.get("HERMES_HOME", "").strip()
    if hermes_home:
        return Path(hermes_home).expanduser() / "skills"
    codex_home = os.environ.get("CODEX_HOME", "").strip()
    if codex_home:
        return Path(codex_home).expanduser() / "skills"
    c_home = os.environ.get("CURSOR_HOME", "").strip()
    if c_home:
        return Path(c_home).expanduser() / "skills"
    try:
        return Path.home() / ".claude" / "skills"
    except (RuntimeError, OSError):
        return Path.cwd() / "skills"


LOG_FILE = resolve_log_file()  # default at import; append_event resolves live
SKILLS_DIR = resolve_skills_dir()

_SKILL_LINE = re.compile(r"(?im)^\s*Skill:\s*([a-z0-9][a-z0-9_-]*)\s*$")
_KNOWN_SKILLS: set[str] | None = None

# OTEL-shaped ids: trace = 16 bytes hex, span = 8 bytes hex.
_SPAN_STATE_NAME = "span_state.json"
_TURN_OPEN_EVENTS = frozenset(
    {
        "userPromptSubmit",
        "UserPromptSubmit",
        "sessionStart",
        "SessionStart",
    }
)
_TURN_CLOSE_EVENTS = frozenset(
    {
        "afterAgentResponse",
        "stop",
        "consumptionReportCompliance",
    }
)
_TASK_LAUNCH_EVENTS = frozenset(
    {
        "subagentLaunch",
        "preToolUseCompression",
    }
)


def utc_ts() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


_APPEND_LOCK = threading.Lock()


def append_event(row: dict[str, Any]) -> None:
    row.setdefault("ts", utc_ts())
    log_file = resolve_log_file(row)
    try:
        attach_span_context(row, log_file=log_file)
    except Exception:
        # Span context is best-effort; a failure must never block telemetry writes.
        pass
    with _APPEND_LOCK:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        with log_file.open("a", encoding="utf-8") as fh:
            locked = False
            pos = 0
            try:
                import fcntl

                fcntl.flock(fh.fileno(), fcntl.LOCK_EX)  # type: ignore[attr-defined]
                locked = True
            except (ImportError, OSError):
                try:
                    import msvcrt

                    pos = fh.tell()
                    msvcrt.locking(fh.fileno(), msvcrt.LK_LOCK, 1)  # type: ignore[attr-defined]
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

                        fcntl.flock(fh.fileno(), fcntl.LOCK_UN)  # type: ignore[attr-defined]
                    except (ImportError, OSError):
                        try:
                            import msvcrt

                            fh.seek(pos)
                            msvcrt.locking(fh.fileno(), msvcrt.LK_UNLCK, 1)  # type: ignore[attr-defined]
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


def new_trace_id() -> str:
    """Return a 32-char hex trace id (OTEL-compatible)."""
    return secrets.token_hex(16)


def new_span_id() -> str:
    """Return a 16-char hex span id (OTEL-compatible)."""
    return secrets.token_hex(8)


def _span_state_path(log_file: Path) -> Path:
    return log_file.parent / _SPAN_STATE_NAME


def _conversation_key(row: dict[str, Any]) -> str:
    for key in ("conversation_id", "session_id", "generation_id"):
        value = row.get(key)
        if isinstance(value, str) and value.strip():
            return f"{key}:{value.strip()[:240]}"
    return "anon"


def _load_span_state(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _save_span_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(path)


def _duration_ms_from_start(start_ts: str | None, end_ts: str) -> int | None:
    start = _parse_ts_seconds(start_ts or "")
    end = _parse_ts_seconds(end_ts)
    if start is None or end is None:
        return None
    return int(max(0.0, (end - start) * 1000.0))


def _clean_id(value: object, *, max_len: int) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()[:max_len]
    return None


def _int_or_none(value: object) -> int | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return int(value)


def attach_span_context(row: dict[str, Any], *, log_file: Path | None = None) -> None:
    """Attach trace_id / span_id / parent_span_id / duration_ms for waterfall correlation.

    Turn hierarchy: userPromptSubmit (root) -> tool calls / subagent launches ->
    subagentStop (child of its Task launch) -> afterAgentResponse.

    State lives next to events.jsonl because each hook runs in its own process, so
    parents cannot be held in memory. Ids already present on the row win.
    """
    if os.environ.get("SCROOGE_SPAN_CONTEXT", "1").strip().lower() in {"0", "false", "off"}:
        return

    log = log_file or resolve_log_file(row)
    state_path = _span_state_path(log)
    event = str(row.get("event") or "")
    tool = str(row.get("tool") or "")
    ts = str(row.get("ts") or utc_ts())
    row.setdefault("ts", ts)

    provided_trace = _clean_id(row.get("trace_id"), max_len=32)
    provided_span = _clean_id(row.get("span_id"), max_len=16)
    provided_parent = row.get("parent_span_id")

    state = _load_span_state(state_path)
    conv_key = _conversation_key(row)
    if state.get("conversation_key") != conv_key:
        state = {
            "conversation_key": conv_key,
            "trace_id": provided_trace or new_trace_id(),
            "turn_span_id": "",
            "turn_started_ts": "",
            "last_task_span_id": "",
        }
    elif provided_trace:
        state["trace_id"] = provided_trace
    elif not _clean_id(state.get("trace_id"), max_len=32):
        state["trace_id"] = new_trace_id()

    span_id = provided_span or new_span_id()
    turn_id = _clean_id(state.get("turn_span_id"), max_len=16) or ""
    is_close = event in _TURN_CLOSE_EVENTS

    if event in _TURN_OPEN_EVENTS or not turn_id:
        # Root span of the turn: either an explicit prompt event or the first event seen.
        turn_id = span_id
        state["turn_span_id"] = turn_id
        state["turn_started_ts"] = ts
        state["last_task_span_id"] = ""
        parent_span_id = ""
    elif event == "subagentStop":
        parent_span_id = _clean_id(state.get("last_task_span_id"), max_len=16) or turn_id
    else:
        parent_span_id = turn_id

    if isinstance(provided_parent, str):
        parent_span_id = provided_parent.strip()[:16]

    duration_ms = _int_or_none(row.get("duration_ms"))
    if duration_ms is None:
        duration_ms = _int_or_none(row.get("task_duration_ms"))
    if duration_ms is None and is_close:
        duration_ms = _duration_ms_from_start(str(state.get("turn_started_ts") or ""), ts)

    row["trace_id"] = str(state.get("trace_id") or new_trace_id())[:32]
    row["span_id"] = span_id
    row["parent_span_id"] = parent_span_id
    if duration_ms is not None:
        row["duration_ms"] = max(0, duration_ms)

    if event in _TASK_LAUNCH_EVENTS or (event == "postToolUse" and tool == "Task"):
        state["last_task_span_id"] = span_id

    if is_close:
        state["turn_span_id"] = ""
        state["turn_started_ts"] = ""
        state["last_task_span_id"] = ""

    try:
        _save_span_state(state_path, state)
    except OSError:
        pass


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


def enrich_correlation(
    hook_data: dict[str, Any], tool_input: dict[str, Any] | None = None
) -> dict[str, str]:
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


_tiktoken_encodings: dict[str, Any] = {}
_claude_tokenizer: Any = None


def _resolve_claude_tokenizer_path() -> Path | None:
    """Resolve absolute path to the offline Claude tokenizer.json file."""
    base_dir = Path(__file__).resolve().parent
    if base_dir.name == "telemetry" and base_dir.parent.name == "src":
        repo_root = base_dir.parent.parent
    else:
        repo_root = base_dir.parent

    # Candidates for offline Claude tokenizer
    candidates = [
        base_dir.parent / "src" / "utils" / "claude_tokenizer" / "tokenizer.json",
        repo_root / "hub_files" / "src" / "utils" / "claude_tokenizer" / "tokenizer.json",
        base_dir / "src" / "utils" / "claude_tokenizer" / "tokenizer.json",
    ]
    for p in candidates:
        if p.is_file():
            return p
    return None


def _get_claude_tokenizer() -> Any:
    """Load Claude tokenizer from file if tokenizers library is available."""
    global _claude_tokenizer  # noqa: PLW0603
    if _claude_tokenizer is not None:
        return _claude_tokenizer

    try:
        from tokenizers import Tokenizer

        tokenizer_path = _resolve_claude_tokenizer_path()
        if tokenizer_path:
            _claude_tokenizer = Tokenizer.from_file(str(tokenizer_path))
            return _claude_tokenizer
    except Exception:
        pass
    _claude_tokenizer = False
    return False


def _get_tiktoken_encoding(model_name: str | None = None) -> Any:
    if not model_name:
        model_name = (
            os.environ.get("CODEX_MODEL")
            or os.environ.get("CURSOR_MODEL")
            or os.environ.get("CLAUDE_MODEL")
            or os.environ.get("GEMINI_MODEL")
            or os.environ.get("HERMES_MODEL")
            or None
        )
    encoding_name = "cl100k_base"
    if model_name:
        model_lower = str(model_name).lower()
        if "gpt-4o" in model_lower or "o1" in model_lower:
            encoding_name = "o200k_base"
        elif "gpt-4" in model_lower or "gpt-3.5" in model_lower:
            encoding_name = "cl100k_base"

    if encoding_name in _tiktoken_encodings:
        return _tiktoken_encodings[encoding_name]

    try:
        import tiktoken

        enc = tiktoken.get_encoding(encoding_name)
        _tiktoken_encodings[encoding_name] = enc
        return enc
    except Exception:
        try:
            import tiktoken

            enc = tiktoken.get_encoding("cl100k_base")
            _tiktoken_encodings[encoding_name] = enc
            return enc
        except Exception:
            _tiktoken_encodings[encoding_name] = False
            return False


@functools.lru_cache(maxsize=1024)
def estimate_tokens_with_source(text: str, model_name: str | None = None) -> tuple[int, str]:
    """Accurately estimate tokens, returning a tuple (count, source).

    source is one of:
      - 'tokenizer_exact' (Claude tokenizer was successfully used)
      - 'tokenizer_approx' (tiktoken was successfully used)
      - 'proxy' (character-based fallback)
    """
    # Check if this is a Claude model
    is_claude = False
    if model_name:
        is_claude = "claude" in str(model_name).lower()
    else:
        is_claude = _detect_source() == "claude"

    if not text:
        return 0, "tokenizer_exact" if is_claude else "tokenizer_approx"

    if is_claude:
        tokenizer = _get_claude_tokenizer()
        if tokenizer:
            try:
                return len(tokenizer.encode(text).ids), "tokenizer_exact"
            except Exception:
                pass

    enc = _get_tiktoken_encoding(model_name)
    if enc:
        try:
            return len(enc.encode(text, disallowed_special=())), "tokenizer_approx"
        except Exception:
            pass

    return max(1, (len(text) + 3) // 4), "proxy"


def estimate_tokens(text: str, model_name: str | None = None) -> int:
    """Accurately estimate tokens using tiktoken/claude tokenizer, falling back to len/4 on failure."""
    return estimate_tokens_with_source(text, model_name)[0]
