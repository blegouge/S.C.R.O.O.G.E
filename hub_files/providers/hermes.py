#!/usr/bin/env python3
"""Hermes provider implementation."""

from __future__ import annotations

from pathlib import Path

from .cursor import CursorProvider


class HermesProvider(CursorProvider):
    """Provider for Hermes.

    Hermes uses the same hook format as Cursor.
    """

    @property
    def name(self) -> str:
        return "hermes"

    @property
    def label(self) -> str:
        return "Hermes"

    @property
    def env_event_var(self) -> str:
        return "HERMES_TT_EVENT"

    @property
    def env_home_var(self) -> str:
        return "HERMES_HOME"

    @property
    def default_home(self) -> Path:
        return Path.home() / ".hermes"

    @property
    def settings_file(self) -> Path:
        return self.home_dir / "hooks.json"

    @property
    def supports_rules(self) -> bool:
        return False  # Hermes doesn't support .mdc rules
