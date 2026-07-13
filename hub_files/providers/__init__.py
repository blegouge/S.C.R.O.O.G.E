#!/usr/bin/env python3
"""Provider abstraction for multi-IDE support.

This module provides a unified interface for different IDEs (Cursor, Claude Code,
Antigravity, Gemini CLI, Hermes). Each provider handles IDE-specific details like:
- Hook response formats
- Configuration file paths and formats
- Feature support (rules, skills, hooks)
- Telemetry routing

Usage:
    from providers import detect_provider, get_provider

    # Auto-detect from environment
    provider = detect_provider()
    response = provider.format_hook_response({"permission": "allow"})

    # Get specific provider
    cursor = get_provider("cursor")
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .base import BaseProvider

from .antigravity import AntigravityProvider
from .claude import ClaudeProvider
from .codex import CodexProvider
from .cursor import CursorProvider
from .gemini import GeminiProvider
from .hermes import HermesProvider

_PROVIDERS: dict[str, type[BaseProvider]] = {
    "cursor": CursorProvider,
    "claude": ClaudeProvider,
    "codex": CodexProvider,
    "antigravity": AntigravityProvider,
    "gemini": GeminiProvider,
    "hermes": HermesProvider,
}


def detect_provider() -> BaseProvider:
    """Detect the active provider from environment variables and path context.

    Detection order (first match wins):
    1. SCROOGE_TELEMETRY_SOURCE override
    2. Dynamic event variables (*_TT_EVENT)
    3. Path-relative home directories matching the execution context
    4. Default fallback → Cursor
    """
    # 1. Explicit override
    explicit = os.environ.get("SCROOGE_TELEMETRY_SOURCE", "").strip().lower()
    if explicit in _PROVIDERS:
        return _PROVIDERS[explicit]()

    # 2. Dynamic event variables
    if os.environ.get("CLAUDE_TT_EVENT"):
        return ClaudeProvider()
    if os.environ.get("CODEX_TT_EVENT"):
        return CodexProvider()
    if os.environ.get("ANTIGRAVITY_TT_EVENT"):
        return AntigravityProvider()
    if os.environ.get("GEMINI_TT_EVENT"):
        return GeminiProvider()
    if os.environ.get("HERMES_TT_EVENT"):
        return HermesProvider()
    if os.environ.get("CURSOR_TT_EVENT"):
        return CursorProvider()

    # 3. Path-relative checks (detect which home folder the executing code lives in)
    try:
        this_file_dir = Path(__file__).resolve().parent
        home_hints = (
            ("CODEX_HOME", "codex"),
            ("ANTIGRAVITY_HOME", "antigravity"),
            ("CLAUDE_HOME", "claude"),
            ("GEMINI_HOME", "gemini"),
            ("HERMES_HOME", "hermes"),
            ("CURSOR_HOME", "cursor"),
        )
        for env_name, source in home_hints:
            val = os.environ.get(env_name, "").strip()
            if val:
                try:
                    resolved_home = Path(val).expanduser().resolve()
                    if this_file_dir.is_relative_to(resolved_home):
                        return _PROVIDERS[source]()
                except (ValueError, OSError):
                    pass
    except Exception:
        pass

    # Default to Cursor
    return CursorProvider()


def get_provider(name: str) -> BaseProvider:
    """Get a provider instance by name.

    Args:
        name: Provider identifier (cursor, claude, codex, antigravity, gemini, hermes)

    Returns:
        Provider instance

    Raises:
        KeyError: If provider name is unknown
    """
    if name not in _PROVIDERS:
        raise KeyError(f"Unknown provider: {name}. Available: {list(_PROVIDERS.keys())}")
    return _PROVIDERS[name]()


def get_all_providers() -> list[BaseProvider]:
    """Get instances of all available providers."""
    return [cls() for cls in _PROVIDERS.values()]


def get_enabled_providers() -> list[BaseProvider]:
    """Get providers that are enabled via environment variables."""
    enabled = []
    for cls in _PROVIDERS.values():
        provider = cls()
        if provider.is_enabled:
            enabled.append(provider)
    return enabled


__all__ = [
    "BaseProvider",
    "CursorProvider",
    "ClaudeProvider",
    "CodexProvider",
    "AntigravityProvider",
    "GeminiProvider",
    "HermesProvider",
    "detect_provider",
    "get_provider",
    "get_all_providers",
    "get_enabled_providers",
]
