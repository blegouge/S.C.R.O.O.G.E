#!/usr/bin/env python3
"""Codex provider implementation."""

from __future__ import annotations

from pathlib import Path

from .cursor import CursorProvider


class CodexProvider(CursorProvider):
    """Provider for Codex.

    Codex uses the same hook format as Cursor, just with different paths.
    """

    @property
    def name(self) -> str:
        return "codex"

    @property
    def label(self) -> str:
        return "Codex"

    @property
    def env_event_var(self) -> str:
        return "CODEX_TT_EVENT"

    @property
    def env_home_var(self) -> str:
        return "CODEX_HOME"

    @property
    def default_home(self) -> Path:
        return Path.home() / ".codex"

    @property
    def settings_file(self) -> Path:
        return self.home_dir / "hooks.json"

    @property
    def supports_rules(self) -> bool:
        return True  # Codex supports .mdc rules like Cursor
