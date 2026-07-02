#!/usr/bin/env python3
"""Unit tests for the SQLite sync logic."""

from __future__ import annotations

import json

# Add project root to sys.path so we can import telemetry_db
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import telemetry_db


class SqliteSyncTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_telemetry.db"
        self.log_file = Path(self.temp_dir.name) / "events.jsonl"

        # Override the db path resolver
        self.original_get_db_path = telemetry_db.get_db_path
        telemetry_db.get_db_path = lambda: self.db_path

    def tearDown(self) -> None:
        telemetry_db.get_db_path = self.original_get_db_path
        self.temp_dir.cleanup()

    def test_sync_empty_file(self) -> None:
        # File doesn't exist
        inserted = telemetry_db.sync_source("test_source", self.log_file)
        self.assertEqual(inserted, 0)

        # Empty file exists
        self.log_file.touch()
        inserted = telemetry_db.sync_source("test_source", self.log_file)
        self.assertEqual(inserted, 0)

    def test_sync_incremental(self) -> None:
        # 1. Write 2 lines
        events = [
            {"event": "subagentLaunch", "approx_tokens": 100, "source": "test"},
            {"event": "postToolUse", "approx_tokens": 50, "source": "test"},
        ]
        lines = [json.dumps(ev) + "\n" for ev in events]
        self.log_file.write_text("".join(lines), encoding="utf-8")

        inserted = telemetry_db.sync_source("test", self.log_file)
        self.assertEqual(inserted, 2)

        # Verify events are in SQLite
        db_events = telemetry_db.fetch_events_from_db("test")
        self.assertEqual(len(db_events), 2)
        self.assertEqual(db_events[0]["event"], "subagentLaunch")

        # 2. Sync again without modifications
        inserted = telemetry_db.sync_source("test", self.log_file)
        self.assertEqual(inserted, 0)

        # 3. Append 1 new event
        new_event = {"event": "afterAgentResponse", "approx_tokens": 200, "source": "test"}
        with self.log_file.open("a", encoding="utf-8") as f:
            f.write(json.dumps(new_event) + "\n")

        inserted = telemetry_db.sync_source("test", self.log_file)
        self.assertEqual(inserted, 1)

        # Total should be 3 in DB
        db_events = telemetry_db.fetch_events_from_db("test")
        self.assertEqual(len(db_events), 3)
        self.assertEqual(db_events[2]["event"], "afterAgentResponse")

    def test_sync_file_truncated(self) -> None:
        # Write 2 lines and sync
        self.log_file.write_text(
            json.dumps({"event": "evt1", "source": "test"})
            + "\n"
            + json.dumps({"event": "evt2", "source": "test"})
            + "\n",
            encoding="utf-8",
        )
        telemetry_db.sync_source("test", self.log_file)

        # Truncate file (replace with 1 line)
        self.log_file.write_text(
            json.dumps({"event": "evt3", "source": "test"}) + "\n", encoding="utf-8"
        )

        # Sync should detect truncation (total lines 1 < last_line_count 2) and reset sync
        inserted = telemetry_db.sync_source("test", self.log_file)
        self.assertEqual(inserted, 1)

        db_events = telemetry_db.fetch_events_from_db("test")
        # In a real sync with truncation, we might have duplicate old rows in DB,
        # but the new sync should succeed and read the file from line 0.
        self.assertEqual(db_events[-1]["event"], "evt3")


if __name__ == "__main__":
    unittest.main()
