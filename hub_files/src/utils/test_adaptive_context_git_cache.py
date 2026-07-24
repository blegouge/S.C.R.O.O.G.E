#!/usr/bin/env python3
"""Tests for Git pre-flight BLOCK_2 cache."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from utils.adaptive_context_manager import (
    AdaptiveContextConfig,
    AdaptiveContextManager,
    GitPreflightCache,
    GitRepoSnapshot,
    _sanitize_porcelain_for_signature,
    collect_git_repo_snapshot,
    compute_git_signature,
    local_kv_summarizer,
)


class GitPreflightCacheTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.projects_dir = Path(self.temp_dir.name)
        self.cache = GitPreflightCache(projects_dir=self.projects_dir)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_porcelain_filter_ignores_cache_artifacts(self) -> None:
        porcelain = "\n".join(
            [
                " M src/foo.py",
                "?? .cursor/projects/cache_deadbeef.json",
                "?? projects/cache_cafebabe.json",
            ]
        )
        filtered = _sanitize_porcelain_for_signature(porcelain)
        self.assertIn("src/foo.py", filtered)
        self.assertNotIn("cache_deadbeef", filtered)
        self.assertNotIn("cache_cafebabe", filtered)

    def test_signature_is_stable_for_same_snapshot(self) -> None:
        snapshot = GitRepoSnapshot(
            branch="main",
            commit_sha="abc123",
            porcelain=" M file.py",
            repo_root="/tmp/repo",
        )
        first = compute_git_signature(snapshot)
        second = compute_git_signature(snapshot)
        self.assertEqual(first, second)
        self.assertEqual(len(first), 16)

    def test_save_and_load_roundtrip(self) -> None:
        snapshot = GitRepoSnapshot(
            branch="feature/x",
            commit_sha="deadbeef",
            porcelain="",
            repo_root="/tmp/repo",
        )
        signature = compute_git_signature(snapshot)
        entry_state = {"Active_Branch": "feature/x", "Status": "ready"}
        from utils.adaptive_context_manager import Block2CacheEntry, format_block_2_content

        entry = Block2CacheEntry(
            global_state_kv=entry_state,
            history_fingerprint="fp123",
            summarizer_mode="heuristic",
            git_snapshot=snapshot,
            block_2_content=format_block_2_content(entry_state),
            created_at="2026-05-29T12:00:00+00:00",
        )
        saved = self.cache.save(signature, entry)
        self.assertIsNotNone(saved)
        loaded = self.cache.load(
            signature,
            history_fingerprint="fp123",
            summarizer_mode="heuristic",
        )
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.global_state_kv, entry_state)

    def test_load_miss_on_fingerprint_mismatch(self) -> None:
        snapshot = GitRepoSnapshot(
            branch="main",
            commit_sha="abc",
            porcelain="",
            repo_root="/tmp/repo",
        )
        signature = compute_git_signature(snapshot)
        from utils.adaptive_context_manager import Block2CacheEntry

        self.cache.save(
            signature,
            Block2CacheEntry(
                global_state_kv={"K": "v"},
                history_fingerprint="old",
                summarizer_mode="auto",
                git_snapshot=snapshot,
            ),
        )
        self.assertIsNone(
            self.cache.load(
                signature,
                history_fingerprint="new",
                summarizer_mode="auto",
            )
        )


class AdaptiveContextManagerCacheTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_compact_history_skips_summarizer_on_cache_hit(self) -> None:
        calls: list[str] = []

        def tracking_summarizer(text: str, max_items: int = 12) -> dict[str, str]:
            calls.append(text)
            return local_kv_summarizer(text, max_items=max_items)

        def mock_run_git(repo_root: Path, *args: str, timeout_sec: float = 2.0) -> str:
            if "status" in args:
                return ""
            if "--abbrev-ref" in args:
                return "main"
            return "abc123commitsha"

        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "README.md").write_text("hello\n", encoding="utf-8")

            with (
                patch("utils.adaptive_context_manager.find_git_repo_root", return_value=repo),
                patch("utils.adaptive_context_manager._run_git", side_effect=mock_run_git),
            ):
                projects_dir = Path(self.temp_dir.name) / "cursor_projects"
                manager = AdaptiveContextManager(
                    config=AdaptiveContextConfig(
                        message_threshold=2,
                        token_threshold=10,
                        keep_recent_messages=1,
                        enable_git_cache=True,
                        summarizer_mode="heuristic",
                    ),
                    summarize_fn=tracking_summarizer,
                    git_cache=GitPreflightCache(projects_dir=projects_dir),
                )

                history = [
                    {"role": "user", "content": "first question with enough text to count"},
                    {"role": "assistant", "content": "first answer with enough text to count"},
                    {"role": "user", "content": "second question with enough text to count"},
                ]

                _, state1, stats1 = manager.compact_history(
                    history,
                    {},
                    repo_root=repo,
                    summarizer_mode="heuristic",
                )
                self.assertTrue(stats1.get("compacted"))
                self.assertFalse(stats1.get("cache_hit"))
                self.assertEqual(len(calls), 1)

                calls.clear()
                _, state2, stats2 = manager.compact_history(
                    history,
                    {},
                    repo_root=repo,
                    summarizer_mode="heuristic",
                )
                self.assertTrue(stats2.get("cache_hit"))
                self.assertTrue(stats2.get("summarizer_skipped"))
                self.assertEqual(len(calls), 0)
                self.assertEqual(state1, state2)

                snapshot = collect_git_repo_snapshot(repo)
                self.assertIsNotNone(snapshot)
                signature = compute_git_signature(snapshot)  # type: ignore[arg-type]
                cache_file = projects_dir / f"cache_{signature}.json"
                self.assertTrue(cache_file.is_file())
                payload = json.loads(cache_file.read_text(encoding="utf-8"))
                self.assertIn("global_state_kv", payload)


if __name__ == "__main__":
    unittest.main()
