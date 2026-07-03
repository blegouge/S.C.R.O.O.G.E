#!/usr/bin/env python3
"""Cursor IDE provider implementation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .base import BaseProvider


class CursorProvider(BaseProvider):
    """Provider for Cursor IDE.

    Cursor is the reference implementation - other providers transform
    from/to Cursor's formats.
    """

    @property
    def name(self) -> str:
        return "cursor"

    @property
    def label(self) -> str:
        return "Cursor"

    @property
    def env_event_var(self) -> str:
        return "CURSOR_TT_EVENT"

    @property
    def env_home_var(self) -> str:
        return "CURSOR_HOME"

    @property
    def default_home(self) -> Path:
        return Path.home() / ".cursor"

    @property
    def settings_file(self) -> Path:
        return self.home_dir / "hooks.json"

    @property
    def supports_rules(self) -> bool:
        return True  # Cursor supports .mdc rules

    def format_hook_response(
        self,
        permission: str,
        *,
        reason: str = "",
        updated_input: dict[str, Any] | None = None,
        user_message: str = "",
    ) -> str:
        """Format hook response in Cursor format.

        Cursor format:
        {
            "permission": "allow" | "deny",
            "agent_message": "...",  # for deny
            "user_message": "...",   # for deny
            "updated_input": {...}   # for allow with modifications
        }
        """
        response: dict[str, Any] = {"permission": permission}

        if permission == "deny":
            if reason:
                response["agent_message"] = reason
            if user_message:
                response["user_message"] = user_message
        elif updated_input is not None:
            response["updated_input"] = updated_input

        return json.dumps(response, ensure_ascii=False)

    def transform_hooks_config(self, cursor_format: dict[str, Any]) -> dict[str, Any]:
        """No transformation needed - Cursor is the reference format."""
        return cursor_format

    def merge_hooks_config(
        self,
        existing: dict[str, Any],
        new_hooks: dict[str, Any],
    ) -> dict[str, Any]:
        """Merge hooks in Cursor format (list-based).

        Cursor hooks.json format:
        {
            "eventName": [
                {"matcher": "ToolName", "command": "/path/to/hook.sh"},
                ...
            ]
        }
        """
        merged = dict(existing)

        for event, hooks in new_hooks.items():
            if event not in merged:
                merged[event] = []

            existing_commands = {h.get("command") for h in merged[event]}

            for hook in hooks:
                if hook.get("command") not in existing_commands:
                    merged[event].append(hook)

        return merged
