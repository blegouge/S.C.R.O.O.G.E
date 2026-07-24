#!/usr/bin/env python3
"""Tests for compression_pipeline module."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Configure paths
PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "src"))

from compaction.compression_pipeline import (
    build_structured_prompt,
    compress_dynamic_block,
    compress_with_claw,
    compress_with_headroom,
    compress_with_llmlingua,
    compression_backend,
    content_tags,
    is_code_like,
    is_log_like,
    is_subagent_output_like,
    parse_role_and_content,
    reassemble_light_prompt,
    safe_float,
    safe_int,
    segment_prompt,
)


class CompressionPipelineTests(unittest.TestCase):
    def test_is_code_like(self) -> None:
        self.assertTrue(is_code_like("def my_func():\n  pass"))
        self.assertTrue(is_code_like("class Foo:"))
        self.assertTrue(is_code_like("```python\nprint(1)\n```"))
        self.assertFalse(is_code_like("Just normal text with no code."))

    def test_is_log_like(self) -> None:
        self.assertTrue(is_log_like("2026-07-24 14:00:00 INFO: App started"))
        self.assertTrue(is_log_like("Traceback (most recent call last):\nValueError"))
        self.assertFalse(is_log_like("Some generic user input."))

    def test_is_subagent_output_like(self) -> None:
        self.assertTrue(is_subagent_output_like("subagent findings and deliverables"))
        self.assertFalse(is_subagent_output_like("plain text"))

    def test_content_tags(self) -> None:
        tags1 = content_tags("def test():\n  print('ERROR: log info')")
        self.assertIn("code", tags1)
        self.assertIn("logs", tags1)

        tags2 = content_tags("subagent deliverables")
        self.assertIn("subagent", tags2)

    def test_safe_conversions(self) -> None:
        self.assertEqual(safe_float("1.5", 0.0), 1.5)
        self.assertEqual(safe_float("invalid", 4.2), 4.2)
        self.assertEqual(safe_int("12", 0), 12)
        self.assertEqual(safe_int("abc", 5), 5)

    def test_compression_backend(self) -> None:
        self.assertIn(compression_backend(), {"claw", "llmlingua", "both", "auto", "headroom"})

    def test_parse_role_and_content(self) -> None:
        parsed1 = parse_role_and_content("USER: hello world")
        self.assertEqual(parsed1, {"role": "user", "content": "hello world"})

        parsed2 = parse_role_and_content("some random segment")
        self.assertEqual(parsed2, {"role": "user", "content": "some random segment"})

    def test_segment_prompt(self) -> None:
        history, latest = segment_prompt("USER: hello\n\nASSISTANT: hi\n\nUSER: how are you?")
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0], {"role": "user", "content": "hello"})
        self.assertEqual(history[1], {"role": "assistant", "content": "hi"})
        self.assertEqual(latest, "USER: how are you?")

    def test_reassemble_light_prompt(self) -> None:
        history = [
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "hi"},
        ]
        res = reassemble_light_prompt(history, "USER: how are you?")
        self.assertEqual(res, "USER: hello\n\nASSISTANT: hi\n\nUSER: how are you?")

    @patch("claw_compactor_adapter.compress_prompt_text")
    def test_compress_with_claw(self, mock_compress) -> None:
        mock_compress.return_value = (
            "compacted",
            {"applied": True, "reduction_pct": 50, "content_type": "code"},
        )
        res, applied = compress_with_claw("input", {"code"})
        self.assertEqual(res, "compacted")
        self.assertTrue(applied)

    @patch("token_compactor.compress_prompt_context")
    def test_compress_with_llmlingua(self, mock_compress) -> None:
        mock_compress.return_value = ("compacted_llm", True)
        res, applied = compress_with_llmlingua("input", 0.6)
        self.assertEqual(res, "compacted_llm")
        self.assertTrue(applied)

    @patch("headroom_adapter.compress_prompt_text")
    def test_compress_with_headroom(self, mock_compress) -> None:
        mock_compress.return_value = (
            "compacted_hr",
            {"applied": True, "reduction_pct": 30, "compressor": "smart"},
        )
        res, applied = compress_with_headroom("input", {"code"})
        self.assertEqual(res, "compacted_hr")
        self.assertTrue(applied)

    @patch("compaction.compression_pipeline.compression_backend", return_value="claw")
    @patch("compaction.compression_pipeline.compress_with_claw")
    def test_compress_dynamic_block_claw(self, mock_claw, mock_backend) -> None:
        mock_claw.return_value = ("claw_out", True)
        out, used_claw, used_llm, backend = compress_dynamic_block("input", 0.6, {"code"})
        self.assertEqual(out, "claw_out")
        self.assertTrue(used_claw)
        self.assertFalse(used_llm)
        self.assertEqual(backend, "claw")

    @patch("compaction.compression_pipeline.compression_backend", return_value="llmlingua")
    @patch("compaction.compression_pipeline.compress_with_llmlingua")
    def test_compress_dynamic_block_llmlingua(self, mock_llm, mock_backend) -> None:
        mock_llm.return_value = ("llm_out", True)
        out, used_claw, used_llm, backend = compress_dynamic_block("input", 0.6, {"code"})
        self.assertEqual(out, "llm_out")
        self.assertFalse(used_claw)
        self.assertTrue(used_llm)
        self.assertEqual(backend, "llmlingua")

    @patch("compaction.compression_pipeline.compression_backend", return_value="headroom")
    @patch("compaction.compression_pipeline.compress_with_headroom")
    def test_compress_dynamic_block_headroom(self, mock_hr, mock_backend) -> None:
        mock_hr.return_value = ("hr_out", True)
        out, used_claw, used_llm, backend = compress_dynamic_block("input", 0.6, {"code"})
        self.assertEqual(out, "hr_out")
        self.assertTrue(used_claw)
        self.assertFalse(used_llm)
        self.assertEqual(backend, "headroom")

    @patch(
        "compaction.compression_pipeline.build_upstream_guardrail_report", return_value="guardrail"
    )
    def test_build_structured_prompt(self, mock_guardrail) -> None:
        mock_manager = MagicMock()
        mock_manager.compact_history.return_value = (
            [{"role": "user", "content": "compacted"}],
            {"k": "v"},
            {"stats": 1},
        )
        mock_manager.build_cache_friendly_messages.return_value = [
            {"role": "system", "content": "static"},
            {"role": "system", "content": "state"},
            {"role": "user", "content": "history"},
            {"role": "user", "content": "latest"},
        ]

        prompt, stats = build_structured_prompt(
            mock_manager,
            [{"role": "user", "content": "hello"}],
            "USER: latest",
            {"global_state": {}, "subagent_type": "test"},
        )
        self.assertIn("[BLOCK_1_STATIC]", prompt)
        self.assertIn("static", prompt)
        self.assertIn("[BLOCK_2_SEMI_STATIC]", prompt)
        self.assertIn("state", prompt)
        self.assertIn("[BLOCK_3_DYNAMIC_HISTORY]", prompt)
        self.assertIn("history", prompt)
        self.assertEqual(stats, {"stats": 1})


if __name__ == "__main__":
    unittest.main()
