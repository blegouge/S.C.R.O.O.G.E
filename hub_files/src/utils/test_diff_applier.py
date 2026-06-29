#!/usr/bin/env python3
"""Unit tests for diff_applier."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from diff_applier import (
    AmbiguousSearchError,
    ApplyResult,
    SearchNotFoundError,
    apply_blocks,
    apply_text,
    parse_blocks,
)


class ParseBlocksTests(unittest.TestCase):
    def test_single_hunk(self) -> None:
        text = """path: src/a.py
<<<<<<< SEARCH
old
=======
new
>>>>>>> REPLACE
"""
        blocks = parse_blocks(text)
        self.assertEqual(len(blocks), 1)
        self.assertEqual(blocks[0].path, "src/a.py")
        self.assertEqual(blocks[0].search, "old")
        self.assertEqual(blocks[0].replace, "new")

    def test_multiple_hunks_same_file(self) -> None:
        text = """path: x.ts
<<<<<<< SEARCH
a
=======
b
>>>>>>> REPLACE
<<<<<<< SEARCH
c
=======
d
>>>>>>> REPLACE
"""
        blocks = parse_blocks(text)
        self.assertEqual(len(blocks), 2)
        self.assertEqual(blocks[0].search, "a")
        self.assertEqual(blocks[1].search, "c")


class ApplyBlocksTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.file = self.root / "hello.txt"
        self.file.write_text("line1\nline2\nline3\n", encoding="utf-8")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_apply_success(self) -> None:
        blocks = parse_blocks(
            """path: hello.txt
<<<<<<< SEARCH
line2
=======
LINE2
>>>>>>> REPLACE
"""
        )
        result = apply_blocks(blocks, [self.root])
        self.assertTrue(result.ok)
        self.assertIn("LINE2", self.file.read_text(encoding="utf-8"))
        self.assertGreater(result.stats.estimated_chars_saved, 0)

    def test_search_not_found(self) -> None:
        blocks = parse_blocks(
            """path: hello.txt
<<<<<<< SEARCH
missing
=======
x
>>>>>>> REPLACE
"""
        )
        result = apply_blocks(blocks, [self.root])
        self.assertFalse(result.ok)
        self.assertTrue(any("not found" in e.lower() for e in result.errors))

    def test_ambiguous_search(self) -> None:
        self.file.write_text("dup\ndup\n", encoding="utf-8")
        blocks = parse_blocks(
            """path: hello.txt
<<<<<<< SEARCH
dup
=======
once
>>>>>>> REPLACE
"""
        )
        result = apply_blocks(blocks, [self.root])
        self.assertFalse(result.ok)
        self.assertTrue(any("matches 2" in e for e in result.errors))

    def test_new_file_empty_search(self) -> None:
        blocks = parse_blocks(
            """path: new.txt
<<<<<<< SEARCH

=======
content
>>>>>>> REPLACE
"""
        )
        result = apply_blocks(blocks, [self.root])
        self.assertTrue(result.ok)
        self.assertEqual((self.root / "new.txt").read_text(encoding="utf-8"), "content")


class ApplyTextTests(unittest.TestCase):
    def test_no_blocks_is_noop(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = apply_text("no patches here", [Path(tmp)])
            self.assertTrue(result.ok)
            self.assertEqual(result.stats.blocks_parsed, 0)


if __name__ == "__main__":
    unittest.main()
