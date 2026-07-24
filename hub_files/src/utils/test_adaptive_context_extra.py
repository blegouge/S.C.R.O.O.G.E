#!/usr/bin/env python3
"""Extra coverage for adaptive_context_manager: parsing, cache misses, git errors."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from utils import adaptive_context_manager as acm
from utils.adaptive_context_manager import (
    AdaptiveContextConfig,
    AdaptiveContextManager,
    GitPreflightCache,
    GitRepoSnapshot,
    _extract_kv_pairs,
    _run_git,
    _sanitize_porcelain_for_signature,
    collect_git_repo_snapshot,
    estimate_messages_tokens,
    find_git_repo_root,
    local_kv_summarizer,
)

CACHE_VERSION = acm.CACHE_SCHEMA_VERSION


class TokenEstimationTests(unittest.TestCase):
    def test_estimate_messages_tokens_list_content(self) -> None:
        messages = [
            {"role": "user", "content": "plain string"},
            {"role": "assistant", "content": [{"text": "structured chunk"}, {"noise": 1}]},
            {"role": "system", "content": 42},
        ]
        self.assertGreater(estimate_messages_tokens(messages), 0)


class PorcelainSanitizeTests(unittest.TestCase):
    def test_gemini_and_regex_artifacts_removed(self) -> None:
        porcelain = "\n".join(
            [
                " M src/keep.py",
                "?? .gemini/antigravity/projects/cache_abcd.json",
                "?? some/projects/cache_ffff.json",
            ]
        )
        filtered = _sanitize_porcelain_for_signature(porcelain)
        self.assertIn("keep.py", filtered)
        self.assertNotIn("cache_abcd", filtered)
        self.assertNotIn("cache_ffff", filtered)


class RunGitTests(unittest.TestCase):
    def test_run_git_nonzero_returns_empty(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(_run_git(Path(tmp), "rev-parse", "HEAD"), "")

    def test_run_git_oserror_returns_empty(self) -> None:
        with patch.object(acm.subprocess, "run", side_effect=OSError("no git")):
            self.assertEqual(_run_git(Path("/tmp"), "status"), "")


class FindRepoRootTests(unittest.TestCase):
    def test_none_start(self) -> None:
        self.assertIsNone(find_git_repo_root(None))

    def test_nonexistent_path(self) -> None:
        self.assertIsNone(find_git_repo_root("/no/such/path/xyz"))

    def test_no_git_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(find_git_repo_root(tmp))

    def test_finds_git_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / ".git").mkdir()
            self.assertEqual(find_git_repo_root(tmp), Path(tmp).resolve())


class CollectSnapshotTests(unittest.TestCase):
    def test_returns_none_when_not_git(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(collect_git_repo_snapshot(tmp))


class CacheLoadMissTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.cache = GitPreflightCache(projects_dir=Path(self.tmp.name))
        self.sig = "0123456789abcdef"

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _write_raw(self, raw: str) -> None:
        self.cache.cache_path(self.sig).write_text(raw, encoding="utf-8")

    def _load(self, **kw):
        defaults = {"history_fingerprint": "fp", "summarizer_mode": "auto"}
        defaults.update(kw)
        return self.cache.load(self.sig, **defaults)

    def test_missing_file(self) -> None:
        self.assertIsNone(self._load())

    def test_invalid_json(self) -> None:
        self._write_raw("{not json")
        self.assertIsNone(self._load())

    def test_not_a_dict(self) -> None:
        self._write_raw("[1, 2, 3]")
        self.assertIsNone(self._load())

    def test_version_mismatch(self) -> None:
        self._write_raw(json.dumps({"version": 999}))
        self.assertIsNone(self._load())

    def test_signature_mismatch(self) -> None:
        self._write_raw(json.dumps({"version": CACHE_VERSION, "git_signature": "other"}))
        self.assertIsNone(self._load())

    def test_summarizer_mode_mismatch(self) -> None:
        self._write_raw(
            json.dumps(
                {
                    "version": CACHE_VERSION,
                    "git_signature": self.sig,
                    "history_fingerprint": "fp",
                    "summarizer_mode": "heuristic",
                }
            )
        )
        self.assertIsNone(self._load(summarizer_mode="auto"))

    def test_kv_not_dict(self) -> None:
        self._write_raw(
            json.dumps(
                {
                    "version": CACHE_VERSION,
                    "git_signature": self.sig,
                    "history_fingerprint": "fp",
                    "summarizer_mode": "auto",
                    "global_state_kv": "nope",
                }
            )
        )
        self.assertIsNone(self._load())

    def test_block2_fallback_rebuilt(self) -> None:
        self._write_raw(
            json.dumps(
                {
                    "version": CACHE_VERSION,
                    "git_signature": self.sig,
                    "history_fingerprint": "fp",
                    "summarizer_mode": "auto",
                    "global_state_kv": {"K": "v"},
                }
            )
        )
        entry = self._load()
        self.assertIsNotNone(entry)
        self.assertIn("[GLOBAL_STATE_KV]", entry.block_2_content)


class CacheSaveErrorTests(unittest.TestCase):
    def test_save_oserror_returns_none(self) -> None:
        from utils.adaptive_context_manager import Block2CacheEntry

        with tempfile.TemporaryDirectory() as tmp:
            cache = GitPreflightCache(projects_dir=Path(tmp))
            snapshot = GitRepoSnapshot("main", "sha", "", tmp)
            entry = Block2CacheEntry(
                global_state_kv={"K": "v"},
                history_fingerprint="fp",
                summarizer_mode="auto",
                git_snapshot=snapshot,
            )
            with patch.object(Path, "write_text", side_effect=OSError("disk full")):
                self.assertIsNone(cache.save("sig", entry))


class KvExtractionTests(unittest.TestCase):
    def test_extract_skips_and_dedup_and_limit(self) -> None:
        text = "\n".join(
            [
                "no colon here",
                "Key: value1",
                "Key: value2",  # duplicate -> skipped
                ": empty key",  # empty key -> skipped
                "user: hello",  # normalized to Last_User_Turn
            ]
        )
        kv = _extract_kv_pairs(text, max_items=2)
        self.assertEqual(kv.get("Key"), "value1")
        self.assertIn("Last_User_Turn", kv)

    def test_local_summarizer_fallback_chunks(self) -> None:
        text = "First sentence. Second sentence. Third one!"
        summary = local_kv_summarizer(text)
        self.assertIn("Conversation_Focus", summary)
        self.assertIn("Pending_Item", summary)


class TryLoadBlock2MetaTests(unittest.TestCase):
    def _manager(self, **cfg) -> AdaptiveContextManager:
        with tempfile.TemporaryDirectory() as tmp:
            cache = GitPreflightCache(projects_dir=Path(tmp))
        return AdaptiveContextManager(config=AdaptiveContextConfig(**cfg), git_cache=cache)

    def test_disabled(self) -> None:
        mgr = self._manager(enable_git_cache=False)
        state, meta = mgr.try_load_block2_cache(
            repo_root=None, history_messages=[{"role": "u", "content": "x"}], previous_state={}
        )
        self.assertIsNone(state)
        self.assertEqual(meta["cache_reason"], "disabled")

    def test_below_threshold(self) -> None:
        mgr = self._manager(message_threshold=100, token_threshold=999999)
        state, meta = mgr.try_load_block2_cache(
            repo_root=None, history_messages=[{"role": "u", "content": "x"}], previous_state={}
        )
        self.assertIsNone(state)
        self.assertEqual(meta["cache_reason"], "below_threshold")

    def test_not_git(self) -> None:
        mgr = self._manager(message_threshold=0, token_threshold=0)
        with tempfile.TemporaryDirectory() as tmp:
            state, meta = mgr.try_load_block2_cache(
                repo_root=tmp,
                history_messages=[{"role": "u", "content": "long enough text here"}],
                previous_state={},
            )
        self.assertIsNone(state)
        self.assertEqual(meta["cache_reason"], "not_git")


class PersistBlock2Tests(unittest.TestCase):
    def test_disabled(self) -> None:
        mgr = AdaptiveContextManager(config=AdaptiveContextConfig(enable_git_cache=False))
        meta = mgr.persist_block2_cache(
            repo_root=None, history_messages=[], previous_state={}, merged_state={}
        )
        self.assertFalse(meta["cache_saved"])

    def test_not_git(self) -> None:
        mgr = AdaptiveContextManager()
        with tempfile.TemporaryDirectory() as tmp:
            meta = mgr.persist_block2_cache(
                repo_root=tmp, history_messages=[], previous_state={}, merged_state={"K": "v"}
            )
        self.assertFalse(meta["cache_saved"])


class CompactHistoryEdgeTests(unittest.TestCase):
    def test_empty_history(self) -> None:
        mgr = AdaptiveContextManager()
        recent, state, stats = mgr.compact_history([], {"K": "v"})
        self.assertEqual(recent, [])
        self.assertFalse(stats["compacted"])

    def test_below_threshold_returns_unchanged(self) -> None:
        mgr = AdaptiveContextManager(
            config=AdaptiveContextConfig(message_threshold=100, token_threshold=999999)
        )
        history = [{"role": "user", "content": "hi"}]
        recent, state, stats = mgr.compact_history(history, {})
        self.assertFalse(stats["compacted"])
        self.assertEqual(recent, history)


class BuildCacheFriendlyTests(unittest.TestCase):
    def test_block_order_and_content(self) -> None:
        mgr = AdaptiveContextManager(config=AdaptiveContextConfig(recent_history_window=2))
        history = [
            {"role": "user", "content": "old"},
            {"role": "assistant", "content": "mid"},
            {"role": "user", "content": "recent"},
        ]
        out = mgr.build_cache_friendly_messages(
            static_system_block="  SYSTEM  ",
            global_state={"K": "v"},
            history_messages=history,
            latest_user_message="hello",
            ephemeral={"x": 1},
        )
        self.assertEqual(out[0]["content"], "SYSTEM")
        self.assertIn("[GLOBAL_STATE_KV]", out[1]["content"])
        self.assertIn("[LATEST_INPUT]", out[-1]["content"])
        # recent_history_window=2 keeps last 2 history messages between blocks 2 and 4.
        self.assertEqual(len(out), 5)


if __name__ == "__main__":
    unittest.main()
