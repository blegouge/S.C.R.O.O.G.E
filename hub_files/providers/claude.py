#!/usr/bin/env python3
"""Claude Code provider implementation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .base import BaseProvider

# Event name mapping: Cursor (camelCase) → Claude Code (PascalCase)
_EVENT_MAPPING = {
    "preToolUse": "PreToolUse",
    "postToolUse": "PostToolUse",
    "stop": "Stop",
    "subagentStart": "SubagentStart",
    "subagentStop": "SubagentStop",
    "sessionStart": "SessionStart",
}

# Reverse mapping for transforms
_EVENT_MAPPING_REVERSE = {v: k for k, v in _EVENT_MAPPING.items()}

# Tool name mapping: Cursor → Claude Code
_TOOL_MAPPING = {
    "Shell": "Bash",
    "shell": "Bash",
}

# Events supported by Claude Code
_SUPPORTED_EVENTS = {
    "PreToolUse",
    "PostToolUse",
    "Stop",
    "SubagentStart",
    "SubagentStop",
    "SessionStart",
}


class ClaudeProvider(BaseProvider):
    """Provider for Claude Code (Anthropic CLI).

    Key differences from Cursor:
    - Hook responses use `hookSpecificOutput` wrapper
    - Settings in settings.json (not hooks.json)
    - Event names are PascalCase
    - Tool names differ (Shell → Bash)
    - No .mdc rules support
    """

    @property
    def name(self) -> str:
        return "claude"

    @property
    def label(self) -> str:
        return "Claude Code"

    @property
    def env_event_var(self) -> str:
        return "CLAUDE_TT_EVENT"

    @property
    def env_home_var(self) -> str:
        return "CLAUDE_HOME"

    @property
    def default_home(self) -> Path:
        return Path.home() / ".claude"

    @property
    def settings_file(self) -> Path:
        return self.home_dir / "settings.json"

    @property
    def supports_rules(self) -> bool:
        return False  # Claude Code doesn't support .mdc rules

    def format_hook_response(
        self,
        permission: str,
        *,
        reason: str = "",
        updated_input: dict[str, Any] | None = None,
        user_message: str = "",
    ) -> str:
        """Format hook response in Claude Code format.

        Claude Code format:
        {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "allow" | "deny",
                "permissionDecisionReason": "...",
                "updatedInput": {...}
            }
        }
        """
        hook_output: dict[str, Any] = {
            "hookEventName": "PreToolUse",
            "permissionDecision": permission,
        }

        if permission == "deny" and reason:
            hook_output["permissionDecisionReason"] = reason
        elif permission == "allow" and updated_input is not None:
            hook_output["updatedInput"] = updated_input

        response = {"hookSpecificOutput": hook_output}
        return json.dumps(response, ensure_ascii=False)

    def transform_hooks_config(self, cursor_format: dict[str, Any]) -> dict[str, Any]:
        """Transform hooks from Cursor format to Claude Code format.

        Cursor format:
        {
            "preToolUse": [
                {"matcher": "Shell", "command": "/path/to/hook.sh"}
            ]
        }

        Claude Code format:
        {
            "PreToolUse": [
                {
                    "matcher": "Bash",
                    "hooks": [
                        {"type": "command", "command": "/path/to/hook.sh"}
                    ]
                }
            ]
        }
        """
        result: dict[str, Any] = {}

        for event, hooks in cursor_format.items():
            # Map event name
            claude_event = _EVENT_MAPPING.get(event, event)

            # Skip unsupported events
            if claude_event not in _SUPPORTED_EVENTS:
                continue

            # Group hooks by matcher
            by_matcher: dict[str, list[dict[str, Any]]] = {}

            for hook in hooks:
                matcher = hook.get("matcher", "*")
                # Map tool names
                matcher = _TOOL_MAPPING.get(matcher, matcher)

                command = hook.get("command", "")
                if not command:
                    continue

                if matcher not in by_matcher:
                    by_matcher[matcher] = []

                by_matcher[matcher].append(
                    {
                        "type": "command",
                        "command": command,
                    }
                )

            # Build Claude format
            if by_matcher:
                result[claude_event] = [
                    {"matcher": matcher, "hooks": hooks_list}
                    for matcher, hooks_list in by_matcher.items()
                ]

        return result

    def merge_hooks_config(
        self,
        existing: dict[str, Any],
        new_hooks: dict[str, Any],
    ) -> dict[str, Any]:
        """Merge hooks in Claude Code format.

        Claude Code format groups hooks by matcher within each event.
        """
        merged = dict(existing)

        for event, matcher_groups in new_hooks.items():
            if event not in merged:
                merged[event] = []

            # Build lookup of existing matchers
            existing_matchers: dict[str, dict[str, Any]] = {}
            for group in merged[event]:
                matcher = group.get("matcher", "*")
                existing_matchers[matcher] = group

            for new_group in matcher_groups:
                matcher = new_group.get("matcher", "*")
                new_hooks_list = new_group.get("hooks", [])

                if matcher in existing_matchers:
                    # Merge into existing matcher group
                    existing_group = existing_matchers[matcher]
                    existing_commands = {h.get("command") for h in existing_group.get("hooks", [])}

                    for hook in new_hooks_list:
                        if hook.get("command") not in existing_commands:
                            existing_group.setdefault("hooks", []).append(hook)
                else:
                    # Add new matcher group
                    merged[event].append(new_group)
                    existing_matchers[matcher] = new_group

        return merged
