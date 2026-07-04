#!/usr/bin/env python3
"""
Append one JSON line per hook trigger — token proxy (postToolUse / afterAgentResponse)
and LOC / Tab metrics (afterFileEdit / afterTabFileEdit).

Cursor does not expose billed tokens or Composer diff reject counts in hooks.
"""
from __future__ import annotations

import datetime as _dt
import difflib
import json
import os
import re
import sys
from pathlib import Path

# Resolve home directory dynamically based on environment or script path
_HOME_DIR = os.getenv("CODEX_HOME") or os.getenv("ANTIGRAVITY_HOME") or os.getenv("CURSOR_HOME")
if _HOME_DIR:
    _HOME_PATH = Path(_HOME_DIR).resolve()
else:
    _HOME_PATH = Path(__file__).resolve().parent.parent

_TOKEN_TELEMETRY_DIR = _HOME_PATH / "token-telemetry"
_SRC_DIR = _HOME_PATH / "src"
for _path in (_TOKEN_TELEMETRY_DIR, _SRC_DIR):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from telemetry_common import (  # pylint: disable=import-error
    append_event,
    correlation_fields,
    enrich_correlation,
    extract_skill_hint,
    extract_tool_label,
    int_field,
    tool_output_text,
    LOG_FILE,
)
from utils.consumption_report_validator import analyze_consumption_report  # pylint: disable=import-error


def _string_chars(obj: object) -> int:
    n = 0
    if isinstance(obj, str):
        n += len(obj)
    elif isinstance(obj, dict):
        for v in obj.values():
            n += _string_chars(v)
    elif isinstance(obj, list):
        for v in obj:
            n += _string_chars(v)
    return n


def _tool_label(data: dict) -> str:
    return extract_tool_label(data)


def _populate_subagent_stop_row(
    row: dict[str, object],
    *,
    data: dict,
    raw: str,
    source: str,
) -> None:
    """Fill subagentStop fields from hook payload or postToolUse fallback."""
    row["event"] = "subagentStop"
    row["subagent_stop_source"] = source
    row["tool"] = "Task"

    summary = data.get("summary")
    summary_text = summary if isinstance(summary, str) else ""
    transcript_path = data.get("agent_transcript_path")

    tool_input = data.get("tool_input")
    if not isinstance(tool_input, dict):
        tool_input = {}

    if not summary_text and source == "postToolUse_fallback":
        summary_text = tool_output_text(data.get("tool_output"))

    if isinstance(transcript_path, str) and transcript_path.strip():
        row["agent_transcript_path"] = transcript_path.strip()[:240]

    status = data.get("status")
    if isinstance(status, str) and status.strip():
        row["subagent_status"] = status.strip()[:80]
    elif source == "postToolUse_fallback":
        row["subagent_status"] = "completed"

    row["subagent_summary_chars"] = len(summary_text)
    transcript_chars = 0
    if isinstance(transcript_path, str):
        transcript_chars = _read_transcript_chars(transcript_path)

    output_chars = len(summary_text) + transcript_chars
    if output_chars == 0 and source == "postToolUse_fallback":
        output_chars = len(tool_output_text(data.get("tool_output")))

    row["text_chars"] = output_chars
    row["approx_tokens"] = (output_chars + 3) // 4 if output_chars else (len(raw) + 3) // 4

    subagent_type = (
        data.get("subagent_type")
        or data.get("type")
        or tool_input.get("subagent_type")
        or tool_input.get("subagentType")
        or tool_input.get("type")
    )
    if isinstance(subagent_type, str):
        row["subagent_type"] = subagent_type.strip()[:80]

    description = tool_input.get("description")
    if isinstance(description, str):
        row["subagent_description"] = description.strip()[:240]

    prompt = tool_input.get("prompt")
    prompt_text = prompt if isinstance(prompt, str) else ""
    row["skill_hint"] = extract_skill_hint(summary_text, prompt_text, raw)

    duration = data.get("duration")
    if isinstance(duration, (int, float)):
        row["task_duration_ms"] = int(duration)

    hook_event = data.get("hook_event_name")
    if isinstance(hook_event, str):
        row["hook_event_name"] = hook_event[:80]

    if source == "hook" and not summary_text and not transcript_path:
        row["subagent_stop_hook_empty"] = True


def _file_basename(data: dict) -> str:
    for k in ("file", "path", "filepath", "uri", "filePath"):
        v = data.get(k)
        if isinstance(v, str) and v:
            return Path(v.replace("file://", "")).name[:200]
    return ""


def _iter_old_new_pairs(obj: object, depth: int = 0) -> list[tuple[str, str]]:
    """Recover (old_content, new_content) pairs from diverse hook payloads."""
    if depth > 14:
        return []
    pairs: list[tuple[str, str]] = []
    keys_old = ("old_string", "oldString", "old_line", "oldLine", "before", "previous")
    keys_new = ("new_string", "newString", "new_line", "newLine", "after", "next")

    if isinstance(obj, dict):
        o = next((obj[k] for k in keys_old if isinstance(obj.get(k), str)), None)
        n = next((obj[k] for k in keys_new if isinstance(obj.get(k), str)), None)
        if isinstance(o, str) and isinstance(n, str):
            pairs.append((o, n))

        edits = obj.get("edits")
        if isinstance(edits, list):
            for e in edits:
                pairs.extend(_iter_old_new_pairs(e, depth + 1))

        for key in ("changes", "operations", "hunks", "diffs", "patches"):
            arr = obj.get(key)
            if isinstance(arr, list):
                for e in arr:
                    pairs.extend(_iter_old_new_pairs(e, depth + 1))

        for v in obj.values():
            if v is edits:
                continue
            if isinstance(v, (dict, list)) and len(pairs) < 50:
                pairs.extend(_iter_old_new_pairs(v, depth + 1))
    elif isinstance(obj, list):
        for item in obj[:80]:
            pairs.extend(_iter_old_new_pairs(item, depth + 1))
    return pairs[:50]


def _line_add_remove(old: str, new: str) -> tuple[int, int]:
    a = old.splitlines()
    b = new.splitlines()
    added = removed = 0
    matcher = difflib.SequenceMatcher(a=a, b=b)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "replace":
            added += j2 - j1
            removed += i2 - i1
        elif tag == "delete":
            removed += i2 - i1
        elif tag == "insert":
            added += j2 - j1
    return added, removed


def _aggregate_edit_stats(data: dict) -> tuple[int, int]:
    pairs = _iter_old_new_pairs(data)
    if not pairs:
        return 0, 0
    ta = tr = 0
    for o, n in pairs:
        a, r = _line_add_remove(o, n)
        ta += a
        tr += r
    return ta, tr


def _iter_strings(obj: object, depth: int = 0) -> list[str]:
    if depth > 10:
        return []
    out: list[str] = []
    if isinstance(obj, str):
        out.append(obj)
    elif isinstance(obj, dict):
        for v in obj.values():
            out.extend(_iter_strings(v, depth + 1))
    elif isinstance(obj, list):
        for v in obj[:120]:
            out.extend(_iter_strings(v, depth + 1))
    return out[:600]


def _calculate_programmatic_consumption() -> dict[str, object]:
    post_tool_calls = 0
    subagents_launched = 0
    git_cache_hit_count = 0
    tool_names: list[str] = []
    
    if LOG_FILE.is_file():
        try:
            with LOG_FILE.open("r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
                for line in reversed(lines[-200:]):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        row = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    
                    ev = row.get("event")
                    if ev == "afterAgentResponse":
                        # We hit the previous response event, so stop backtracking
                        break
                    
                    if ev == "postToolUse":
                        tool_name = str(row.get("tool") or "")
                        if tool_name == "Task":
                            pass
                        elif tool_name:
                            post_tool_calls += 1
                            tool_names.append(tool_name)
                    elif ev in {"subagentLaunch", "preToolUseCompression"}:
                        subagents_launched += 1
                        if row.get("compression_git_cache_hit") is True or row.get("git_cache_hit") is True:
                            git_cache_hit_count += 1
        except OSError:
            pass

    if subagents_launched > 1:
        work_mode = "multiple subagents"
    elif subagents_launched == 1:
        work_mode = "single subagent"
    else:
        work_mode = "direct tools only"

    if post_tool_calls == 0 and subagents_launched == 0:
        tool_activity = "no tools used"
    else:
        parts = []
        if post_tool_calls > 0:
            parts.append(f"{post_tool_calls} tool calls")
        if subagents_launched > 0:
            parts.append(f"{subagents_launched} subagent calls")
        tool_activity = " and ".join(parts)
        if tool_names:
            unique_tools = list(dict.fromkeys(tool_names))
            tool_activity += f" ({', '.join(unique_tools[:3])})"

    if subagents_launched > 1:
        token_risk = "high"
    elif subagents_launched == 1 or post_tool_calls > 5:
        token_risk = "medium"
    else:
        token_risk = "low"

    cost_drivers_list = []
    if subagents_launched > 0:
        cost_drivers_list.append(f"{subagents_launched} subagent run(s)")
    if post_tool_calls > 5:
        cost_drivers_list.append(f"{post_tool_calls} tool calls")
    if not cost_drivers_list:
        cost_drivers_list.append("none")
    cost_drivers = "; ".join(cost_drivers_list)

    opt_list = []
    if git_cache_hit_count > 0:
        opt_list.append("git cache hit")
    if post_tool_calls > 0 and subagents_launched == 0:
        opt_list.append("direct tools only")
    if not opt_list:
        opt_list.append("none")
    optimization = ", ".join(opt_list)

    return {
        "consumption_present": True,
        "consumption_complete": True,
        "consumption_work_mode": work_mode,
        "consumption_tool_activity": tool_activity,
        "consumption_token_risk": token_risk,
        "consumption_cost_drivers": cost_drivers,
        "consumption_optimization": optimization,
        "consumption_exact_unknown": True,
    }


def _extract_consumption_report(data: dict) -> dict[str, object]:
    strings = _iter_strings(data)
    blob = "\n".join(strings) if strings else ""
    status = analyze_consumption_report(blob)

    if status.present:
        return {
            "consumption_present": status.present,
            "consumption_complete": status.complete,
            "consumption_work_mode": status.work_mode[:320],
            "consumption_tool_activity": status.tool_activity[:320],
            "consumption_token_risk": status.token_risk[:120],
            "consumption_cost_drivers": status.cost_drivers[:400],
            "consumption_optimization": status.optimization[:400],
            "consumption_exact_unknown": status.exact_unknown,
        }
    else:
        return _calculate_programmatic_consumption()


def _read_transcript_chars(path_value: str) -> int:
    path = Path(path_value.replace("file://", "")).expanduser()
    if not path.is_file():
        return 0
    try:
        return len(path.read_text(encoding="utf-8", errors="replace"))
    except OSError:
        return 0


def _usage_fields(data: dict) -> dict[str, object]:
    input_tokens = int_field(data, "input_tokens")
    output_tokens = int_field(data, "output_tokens")
    cache_read = int_field(data, "cache_read_tokens")
    cache_write = int_field(data, "cache_write_tokens")
    billed_total = None
    if input_tokens is not None and output_tokens is not None:
        billed_total = input_tokens + output_tokens
    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cache_read_tokens": cache_read,
        "cache_write_tokens": cache_write,
        "billed_total_tokens": billed_total,
    }


def _build_row(
    event: str,
    raw: str,
    data: dict,
) -> dict[str, object]:
    text_chars = _string_chars(data)
    raw_chars = len(raw)
    approx = (max(text_chars, raw_chars) + 3) // 4

    row: dict[str, object] = {
        "ts": _dt.datetime.now(_dt.timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z"),
        "event": event,
        "approx_tokens": approx,
        "text_chars": text_chars,
        "raw_chars": raw_chars,
        "tool": _tool_label(data) if event == "postToolUse" else "",
        "payload_keys": list(data.keys())[:30],
        "lines_added": 0,
        "lines_removed": 0,
        "file_hint": "",
        "edit_kind": "",
        "consumption_present": False,
        "consumption_complete": False,
        "consumption_work_mode": "",
        "consumption_tool_activity": "",
        "consumption_token_risk": "",
        "consumption_cost_drivers": "",
        "consumption_optimization": "",
        "consumption_exact_unknown": False,
        "subagent_type": "",
        "subagent_description": "",
        "skill_hint": "",
        "subagent_status": "",
        "subagent_summary_chars": 0,
        "subagent_stop_source": "",
    }
    row.update(correlation_fields(data))

    if event == "afterFileEdit":
        la, lr = _aggregate_edit_stats(data)
        row["lines_added"] = la
        row["lines_removed"] = lr
        row["file_hint"] = _file_basename(data)
        row["edit_kind"] = "agent"
        # Keep token chart readable: payload can be huge; LOC is the signal.
        row["approx_tokens"] = 0
        row["text_chars"] = 0
    elif event == "afterTabFileEdit":
        la, lr = _aggregate_edit_stats(data)
        row["lines_added"] = la
        row["lines_removed"] = lr
        row["file_hint"] = _file_basename(data)
        row["edit_kind"] = "tab"
        row["approx_tokens"] = 0
        row["text_chars"] = 0
    elif event == "afterAgentResponse":
        row.update(_extract_consumption_report(data))
        row.update(_usage_fields(data))
        if row.get("billed_total_tokens") is not None:
            row["approx_tokens"] = row["billed_total_tokens"]
    elif event == "subagentStop":
        _populate_subagent_stop_row(row, data=data, raw=raw, source="hook")
    elif event == "postToolUse" and _tool_label(data) == "Task":
        _populate_subagent_stop_row(row, data=data, raw=raw, source="postToolUse_fallback")
        row.update(enrich_correlation(data, data.get("tool_input") if isinstance(data.get("tool_input"), dict) else None))

    return row


def main() -> None:
    raw = sys.stdin.read()
    data: dict
    try:
        data = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        data = {"_parse_error": True, "_raw_len": len(raw)}

    event = (
        os.environ.get("CODEX_TT_EVENT")
        or os.environ.get("ANTIGRAVITY_TT_EVENT")
        or os.environ.get("CURSOR_TT_EVENT", "unknown")
    ).strip()
    row = _build_row(event, raw, data)

    append_event(row)


if __name__ == "__main__":
    main()
