#!/usr/bin/env python3
"""Antigravity provider implementation."""

from __future__ import annotations

from pathlib import Path

from .cursor import CursorProvider


class AntigravityProvider(CursorProvider):
    """Provider for Antigravity (Gemini-based IDE).

    Antigravity uses the same hook format as Cursor, just with different paths.
    """

    @property
    def name(self) -> str:
        return "antigravity"

    @property
    def label(self) -> str:
        return "Antigravity"

    @property
    def env_event_var(self) -> str:
        return "ANTIGRAVITY_TT_EVENT"

    @property
    def env_home_var(self) -> str:
        return "ANTIGRAVITY_HOME"

    @property
    def default_home(self) -> Path:
        return Path.home() / ".gemini" / "antigravity"

    @property
    def settings_file(self) -> Path:
        return self.home_dir / "hooks.json"

    @property
    def supports_rules(self) -> bool:
        return True  # Antigravity supports .mdc rules like Cursor
