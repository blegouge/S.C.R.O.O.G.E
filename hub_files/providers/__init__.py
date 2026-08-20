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
    "claude": ClaudeProvider,
    "gemini": GeminiProvider,
    "antigravity": AntigravityProvider,
    "hermes": HermesProvider,
    "codex": CodexProvider,
    "cursor": CursorProvider,
}


# Deployment roots, longest first: ~/.gemini/antigravity is nested in ~/.gemini.
_HOME_HINTS: tuple[tuple[str, str, str], ...] = (
    ("CLAUDE_HOME", ".claude", "claude"),
    ("ANTIGRAVITY_HOME", ".gemini/antigravity", "antigravity"),
    ("GEMINI_HOME", ".gemini", "gemini"),
    ("HERMES_HOME", ".hermes", "hermes"),
    ("CODEX_HOME", ".codex", "codex"),
    ("CURSOR_HOME", ".cursor", "cursor"),
)

_EVENT_HINTS: tuple[tuple[str, str], ...] = (
    ("CLAUDE_TT_EVENT", "claude"),
    ("GEMINI_TT_EVENT", "gemini"),
    ("ANTIGRAVITY_TT_EVENT", "antigravity"),
    ("HERMES_TT_EVENT", "hermes"),
    ("CODEX_TT_EVENT", "codex"),
    ("CURSOR_TT_EVENT", "cursor"),
)


def _path_is_relative_to(path: Path, root: Path) -> bool:
    try:
        if hasattr(path, "is_relative_to"):
            if path.resolve().is_relative_to(root.resolve()):
                return True
    except (ValueError, OSError):
        pass
    try:
        p_str = os.path.normcase(os.path.abspath(str(path)))
        r_str = os.path.normcase(os.path.abspath(str(root)))
        if p_str == r_str:
            return True
        return p_str.startswith(r_str.rstrip("\\/") + os.sep)
    except Exception:
        return False


def source_from_install_path(path: Path) -> str | None:
    """Map an install path to a provider, or None when it sits outside every root."""
    for env_name, rel_home, source in _HOME_HINTS:
        roots = []
        configured = os.environ.get(env_name, "").strip()
        if configured:
            roots.append(Path(configured).expanduser())
        try:
            roots.append(Path.home() / rel_home)
        except (RuntimeError, OSError):
            pass
        for root in roots:
            if _path_is_relative_to(path, root):
                return source
    return None


def source_from_event_vars() -> str | None:
    """Read *_TT_EVENT, but only when a single agent claims the event.

    Hook wrappers broadcast every *_TT_EVENT variable so one script can be
    deployed to all agents. Those variables carry the event name, not the
    identity of the caller, so an ambiguous set must never pick a winner.
    """
    claimed = {source for env_name, source in _EVENT_HINTS if os.environ.get(env_name, "").strip()}
    if len(claimed) == 1:
        return claimed.pop()
    return None


def detect_provider() -> BaseProvider:
    """Detect the active provider from the execution context.

    Detection order (first match wins):
    1. SCROOGE_TELEMETRY_SOURCE override
    2. Install path of this module — every agent has its own deployment root
    3. *_TT_EVENT, only when a single agent claims the event
    4. Default fallback → Claude Code
    """
    explicit = os.environ.get("SCROOGE_TELEMETRY_SOURCE", "").strip().lower()
    if explicit in _PROVIDERS:
        return _PROVIDERS[explicit]()

    source = None
    try:
        source = source_from_install_path(Path(__file__).resolve().parent)
    except OSError:
        pass
    if source is None:
        source = source_from_event_vars()

    return _PROVIDERS.get(source or "claude", ClaudeProvider)()


def get_provider(name: str) -> BaseProvider:
    """Get a provider instance by name.

    Args:
        name: Provider identifier (claude, gemini, antigravity, hermes, codex, cursor)

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
