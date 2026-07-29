#!/usr/bin/env python3
"""Repair agent attribution across telemetry logs and the SQLite mirror.

Three independent steps, each opt-in:

--redeploy      push the fixed runtime (hooks, providers, token-telemetry) to
                every detected agent hub
--replay        move events sitting in the wrong agent log to the log of the
                agent that really produced them
--rebuild-db    drop and re-ingest the SQLite mirror so deduplication applies
                to the whole history

Without any of those flags the script only reports what it would do.

Attribution relies on identity markers carried by the events themselves:
`cursor_version` in `payload_keys`, and `transcript_path` pointing inside a
known agent home. Fields that merely reference edited files (`path`,
`file_hint`, `cwd`) are ignored: editing a file under ~/.claude from Cursor must
not make the event a Claude event.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "src" / "telemetry"))
sys.path.insert(0, str(REPO_ROOT / "hub_files"))

# Deployment roots, longest first: ~/.gemini/antigravity is nested in ~/.gemini.
AGENT_HOMES: tuple[tuple[str, str], ...] = (
    ("antigravity", ".gemini/antigravity"),
    ("codex", ".codex"),
    ("claude", ".claude"),
    ("hermes", ".hermes"),
    ("gemini", ".gemini"),
    ("cursor", ".cursor"),
)

# Payload keys that only one agent ever emits.
EXCLUSIVE_PAYLOAD_KEYS: dict[str, str] = {
    "cursor_version": "cursor",
}

# Event fields that identify the caller rather than the files it touched.
IDENTITY_FIELDS: tuple[str, ...] = ("transcript_path", "session_path", "hook_home")


def agent_log(agent: str) -> Path:
    for name, rel in AGENT_HOMES:
        if name == agent:
            return Path.home() / rel / "token-telemetry" / "events.jsonl"
    raise KeyError(agent)


def classify_event(event: dict[str, Any]) -> str | None:
    """Return the agent that really produced an event, or None when unknown."""
    payload_keys = event.get("payload_keys")
    if isinstance(payload_keys, list):
        for key, agent in EXCLUSIVE_PAYLOAD_KEYS.items():
            if key in payload_keys:
                return agent

    for field in IDENTITY_FIELDS:
        value = event.get(field)
        if not isinstance(value, str) or not value:
            continue
        for agent, rel in AGENT_HOMES:
            if f"/{rel}/" in value:
                return agent
    return None


def read_log(path: Path) -> tuple[list[tuple[str, dict[str, Any]]], list[str]]:
    """Return (parsed events with their raw line, unparsable raw lines)."""
    parsed: list[tuple[str, dict[str, Any]]] = []
    junk: list[str] = []
    if not path.is_file():
        return parsed, junk
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            junk.append(line)
            continue
        if isinstance(event, dict):
            parsed.append((line, event))
        else:
            junk.append(line)
    return parsed, junk


def plan_replay() -> tuple[dict[str, list[tuple[str, dict[str, Any]]]], list[str]]:
    """Compute the target agent log for every event of every agent log."""
    moves: dict[str, list[tuple[str, dict[str, Any]]]] = {}
    notes: list[str] = []

    for agent, _rel in AGENT_HOMES:
        path = agent_log(agent)
        parsed, junk = read_log(path)
        if not parsed:
            continue
        if junk:
            notes.append(f"{agent}: {len(junk)} unparsable line(s) dropped")

        identified = {origin for _line, event in parsed if (origin := classify_event(event))}
        foreign = identified - {agent}

        if not foreign:
            notes.append(f"{agent}: {len(parsed)} event(s) already correct")
            moves.setdefault(agent, []).extend(parsed)
            continue

        if len(identified) == 1:
            # The whole log belongs to a single other agent, so unmarked events
            # (compliance, diff-only) follow the marked ones without guessing.
            target = next(iter(identified))
            notes.append(
                f"{agent}: unanimous log, {len(parsed)} event(s) re-attributed to {target}"
            )
            moves.setdefault(target, []).extend(parsed)
            continue

        # Mixed log: only move what carries an explicit marker.
        kept = 0
        moved = 0
        for line, event in parsed:
            origin = classify_event(event)
            if origin and origin != agent:
                moves.setdefault(origin, []).append((line, event))
                moved += 1
            else:
                moves.setdefault(agent, []).append((line, event))
                kept += 1
        notes.append(f"{agent}: mixed log, {moved} event(s) moved, {kept} kept (unmarked)")

    return moves, notes


def write_log(path: Path, agent: str, entries: list[tuple[str, dict[str, Any]]], stamp: str) -> int:
    """Rewrite an agent log chronologically, keeping a timestamped backup.

    Returns how many events had a stale `source` field corrected. A few writers
    stamp the provider inside the payload, so a misattributed event carries the
    wrong name until it is rewritten here.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_file():
        shutil.copy2(path, path.with_suffix(f".jsonl.bak-{stamp}"))

    # Events without a timestamp keep their relative order at the head.
    ordered = sorted(entries, key=lambda item: item[1].get("ts") or "")

    corrected = 0
    lines: list[str] = []
    for line, event in ordered:
        if event.get("source") and event["source"] != agent:
            event["source"] = agent
            line = json.dumps(event, ensure_ascii=False)
            corrected += 1
        lines.append(line)

    tmp = path.with_suffix(f".jsonl.repair-{stamp}")
    tmp.write_text("".join(f"{line}\n" for line in lines), encoding="utf-8")
    tmp.replace(path)
    return corrected


def redeploy(hubs: list[Path]) -> None:
    from install_helpers import (
        copy_tree_idempotent,
        deploy_token_telemetry_runtime,
        prune_token_telemetry_runtime,
    )

    hub_files = REPO_ROOT / "hub_files"
    for hub in hubs:
        for folder in ("hooks", "providers", "src"):
            copy_tree_idempotent(
                hub_files / folder, hub / folder, ignore=["__pycache__"], overwrite=True
            )
        token_telemetry = hub / "token-telemetry"
        deploy_token_telemetry_runtime(REPO_ROOT, token_telemetry)
        prune_token_telemetry_runtime(token_telemetry)
        print(f"  redeployed runtime to {hub}")


def rebuild_db() -> None:
    import telemetry_db

    db_path = telemetry_db.get_db_path()
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    if db_path.is_file():
        shutil.copy2(db_path, db_path.with_name(f"{db_path.name}.bak-{stamp}"))

    telemetry_db.init_db()
    conn = telemetry_db.get_db_connection()
    try:
        with conn:
            conn.execute("DELETE FROM events")
            conn.execute("DELETE FROM sync_state")
    finally:
        conn.close()

    results = telemetry_db.sync_all_enabled()
    for source, count in sorted(results.items()):
        print(f"  {source}: {count} event(s) ingested")

    conn = telemetry_db.get_db_connection()
    try:
        rows = conn.execute("SELECT source, COUNT(*) FROM events GROUP BY source").fetchall()
    finally:
        conn.close()
    print(f"  database: {db_path}")
    for row in rows:
        print(f"    {row[0]}: {row[1]} row(s)")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--redeploy", action="store_true", help="Push fixed runtime to every hub")
    parser.add_argument("--replay", action="store_true", help="Re-attribute misplaced events")
    parser.add_argument("--rebuild-db", action="store_true", help="Drop and re-ingest SQLite")
    args = parser.parse_args(argv)

    hubs = [Path.home() / rel for _agent, rel in AGENT_HOMES if (Path.home() / rel).is_dir()]
    print(f"Detected hubs: {', '.join(str(h) for h in hubs)}")

    moves, notes = plan_replay()
    print("\nAttribution plan:")
    for note in notes:
        print(f"  {note}")
    print("\nResulting log sizes:")
    for agent, _rel in AGENT_HOMES:
        entries = moves.get(agent, [])
        current = len(read_log(agent_log(agent))[0])
        print(f"  {agent}: {current} -> {len(entries)}")

    if not (args.redeploy or args.replay or args.rebuild_db):
        print("\nReport only. Re-run with --redeploy --replay --rebuild-db to apply.")
        return 0

    if args.redeploy:
        print("\nRedeploying runtime:")
        redeploy(hubs)

    if args.replay:
        print("\nRewriting logs:")
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        for agent, _rel in AGENT_HOMES:
            path = agent_log(agent)
            entries = moves.get(agent, [])
            if not entries and not path.is_file():
                continue
            corrected = write_log(path, agent, entries, stamp)
            suffix = f", {corrected} source field(s) corrected" if corrected else ""
            print(f"  {path}: {len(entries)} event(s){suffix}")

    if args.rebuild_db:
        print("\nRebuilding SQLite mirror:")
        rebuild_db()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
