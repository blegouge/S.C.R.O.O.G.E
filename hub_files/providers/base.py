#!/usr/bin/env python3
"""Base provider interface for multi-IDE support."""

from __future__ import annotations

import json
import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any


class BaseProvider(ABC):
    """Abstract base class for IDE providers.

    Each provider implements IDE-specific behavior for:
    - File paths (home, hooks, data, settings)
    - Hook response formats
    - Settings/configuration formats
    - Feature support flags
    """

    # === Identity ===

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider identifier (lowercase, no spaces)."""

    @property
    @abstractmethod
    def label(self) -> str:
        """Human-readable provider name."""

    @property
    @abstractmethod
    def env_event_var(self) -> str:
        """Environment variable for telemetry event type (e.g., CLAUDE_TT_EVENT)."""

    @property
    @abstractmethod
    def env_home_var(self) -> str:
        """Environment variable for home directory override (e.g., CLAUDE_HOME)."""

    @property
    def env_enabled_var(self) -> str:
        """Environment variable to enable telemetry for this provider."""
        return f"TELEMETRY_{self.name.upper()}_ENABLED"

    # === Paths ===

    @property
    @abstractmethod
    def default_home(self) -> Path:
        """Default home directory path (e.g., ~/.claude)."""

    @property
    def home_dir(self) -> Path:
        """Resolved home directory (checks env var first)."""
        override = os.environ.get(self.env_home_var, "").strip()
        if override:
            return Path(override).expanduser()
        return self.default_home

    @property
    def hooks_dir(self) -> Path:
        """Directory containing hook scripts."""
        return self.home_dir / "hooks"

    @property
    def data_dir(self) -> Path:
        """Directory for telemetry data (events.jsonl, etc.)."""
        return self.home_dir / "token-telemetry"

    @property
    def events_file(self) -> Path:
        """Path to events.jsonl log file."""
        return self.data_dir / "events.jsonl"

    @property
    @abstractmethod
    def settings_file(self) -> Path:
        """Path to hooks configuration file."""

    # === Feature Support ===

    @property
    def supports_rules(self) -> bool:
        """Whether this IDE supports .mdc rules with alwaysApply."""
        return False

    @property
    def supports_skills(self) -> bool:
        """Whether this IDE supports skills (SKILL.md)."""
        return True

    @property
    def supports_hooks(self) -> bool:
        """Whether this IDE supports hooks."""
        return True

    @property
    def supports_mcp(self) -> bool:
        """Whether this IDE supports MCP servers."""
        return True

    # === State ===

    @property
    def is_enabled(self) -> bool:
        """Check if telemetry is enabled for this provider."""
        value = os.environ.get(self.env_enabled_var, "").strip().lower()
        return value in ("1", "true", "yes", "on")

    @property
    def is_active(self) -> bool:
        """Check if this provider is currently active (detected from env)."""
        return bool(
            os.environ.get(self.env_event_var)
            or os.environ.get(self.env_home_var)
        )

    # === Hook Response Formatting ===

    @abstractmethod
    def format_hook_response(
        self,
        permission: str,
        *,
        reason: str = "",
        updated_input: dict[str, Any] | None = None,
        user_message: str = "",
    ) -> str:
        """Format a PreToolUse hook response for this IDE.

        Args:
            permission: "allow" or "deny"
            reason: Explanation for deny (shown to agent)
            updated_input: Modified tool input (for allow with changes)
            user_message: Message shown to user (for deny)

        Returns:
            JSON string in the IDE's expected format
        """

    def format_allow(self, updated_input: dict[str, Any] | None = None) -> str:
        """Shorthand for allow response."""
        return self.format_hook_response("allow", updated_input=updated_input)

    def format_deny(self, reason: str, user_message: str = "") -> str:
        """Shorthand for deny response."""
        return self.format_hook_response("deny", reason=reason, user_message=user_message)

    # === Settings Format ===

    @abstractmethod
    def transform_hooks_config(self, cursor_format: dict[str, Any]) -> dict[str, Any]:
        """Transform hooks config from Cursor format to this IDE's format.

        Args:
            cursor_format: Hooks configuration in Cursor/hooks.json format

        Returns:
            Configuration in this IDE's expected format
        """

    @abstractmethod
    def merge_hooks_config(
        self,
        existing: dict[str, Any],
        new_hooks: dict[str, Any],
    ) -> dict[str, Any]:
        """Merge new hooks into existing configuration without duplicates.

        Args:
            existing: Current hooks configuration
            new_hooks: New hooks to add

        Returns:
            Merged configuration
        """

    # === Installation ===

    def install_hooks(self, hooks_config: dict[str, Any]) -> None:
        """Install hooks configuration to the settings file.

        Args:
            hooks_config: Hooks configuration in Cursor format (will be transformed)
        """
        # Transform to this IDE's format
        transformed = self.transform_hooks_config(hooks_config)

        # Load existing settings
        existing: dict[str, Any] = {}
        if self.settings_file.is_file():
            try:
                existing = json.loads(self.settings_file.read_text())
            except json.JSONDecodeError:
                pass

        # Merge hooks
        existing_hooks = existing.get("hooks", {})
        merged_hooks = self.merge_hooks_config(existing_hooks, transformed)
        existing["hooks"] = merged_hooks

        # Write back
        self.settings_file.parent.mkdir(parents=True, exist_ok=True)
        self.settings_file.write_text(json.dumps(existing, indent=2) + "\n")

    def ensure_directories(self) -> None:
        """Create required directories if they don't exist."""
        self.hooks_dir.mkdir(parents=True, exist_ok=True)
        self.data_dir.mkdir(parents=True, exist_ok=True)

    # === Utilities ===

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name!r}, home={self.home_dir})"
