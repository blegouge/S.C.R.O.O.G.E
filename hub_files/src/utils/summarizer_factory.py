#!/usr/bin/env python3
"""Factory helpers for adaptive context summarizers."""

from __future__ import annotations

import os

from utils.flash_kv_summarizer import SummarizerFn, create_summarizer


def resolve_summarizer_mode() -> str:
    """Read global summarizer mode from environment."""
    return os.getenv("ADAPTIVE_CTX_SUMMARIZER", "auto").strip().lower() or "auto"


def resolve_summarizer(mode: str | None = None) -> SummarizerFn:
    """Return summarizer callable for AdaptiveContextManager."""
    return create_summarizer(mode or resolve_summarizer_mode())
