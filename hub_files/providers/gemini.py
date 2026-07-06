#!/usr/bin/env python3
"""Gemini CLI provider implementation."""

from __future__ import annotations

from pathlib import Path

from .cursor import CursorProvider


class GeminiProvider(CursorProvider):
    """Provider for Gemini CLI.

    Gemini CLI uses the same hook format as Cursor.
    """

    @property
    def name(self) -> str:
        return "gemini"

    @property
    def label(self) -> str:
        return "Gemini CLI"

    @property
    def env_event_var(self) -> str:
        return "GEMINI_TT_EVENT"

    @property
    def env_home_var(self) -> str:
        return "GEMINI_HOME"

    @property
    def default_home(self) -> Path:
        return Path.home() / ".gemini"

    @property
    def settings_file(self) -> Path:
        return self.home_dir / "hooks.json"

    @property
    def supports_rules(self) -> bool:
        return False  # Gemini CLI doesn't support .mdc rules
