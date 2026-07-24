#!/usr/bin/env python3
"""Extra coverage for diff_applier: parsing, resolution, apply flow, CLI, telemetry."""

from __future__ import annotations

import io
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

from utils import diff_applier as da


def _hunk(path: str, search: str, replace: str) -> str:
    return (
        f"path: {path}\n"
        f"{da.MARKER_SEARCH}\n{search}\n{da.MARKER_SEP}\n{replace}\n{da.MARKER_REPLACE}\n"
    )


class HelperTests(unittest.TestCase):
    def test_strip_markdown_fences(self) -> None:
        fenced = "```\npath: a\ncontent\n```"
        self.assertEqual(da._strip_markdown_fences(fenced), "path: a\ncontent")
        self.assertEqual(da._strip_markdown_fences("no fence"), "no fence")

    def test_extract_response_text_direct(self) -> None:
        self.assertEqual(da.extract_response_text({"text": "hello"}), "hello")

    def test_extract_response_text_fallback_walk(self) -> None:
        payload = {"data": {"nested": "path: a.txt\n" + da.MARKER_SEARCH}}
        out = da.extract_response_text(payload)
        self.assertIn(da.MARKER_SEARCH, out)

    def test_count_occurrences(self) -> None:
        self.assertEqual(da._count_occurrences("aaa", ""), 0)
        self.assertEqual(da._count_occurrences("abcabc", "abc"), 2)
        self.assertEqual(da._count_occurrences("abc", "z"), 0)


class ResolveTests(unittest.TestCase):
    def test_resolve_workspace_roots_from_list_and_cwd(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            roots = da.resolve_workspace_roots({"workspace_roots": [tmp]})
            self.assertIn(Path(tmp).resolve(), roots)

    def test_resolve_file_absolute(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            f = Path(tmp) / "abs.txt"
            f.write_text("x", encoding="utf-8")
            self.assertEqual(da._resolve_file(str(f), []), f.resolve())

    def test_resolve_file_relative_no_roots_raises(self) -> None:
        with self.assertRaises(da.WorkspaceNotFoundError):
            da._resolve_file("rel/path.txt", [])

    def test_resolve_file_relative_existing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "sub").mkdir()
            f = root / "sub" / "f.txt"
            f.write_text("x", encoding="utf-8")
            self.assertEqual(da._resolve_file("sub/f.txt", [root]), f.resolve())


class ParseBlocksTests(unittest.TestCase):
    def test_no_marker_returns_empty(self) -> None:
        self.assertEqual(da.parse_blocks("nothing here"), [])

    def test_single_block(self) -> None:
        blocks = da.parse_blocks(_hunk("a.txt", "old", "new"))
        self.assertEqual(len(blocks), 1)
        self.assertEqual(blocks[0].path, "a.txt")
        self.assertEqual(blocks[0].search, "old")
        self.assertEqual(blocks[0].replace, "new")

    def test_path_reuse_across_hunks(self) -> None:
        text = (
            "path: a.txt\n"
            f"{da.MARKER_SEARCH}\nfoo\n{da.MARKER_SEP}\nFOO\n{da.MARKER_REPLACE}\n"
            f"{da.MARKER_SEARCH}\nbar\n{da.MARKER_SEP}\nBAR\n{da.MARKER_REPLACE}\n"
        )
        blocks = da.parse_blocks(text)
        self.assertEqual(len(blocks), 2)
        self.assertTrue(all(b.path == "a.txt" for b in blocks))


class ApplyOneTests(unittest.TestCase):
    def test_new_file_empty_search(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "new.txt"
            content, normalized = da._apply_one(target, "", "created")
            self.assertEqual(content, "created")
            self.assertFalse(normalized)

    def test_empty_search_existing_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "e.txt"
            target.write_text("data", encoding="utf-8")
            with self.assertRaises(da.DiffApplyError):
                da._apply_one(target, "", "x")

    def test_exact_match_single(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "f.txt"
            target.write_text("hello world", encoding="utf-8")
            content, _ = da._apply_one(target, "hello", "hi")
            self.assertEqual(content, "hi world")

    def test_ambiguous_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "f.txt"
            target.write_text("x x x", encoding="utf-8")
            with self.assertRaises(da.AmbiguousSearchError):
                da._apply_one(target, "x", "y")

    def test_not_found_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "f.txt"
            target.write_text("abc", encoding="utf-8")
            with self.assertRaises(da.SearchNotFoundError):
                da._apply_one(target, "zzz", "y")


class ApplyFlowTests(unittest.TestCase):
    def test_apply_text_writes_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            f = root / "a.txt"
            f.write_text("hello world\n", encoding="utf-8")
            result = da.apply_text(_hunk("a.txt", "hello world", "hi world"), [root])
            self.assertTrue(result.ok)
            self.assertEqual(result.stats.blocks_applied, 1)
            self.assertEqual(f.read_text(encoding="utf-8"), "hi world\n")

    def test_apply_text_dry_run_does_not_write(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            f = root / "a.txt"
            f.write_text("keep", encoding="utf-8")
            result = da.apply_text(_hunk("a.txt", "keep", "changed"), [root], dry_run=True)
            self.assertTrue(result.ok)
            self.assertEqual(f.read_text(encoding="utf-8"), "keep")

    def test_apply_text_collects_errors(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a.txt").write_text("abc", encoding="utf-8")
            result = da.apply_text(_hunk("a.txt", "missing", "x"), [root])
            self.assertFalse(result.ok)
            self.assertTrue(result.errors)

    def test_apply_blocks_empty(self) -> None:
        result = da.apply_blocks([], [])
        self.assertTrue(result.ok)
        self.assertEqual(result.stats.blocks_parsed, 0)


class OutputTests(unittest.TestCase):
    def test_log_savings_writes_stream(self) -> None:
        stream = io.StringIO()
        stats = da.ApplyStats(blocks_applied=1, blocks_parsed=2, files_touched=1)
        da.log_savings(stats, stream=stream)
        self.assertIn("diff-only", stream.getvalue())

    def test_stats_to_log_dict(self) -> None:
        d = da.ApplyStats(blocks_parsed=3).to_log_dict()
        self.assertEqual(d["blocks_parsed"], 3)

    def test_append_telemetry_writes_events(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with patch("pathlib.Path.home", return_value=Path(tmp)):
                da.append_telemetry(da.ApplyStats(blocks_applied=1), "diffOnlyApplyTest", [])
                log = Path(tmp) / ".cursor" / "token-telemetry" / "events.jsonl"
                self.assertTrue(log.is_file())


class MainCliTests(unittest.TestCase):
    def test_main_dry_run_ok(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a.txt").write_text("hello\n", encoding="utf-8")
            inp = root / "in.txt"
            inp.write_text(_hunk("a.txt", "hello", "bye"), encoding="utf-8")
            rc = da.main([str(inp), "--dry-run", "--workspace", str(root)])
            self.assertEqual(rc, 0)

    def test_main_returns_error_code(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a.txt").write_text("abc", encoding="utf-8")
            inp = root / "in.txt"
            inp.write_text(_hunk("a.txt", "missing", "x"), encoding="utf-8")
            rc = da.main([str(inp), "--workspace", str(root)])
            self.assertEqual(rc, 1)


if __name__ == "__main__":
    unittest.main()
