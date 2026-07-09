#!/usr/bin/env python3
"""Tests for summarizer factory."""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

local_src = Path(__file__).resolve().parents[2]
if str(local_src) not in sys.path:
    sys.path.insert(0, str(local_src))

from utils.summarizer_factory import resolve_summarizer, resolve_summarizer_mode


class SummarizerFactoryTests(unittest.TestCase):
    @patch.dict(os.environ, {"ADAPTIVE_CTX_SUMMARIZER": "flash"})
    def test_resolve_summarizer_mode_env(self) -> None:
        self.assertEqual(resolve_summarizer_mode(), "flash")

    @patch.dict(os.environ, {"ADAPTIVE_CTX_SUMMARIZER": ""})
    def test_resolve_summarizer_mode_default(self) -> None:
        self.assertEqual(resolve_summarizer_mode(), "auto")

    def test_resolve_summarizer_auto(self) -> None:
        fn = resolve_summarizer("auto")
        self.assertTrue(callable(fn))

    def test_resolve_summarizer_flash(self) -> None:
        fn = resolve_summarizer("flash")
        self.assertTrue(callable(fn))
