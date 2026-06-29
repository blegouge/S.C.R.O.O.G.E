#!/usr/bin/env python3
"""Resolve Token Telemetry application vs persistent data directories."""

from __future__ import annotations

import os
from pathlib import Path

DEFAULT_DATA_DIR = Path.home() / ".cursor" / "token-telemetry"
GEMINI_DATA_DIR = Path.home() / ".gemini" / "token-telemetry"
HERMES_DATA_DIR = Path.home() / ".hermes" / "token-telemetry"
DEFAULT_APP_DIR = Path.home() / "www" / "private" / "TelemetryToken"


def resolve_data_dir(source: str | None = None) -> Path:
    """Persistent telemetry storage (events.jsonl, layout, diff-only cache)."""
    override = os.environ.get("CURSOR_TOKEN_TELEMETRY_DATA_DIR", "").strip()
    if override:
        return Path(override).expanduser()
    if source == "hermes":
        return HERMES_DATA_DIR
    if source == "gemini":
        return GEMINI_DATA_DIR
    return DEFAULT_DATA_DIR


def resolve_log_file(source: str | None = None) -> Path:
    return resolve_data_dir(source=source) / "events.jsonl"


def resolve_app_dir() -> Path:
    """Application code, venv, dashboard assets, build scripts."""
    override = os.environ.get("CURSOR_TOKEN_TELEMETRY_APP", "").strip()
    if override:
        return Path(override).expanduser()
    return DEFAULT_APP_DIR


def resolve_venv_python() -> Path:
    return resolve_app_dir() / ".venv-desktop" / "bin" / "python"


def resolve_venv_claw_compactor() -> Path:
    return resolve_app_dir() / ".venv-desktop" / "bin" / "claw-compactor"
