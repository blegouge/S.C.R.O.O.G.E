#!/usr/bin/env python3
"""Tests for flash_kv_summarizer helpers, provider routing and fallbacks (HTTP mocked)."""

from __future__ import annotations

import sys
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[3]
for sub in ["src/telemetry", "src/compaction", "src/bridge", "hub_files/src"]:
    p = PROJECT_ROOT / sub
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import flash_kv_summarizer as fk

_LONG = "This is a long conversation fragment. " * 20  # > 400 chars


class NormalizeTests(unittest.TestCase):
    def test_normalize_key(self) -> None:
        self.assertEqual(fk._normalize_key("Active Branch!"), "Active_Branch")
        self.assertEqual(fk._normalize_key("  __weird--key__  "), "weird_key")
        self.assertEqual(len(fk._normalize_key("x" * 100)), 64)

    def test_normalize_state_filters_and_truncates(self) -> None:
        raw = {
            "Status": "ok",
            "Empty": "   ",
            "None_Val": None,
            123: "bad key type",
            "Long": "y" * 500,
        }
        out = fk._normalize_state(raw, max_items=10)
        self.assertEqual(out["Status"], "ok")
        self.assertNotIn("Empty", out)
        self.assertNotIn("None_Val", out)
        self.assertEqual(len(out["Long"]), 240)

    def test_normalize_state_non_dict(self) -> None:
        self.assertEqual(fk._normalize_state(["a"], max_items=5), {})

    def test_normalize_state_max_items(self) -> None:
        raw = {f"K{i}": str(i) for i in range(20)}
        out = fk._normalize_state(raw, max_items=3)
        self.assertEqual(len(out), 3)

    def test_extract_json_object_fenced(self) -> None:
        out = fk._extract_json_object('```json\n{"A": "1"}\n```')
        self.assertEqual(out, {"A": "1"})

    def test_extract_json_object_braces(self) -> None:
        out = fk._extract_json_object('prefix {"B": "2"} suffix')
        self.assertEqual(out, {"B": "2"})

    def test_extract_json_object_invalid_and_empty(self) -> None:
        self.assertEqual(fk._extract_json_object("not json"), {})
        self.assertEqual(fk._extract_json_object(""), {})

    def test_build_user_prompt(self) -> None:
        prompt = fk._build_user_prompt("hello", 7)
        self.assertIn("7", prompt)
        self.assertIn("hello", prompt)


class DetectProviderTests(unittest.TestCase):
    def test_config_provider_wins(self) -> None:
        cfg = fk.FlashSummarizerConfig(provider="OpenAI")
        self.assertEqual(fk._detect_provider(cfg), "openai")

    def test_env_provider(self) -> None:
        with patch.dict("os.environ", {"FLASH_SUMMARIZER_PROVIDER": "anthropic"}, clear=True):
            self.assertEqual(fk._detect_provider(fk.FlashSummarizerConfig()), "anthropic")

    def test_openai_key_detection(self) -> None:
        with patch.dict("os.environ", {"OPENAI_API_KEY": "sk-x"}, clear=True):
            with patch.object(fk, "_ollama_reachable", return_value=False):
                self.assertEqual(fk._detect_provider(fk.FlashSummarizerConfig()), "openai")

    def test_anthropic_key_detection(self) -> None:
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "ak-x"}, clear=True):
            with patch.object(fk, "_ollama_reachable", return_value=False):
                self.assertEqual(fk._detect_provider(fk.FlashSummarizerConfig()), "anthropic")

    def test_no_provider(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            with patch.object(fk, "_ollama_reachable", return_value=False):
                self.assertEqual(fk._detect_provider(fk.FlashSummarizerConfig()), "")

    def test_ollama_reachable_handles_error(self) -> None:
        with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("down")):
            self.assertFalse(fk._ollama_reachable(fk.FlashSummarizerConfig()))


class ProviderCallTests(unittest.TestCase):
    def test_call_openai_no_key(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            self.assertEqual(fk._call_openai("t", 5, fk.FlashSummarizerConfig()), {})

    def test_call_openai_success(self) -> None:
        response = {"choices": [{"message": {"content": '{"Status": "done"}'}}]}
        with patch.dict("os.environ", {"OPENAI_API_KEY": "sk-x"}, clear=True):
            with patch.object(fk, "_http_post_json", return_value=response):
                out = fk._call_openai("t", 5, fk.FlashSummarizerConfig())
        self.assertEqual(out, {"Status": "done"})

    def test_call_openai_bad_shape(self) -> None:
        with patch.dict("os.environ", {"OPENAI_API_KEY": "sk-x"}, clear=True):
            with patch.object(fk, "_http_post_json", return_value={"choices": []}):
                self.assertEqual(fk._call_openai("t", 5, fk.FlashSummarizerConfig()), {})

    def test_call_ollama_success(self) -> None:
        response = {"message": {"content": '{"Branch": "main"}'}}
        with patch.dict("os.environ", {}, clear=True):
            with patch.object(fk, "_http_post_json", return_value=response):
                out = fk._call_ollama("t", 5, fk.FlashSummarizerConfig())
        self.assertEqual(out, {"Branch": "main"})

    def test_call_anthropic_no_key(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            self.assertEqual(fk._call_anthropic("t", 5, fk.FlashSummarizerConfig()), {})

    def test_call_anthropic_success(self) -> None:
        response = {"content": [{"type": "text", "text": '{"Decision": "ship"}'}]}
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "ak-x"}, clear=True):
            with patch.object(fk, "_http_post_json", return_value=response):
                out = fk._call_anthropic("t", 5, fk.FlashSummarizerConfig())
        self.assertEqual(out, {"Decision": "ship"})


class FlashSummarizeTests(unittest.TestCase):
    def test_short_text_returns_empty(self) -> None:
        self.assertEqual(fk.flash_kv_summarize("tiny"), {})

    def test_no_provider_returns_empty(self) -> None:
        cfg = fk.FlashSummarizerConfig(provider="")
        with patch.object(fk, "_detect_provider", return_value=""):
            self.assertEqual(fk.flash_kv_summarize(_LONG, config=cfg), {})

    def test_openai_path(self) -> None:
        cfg = fk.FlashSummarizerConfig(provider="openai")
        with patch.object(fk, "_call_openai", return_value={"Status": "ok"}):
            out = fk.flash_kv_summarize(_LONG, config=cfg)
        self.assertEqual(out, {"Status": "ok"})

    def test_exception_path_returns_empty(self) -> None:
        cfg = fk.FlashSummarizerConfig(provider="openai")
        with patch.object(fk, "_call_openai", side_effect=urllib.error.URLError("boom")):
            self.assertEqual(fk.flash_kv_summarize(_LONG, config=cfg), {})


class HybridAndFactoryTests(unittest.TestCase):
    def test_hybrid_uses_flash_when_available(self) -> None:
        with patch.object(fk, "flash_kv_summarize", return_value={"K": "v"}):
            self.assertEqual(fk.hybrid_kv_summarizer(_LONG), {"K": "v"})

    def test_hybrid_falls_back_to_local(self) -> None:
        with patch.object(fk, "flash_kv_summarize", return_value={}):
            with patch.object(fk, "local_kv_summarizer", return_value={"Local": "1"}):
                self.assertEqual(fk.hybrid_kv_summarizer(_LONG), {"Local": "1"})

    def test_create_summarizer_heuristic(self) -> None:
        fn = fk.create_summarizer("heuristic")
        self.assertIs(fn, fk.local_kv_summarizer)

    def test_create_summarizer_flash_falls_back(self) -> None:
        fn = fk.create_summarizer("flash")
        with patch.object(fk, "flash_kv_summarize", return_value={}):
            with patch.object(fk, "local_kv_summarizer", return_value={"L": "1"}):
                self.assertEqual(fn(_LONG, 12), {"L": "1"})

    def test_create_summarizer_auto(self) -> None:
        fn = fk.create_summarizer("auto")
        with patch.object(fk, "flash_kv_summarize", return_value={"A": "1"}):
            self.assertEqual(fn(_LONG, 12), {"A": "1"})


if __name__ == "__main__":
    unittest.main()
