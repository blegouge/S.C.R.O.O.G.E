#!/usr/bin/env python3
"""Shared utilities for IDE agent hooks (preToolUse, postToolUse, etc.)."""

from __future__ import annotations

import functools
import json
import os
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any


def resolve_home_path() -> Path:
    """Resolve the global IDE hub directory.

    Resolves based on active environment variables (CODEX_HOME, ANTIGRAVITY_HOME, CURSOR_HOME)
    or falls back to the directory containing the running hook script.
    """
    home_dir = os.getenv("CODEX_HOME") or os.getenv("ANTIGRAVITY_HOME") or os.getenv("CURSOR_HOME")
    if home_dir:
        return Path(home_dir).resolve()

    # Fallback to grandparent of the hook script (hooks live under hub_files/hooks/ or ~/.cursor/hooks/)
    return Path(__file__).resolve().parent.parent.parent


def load_stdin_json() -> dict[str, Any]:
    """Read sys.stdin and parse it as a JSON object.

    Returns an empty dict if stdin is empty or malformed.
    """
    raw = sys.stdin.read()
    if not raw.strip():
        return {}
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else {"_raw": raw}
    except json.JSONDecodeError:
        return {"_raw": raw}


def extract_tool_name(data: dict[str, Any]) -> str:
    """Extract tool name from hook payload data."""
    for key in ("tool_name", "toolName", "name"):
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()

    tool = data.get("tool")
    if isinstance(tool, dict):
        nested = tool.get("name") or tool.get("tool")
        if isinstance(nested, str) and nested.strip():
            return nested.strip()
    if isinstance(tool, str) and tool.strip():
        return tool.strip()

    tool_calls = data.get("tool_calls")
    if isinstance(tool_calls, list) and tool_calls:
        first = tool_calls[0]
        if isinstance(first, dict):
            fn = first.get("function") or {}
            if isinstance(fn, dict) and isinstance(fn.get("name"), str):
                return fn["name"].strip()
    return ""


def extract_tool_input(data: dict[str, Any]) -> dict[str, Any]:
    """Extract tool input dictionary from hook payload data."""
    for key in ("tool_input", "input"):
        value = data.get(key)
        if isinstance(value, dict):
            return value
    tool = data.get("tool")
    if isinstance(tool, dict):
        nested = tool.get("input") or tool.get("tool_input")
        if isinstance(nested, dict):
            return nested
    return {}


def fail_safe(fallback_value: Any = None) -> Callable:
    """Decorator to catch exceptions, print to stderr, and return a fallback value."""

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return func(*args, **kwargs)
            except Exception as exc:
                sys.stderr.write(f"[hook-failsafe] Error in {func.__name__}: {exc}\n")
                return fallback_value

        return wrapper

    return decorator


def hook_fail_safe(fallback_json: str = '{"permission": "allow"}') -> Callable:
    """Decorator for hook main() functions.

    Outputs fallback_json to stdout and exits 0 on crash.
    """

    def decorator(func: Callable[[], int]) -> Callable[[], int]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> int:
            try:
                return func(*args, **kwargs)
            except Exception as exc:
                sys.stderr.write(f"[hook-failsafe] Critical error in {func.__name__}: {exc}\n")
                sys.stdout.write(fallback_json)
                sys.stdout.flush()
                return 0

        return wrapper

    return decorator
