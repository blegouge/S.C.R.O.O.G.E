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
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .base import BaseProvider

from .cursor import CursorProvider
from .claude import ClaudeProvider
from .codex import CodexProvider
from .antigravity import AntigravityProvider
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
    """Detect the active provider from environment variables.

    Detection order (first match wins):
    1. CLAUDE_TT_EVENT or CLAUDE_HOME → Claude Code
    2. CODEX_TT_EVENT or CODEX_HOME → Codex
    3. ANTIGRAVITY_TT_EVENT or ANTIGRAVITY_HOME → Antigravity
    4. GEMINI_TT_EVENT or GEMINI_HOME → Gemini CLI
    5. HERMES_TT_EVENT or HERMES_HOME → Hermes
    6. Default → Cursor
    """
    if os.environ.get("CLAUDE_TT_EVENT") or os.environ.get("CLAUDE_HOME"):
        return ClaudeProvider()
    if os.environ.get("CODEX_TT_EVENT") or os.environ.get("CODEX_HOME"):
        return CodexProvider()
    if os.environ.get("ANTIGRAVITY_TT_EVENT") or os.environ.get("ANTIGRAVITY_HOME"):
        return AntigravityProvider()
    if os.environ.get("GEMINI_TT_EVENT") or os.environ.get("GEMINI_HOME"):
        return GeminiProvider()
    if os.environ.get("HERMES_TT_EVENT") or os.environ.get("HERMES_HOME"):
        return HermesProvider()
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
    for name, cls in _PROVIDERS.items():
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
