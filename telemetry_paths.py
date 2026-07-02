#!/usr/bin/env python3
"""Resolve S.C.R.O.O.G.E. application vs persistent data directories."""

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
    
    # 2. Add current file's directory and all its parents
    this_dir = Path(__file__).resolve().parent
    search_paths.append(this_dir)
    search_paths.extend(this_dir.parents)
    search_paths.append(Path.cwd())
    search_paths.extend(Path.cwd().parents)
    
    # 3. If frozen, also add executable's directory and all its parents
    import sys
    if getattr(sys, "frozen", False):
        exec_dir = Path(sys.executable).resolve().parent
        search_paths.append(exec_dir)
        search_paths.extend(exec_dir.parents)
    
    # 4. Add default app directory and default home paths
    search_paths.append(Path.home() / "www" / "private" / "SCROOGE")
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

from providers_config import get_data_dir
DEFAULT_APP_DIR = Path.home() / "www" / "private" / "SCROOGE"


def resolve_data_dir(source: str | None = None) -> Path:
    """Persistent telemetry storage (events.jsonl, layout, diff-only cache)."""
    # 1. Direct environment variable override
    override = os.environ.get("CURSOR_TOKEN_TELEMETRY_DATA_DIR", "").strip()
    if override:
        return Path(override).expanduser()
    data_dir = get_data_dir(source or "cursor")
    if data_dir is None:
        # Fallback to cursor default if provider not found
        return Path.home() / ".cursor" / "token-telemetry"
    return data_dir


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

