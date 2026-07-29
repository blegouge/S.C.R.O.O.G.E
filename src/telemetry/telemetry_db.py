#!/usr/bin/env python3
"""SQLite database interface for local telemetry event logs."""

from __future__ import annotations

import json
import pathlib
import sqlite3
import sys
from typing import Any

from telemetry_paths import resolve_data_dir

DB_FILE_NAME = "telemetry.db"


def get_db_path() -> pathlib.Path:
    """Resolve absolute path to the SQLite database file."""
    # Store the DB in the default common token-telemetry directory (usually ~/.cursor/token-telemetry)
    return resolve_data_dir(None) / DB_FILE_NAME


def get_db_connection() -> sqlite3.Connection:
    """Create a new SQLite connection with row factory enabled."""
    db_path = get_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Initialize the SQLite database schema and indexes."""
    conn = get_db_connection()
    try:
        with conn:
            # Create events table
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts TEXT,
                    source TEXT,
                    event TEXT,
                    session_id TEXT,
                    conversation_id TEXT,
                    payload TEXT,
                    sync_source TEXT,
                    line_no INTEGER
                )
                """
            )
            # Databases created before deduplication lack the identity columns.
            columns = {row[1] for row in conn.execute("PRAGMA table_info(events)")}
            if "sync_source" not in columns:
                conn.execute("ALTER TABLE events ADD COLUMN sync_source TEXT")
            if "line_no" not in columns:
                conn.execute("ALTER TABLE events ADD COLUMN line_no INTEGER")

            # Create indexes for rapid querying
            conn.execute("CREATE INDEX IF NOT EXISTS idx_events_ts ON events(ts)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_events_source ON events(source)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_events_event ON events(event)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_events_session ON events(session_id)")
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_events_conversation ON events(conversation_id)"
            )
            # (sync_source, line_no) identifies a log line and makes re-ingestion
            # idempotent, so a truncated or rotated log can no longer duplicate
            # rows. Legacy rows keep both columns NULL, which SQLite treats as
            # distinct, so the index can be created without a prior cleanup.
            conn.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_events_sync_line "
                "ON events(sync_source, line_no)"
            )

            # Create sync_state table to track position in JSONL files
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS sync_state (
                    source TEXT PRIMARY KEY,
                    last_line_count INTEGER NOT NULL
                )
                """
            )
    finally:
        conn.close()


def sync_source(source: str, log_file_path: pathlib.Path) -> int:
    """Sync a single JSONL log file to SQLite incrementally.

    Returns the number of log lines ingested, whether inserted or refreshed.
    """
    if not log_file_path.is_file():
        return 0

    init_db()
    conn = get_db_connection()
    try:
        # Get last synced line count
        cursor = conn.cursor()
        cursor.execute("SELECT last_line_count FROM sync_state WHERE source = ?", (source,))
        row = cursor.fetchone()
        last_line_count = row["last_line_count"] if row else 0

        # Read the file lines
        try:
            lines = log_file_path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError as exc:
            sys.stderr.write(f"[sqlite-sync] Read error on {log_file_path}: {exc}\n")
            return 0

        total_lines = len(lines)
        if total_lines < last_line_count:
            # File was truncated, cleared, or rotated -> reset sync pointer
            last_line_count = 0

        if total_lines == last_line_count:
            return 0  # Nothing new to sync

        new_lines = lines[last_line_count:]
        ingested = 0

        with conn:
            for offset, raw_line in enumerate(new_lines):
                line_no = last_line_count + offset
                line = raw_line.strip()
                if not line:
                    continue
                try:
                    event_data = json.loads(line)
                except json.JSONDecodeError:
                    continue

                if not isinstance(event_data, dict):
                    continue

                # Normalise common fields for quick querying
                event_source = event_data.get("source", source)
                event_name = event_data.get("event", "")
                ts = event_data.get("ts", "")
                session_id = event_data.get("session_id", "")
                conversation_id = event_data.get("conversation_id", "")

                # Upsert on (sync_source, line_no): replaying a log line refreshes
                # the row in place instead of appending a duplicate.
                conn.execute(
                    """
                    INSERT INTO events (
                        ts, source, event, session_id, conversation_id, payload,
                        sync_source, line_no
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(sync_source, line_no) DO UPDATE SET
                        ts = excluded.ts,
                        source = excluded.source,
                        event = excluded.event,
                        session_id = excluded.session_id,
                        conversation_id = excluded.conversation_id,
                        payload = excluded.payload
                    """,
                    (
                        ts,
                        event_source,
                        event_name,
                        session_id,
                        conversation_id,
                        json.dumps(event_data, ensure_ascii=False),
                        source,
                        line_no,
                    ),
                )
                ingested += 1

            # Drop rows left behind by a log that shrank after truncation or rotation
            conn.execute(
                "DELETE FROM events WHERE sync_source = ? AND line_no >= ?",
                (source, total_lines),
            )

            # Update sync state atomically
            conn.execute(
                """
                INSERT INTO sync_state (source, last_line_count)
                VALUES (?, ?)
                ON CONFLICT(source) DO UPDATE SET last_line_count = ?
                """,
                (source, total_lines, total_lines),
            )

        return ingested
    finally:
        conn.close()


def sync_all_enabled() -> dict[str, int]:
    """Sync all enabled provider log files.

    Returns a dict mapping source ID to the number of new events inserted.
    """
    results: dict[str, int] = {}
    try:
        from providers_config import get_data_dir, get_enabled_providers

        for provider in get_enabled_providers():
            source = provider["id"]
            d = get_data_dir(source)
            if d:
                log_file = d / "events.jsonl"
                results[source] = sync_source(source, log_file)
    except Exception as exc:
        sys.stderr.write(f"[sqlite-sync] Error during sync: {exc}\n")
    return results


def fetch_events_from_db(source: str) -> list[dict[str, Any]]:
    """Retrieve all synced events for a specific source from SQLite."""
    init_db()
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT payload FROM events WHERE source = ? ORDER BY ts ASC",
            (source,),
        )
        rows = cursor.fetchall()
        events = []
        for r in rows:
            try:
                events.append(json.loads(r["payload"]))
            except json.JSONDecodeError:
                continue
        return events
    finally:
        conn.close()
