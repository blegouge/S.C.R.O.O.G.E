#!/usr/bin/env python3
"""Resolve Token Telemetry application vs persistent data directories."""

from __future__ import annotations

import os
from pathlib import Path


def load_telemetry_env() -> None:
    """Load configuration from .env file if present in the app directory or parents."""
    # 1. Check override
    app_override = os.environ.get("CURSOR_TOKEN_TELEMETRY_APP", "").strip()
    search_paths = []
    if app_override:
        search_paths.append(Path(app_override).expanduser())
    
    # 2. Add current file's directory and parents
    this_dir = Path(__file__).resolve().parent
    search_paths.append(this_dir)
    search_paths.append(this_dir.parent)
    search_paths.append(Path.cwd())
    
    # 3. Add default home paths
    search_paths.append(Path.home() / ".cursor")
    search_paths.append(Path.home() / ".gemini" / "antigravity")

    for path in search_paths:
        env_file = path / ".env"
        if env_file.is_file():
            try:
                with env_file.open("r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith("#"):
                            continue
                        if "=" in line:
                            k, v = line.split("=", 1)
                            k = k.strip()
                            v = v.strip().strip('"').strip("'")
                            if k and k not in os.environ:
                                os.environ[k] = v
                break  # Stop after loading the first valid .env
            except Exception:
                pass


# Load env configurations immediately on import
load_telemetry_env()

DEFAULT_DATA_DIR = Path.home() / ".cursor" / "token-telemetry"
DEFAULT_APP_DIR = Path.home() / "www" / "private" / "TelemetryToken"


def resolve_data_dir(source: str | None = None) -> Path:
    """Persistent telemetry storage (events.jsonl, layout, diff-only cache)."""
    # 1. Direct environment variable override
    override = os.environ.get("CURSOR_TOKEN_TELEMETRY_DATA_DIR", "").strip()
    if override:
        return Path(override).expanduser()

    # 2. Check source specific stats directories from env
    if source == "cursor" or source is None:
        c_stats = os.environ.get("CURSOR_STATS_DIR", "").strip()
        if c_stats:
            return Path(c_stats).expanduser()
        c_home = os.environ.get("CURSOR_HOME", "").strip()
        if c_home:
            return Path(c_home).expanduser() / "token-telemetry"
        return DEFAULT_DATA_DIR

    if source == "gemini" or source == "antigravity":
        g_stats = os.environ.get("GEMINI_STATS_DIR", "").strip() or os.environ.get("ANTIGRAVITY_STATS_DIR", "").strip()
        if g_stats:
            return Path(g_stats).expanduser()
        g_home = os.environ.get("ANTIGRAVITY_HOME", "").strip() or os.environ.get("GEMINI_HOME", "").strip()
        if g_home:
            return Path(g_home).expanduser() / "token-telemetry"
        return Path.home() / ".gemini" / "antigravity" / "token-telemetry"

    if source == "hermes":
        h_stats = os.environ.get("HERMES_STATS_DIR", "").strip()
        if h_stats:
            return Path(h_stats).expanduser()
        h_home = os.environ.get("HERMES_HOME", "").strip()
        if h_home:
            return Path(h_home).expanduser() / "token-telemetry"
        return Path.home() / ".hermes" / "token-telemetry"

    if source == "claude":
        cl_stats = os.environ.get("CLAUDE_STATS_DIR", "").strip()
        if cl_stats:
            return Path(cl_stats).expanduser()
        cl_home = os.environ.get("CLAUDE_HOME", "").strip()
        if cl_home:
            return Path(cl_home).expanduser() / "token-telemetry"
        return Path.home() / ".claude" / "token-telemetry"

    # Default fallback
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

