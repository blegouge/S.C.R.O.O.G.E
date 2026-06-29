#!/usr/bin/env python3
"""Bridge Hermes compression.log -> token-telemetry events.jsonl for the dashboard."""

from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path
from typing import Any

HERMES_LOG = Path.home() / ".hermes" / "compression.log"
HERMES_EVENTS = Path.home() / ".hermes" / "token-telemetry" / "events.jsonl"
SOURCE = "hermes"

_TOKEN_RE = re.compile(r"\b(\d[\d,]*)\s*(?:tok|token|tokens)\b", re.IGNORECASE)
_SIZE_RE = re.compile(r"(\d[\d,]*)\s*(?:b|byte|bytes)", re.IGNORECASE)


def _parse_int(value: Any) -> int:
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, str):
        cleaned = value.replace(",", "").strip()
        if not cleaned:
            return 0
        try:
            return int(float(cleaned))
        except ValueError:
            return 0
    return 0


def _estimate_tokens_from_text(text: str) -> int:
    if not text:
        return 0
    match = _TOKEN_RE.search(text)
    if match:
        return _parse_int(match.group(1))
    match = _SIZE_RE.search(text)
    if match:
        raw = _parse_int(match.group(1))
        return max(1, raw // 4)
    return max(1, len(text) // 4)


def _normalize_hermes_event(row: dict[str, Any]) -> dict[str, Any] | None:
    event_name = str(row.get("event") or "").strip().lower()
    if not event_name:
        return None

    out: dict[str, Any] = {
        "source": SOURCE,
        "event": event_name,
    }
    out.update(
        {
            key: value
            for key, value in row.items()
            if key in {"ts", "session_id", "conversation_id", "transcript_path", "model", "tool"}
            and isinstance(value, str) and value.strip()
        }
    )

    if event_name == "subagent_stop":
        summary = str(row.get("summary") or row.get("summary_len") or "")
        out["approx_tokens"] = _estimate_tokens_from_text(summary)
        out["text_chars"] = len(summary)
        out["subagent_status"] = str(row.get("subagent_status") or "completed").strip() or "completed"

    elif event_name in {"after_agent_response", "afterAgentResponse"}:
        text_len = _parse_int(row.get("text_len") or row.get("output_len"))
        out["text_chars"] = text_len
        out["approx_tokens"] = max(1, text_len // 4) if text_len else 0

    elif event_name == "post_tool_use":
        output_len = _parse_int(row.get("output_len") or row.get("text_len"))
        out["text_chars"] = output_len
        out["approx_tokens"] = max(1, output_len // 4) if output_len else 0

    elif event_name in {"subagent_launch", "agent_started", "action.execution_start", "pre_tool_use_compression"}:
        text_len = _parse_int(row.get("text_len") or row.get("output_len"))
        out["text_chars"] = text_len
        out["approx_tokens"] = max(1, text_len // 4) if text_len else 0

    else:
        text_len = _parse_int(row.get("text_len") or row.get("output_len"))
        out["text_chars"] = text_len
        out["approx_tokens"] = max(1, text_len // 4) if text_len else 0

    return out


def _already_emitted(target: Path, raw_line: str) -> bool:
    if not target.is_file():
        return False
    try:
        return any(raw_line == line.rstrip("\n") for line in target.read_text(encoding="utf-8", errors="replace").splitlines())
    except OSError:
        return False


def emit_events(target: Path = HERMES_EVENTS) -> dict[str, Any]:
    target.parent.mkdir(parents=True, exist_ok=True)
    if not HERMES_LOG.is_file():
        return {"ok": True, "emitted": 0, "mode": "no-input"}

    seen: set[str] = set()
    emitted = 0

    with HERMES_LOG.open("r", encoding="utf-8", errors="replace") as src, target.open("a", encoding="utf-8") as dst:
        for raw_line in src:
            raw = raw_line.rstrip("\n")
            if not raw.strip() or raw in seen:
                continue
            seen.add(raw)
            try:
                row = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if not isinstance(row, dict):
                continue
            normalized = _normalize_hermes_event(row)
            if not normalized:
                continue
            if _already_emitted(target, json.dumps(normalized, ensure_ascii=False)):
                continue
            dst.write(json.dumps(normalized, ensure_ascii=False) + "\n")
            emitted += 1

    return {"ok": True, "emitted": emitted, "mode": "sync"}


def watch(poll_ms: int = 1000) -> None:
    print(f"Hermes telemetry bridge -> {HERMES_EVENTS} (poll {poll_ms}ms)")
    last_size = -1
    while True:
        try:
            stat = HERMES_LOG.stat()
        except FileNotFoundError:
            last_size = -1
        else:
            size = stat.st_size
            if size != last_size:
                result = emit_events()
                if result.get("emitted"):
                    print(json.dumps(result, ensure_ascii=False))
                last_size = size
        time.sleep(poll_ms / 1000)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "watch":
        watch()
    else:
        print(json.dumps(emit_events(), ensure_ascii=False))
