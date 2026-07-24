#!/usr/bin/env python3
"""Extra coverage for telemetry_db: sync edge cases, sync_all_enabled, fetch."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[3]
for sub in ["src/telemetry", "src/compaction", "src/bridge", "hub_files/src"]:
    p = PROJECT_ROOT / sub
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import telemetry_db as db


class SyncSourceEdgeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / "t.db"
        self._orig = db.get_db_path
        db.get_db_path = lambda: self.db_path

    def tearDown(self) -> None:
        db.get_db_path = self._orig
        self.tmp.cleanup()

    def test_missing_log_returns_zero(self) -> None:
        self.assertEqual(db.sync_source("cursor", Path(self.tmp.name) / "absent.jsonl"), 0)

    def test_skips_empty_invalid_and_non_dict_lines(self) -> None:
        log = Path(self.tmp.name) / "events.jsonl"
        log.write_text(
            '\n{"event": "a", "ts": "t1", "session_id": "s"}\n'
            "not-json\n"
            "[1, 2, 3]\n"
            '{"event": "b", "ts": "t2"}\n',
            encoding="utf-8",
        )
        inserted = db.sync_source("cursor", log)
        self.assertEqual(inserted, 2)

    def test_read_error_returns_zero(self) -> None:
        log = Path(self.tmp.name) / "events.jsonl"
        log.write_text('{"event": "a"}\n', encoding="utf-8")
        with patch.object(Path, "read_text", side_effect=OSError("boom")):
            self.assertEqual(db.sync_source("cursor", log), 0)

    def test_truncation_resets_pointer(self) -> None:
        log = Path(self.tmp.name) / "events.jsonl"
        log.write_text('{"event": "a", "ts": "t1"}\n{"event": "b", "ts": "t2"}\n', encoding="utf-8")
        self.assertEqual(db.sync_source("cursor", log), 2)
        # Rewrite smaller -> truncation path resets and re-inserts.
        log.write_text('{"event": "c", "ts": "t3"}\n', encoding="utf-8")
        self.assertEqual(db.sync_source("cursor", log), 1)

    def test_fetch_events_from_db(self) -> None:
        log = Path(self.tmp.name) / "events.jsonl"
        log.write_text('{"event": "a", "ts": "t1", "source": "cursor"}\n', encoding="utf-8")
        db.sync_source("cursor", log)
        events = db.fetch_events_from_db("cursor")
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["event"], "a")


class SyncAllEnabledTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / "t.db"
        self._orig = db.get_db_path
        db.get_db_path = lambda: self.db_path

    def tearDown(self) -> None:
        db.get_db_path = self._orig
        self.tmp.cleanup()

    def test_sync_all_enabled(self) -> None:
        data_dir = Path(self.tmp.name) / "data"
        data_dir.mkdir()
        (data_dir / "events.jsonl").write_text('{"event": "x", "ts": "t1"}\n', encoding="utf-8")
        import providers_config as pc

        with patch.object(pc, "get_enabled_providers", return_value=[{"id": "cursor"}]):
            with patch.object(pc, "get_data_dir", return_value=data_dir):
                results = db.sync_all_enabled()
        self.assertEqual(results.get("cursor"), 1)

    def test_sync_all_enabled_handles_errors(self) -> None:
        import providers_config as pc

        with patch.object(pc, "get_enabled_providers", side_effect=RuntimeError("x")):
            self.assertEqual(db.sync_all_enabled(), {})


if __name__ == "__main__":
    unittest.main()
