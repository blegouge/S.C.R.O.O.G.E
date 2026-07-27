#!/usr/bin/env python3
"""Load and access provider configuration from providers_config.yaml."""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore[assignment]


@dataclass
class ProviderConfig:
    """Configuration for a telemetry provider."""

    name: str
    env_enabled: str
    data_dir: str
    rtk_cwd: str | None
    env_home: str | None
    label: str
    env_stats: str | None = None


_config_cache: dict[str, ProviderConfig] | None = None


def _config_path() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS) / "providers_config.yaml"  # type: ignore[attr-defined]
    return Path(__file__).parent / "providers_config.yaml"


def _parse_simple_yaml(text: str) -> dict[str, Any]:
    """Fallback YAML parser for simple key-value/nested dict structure when PyYAML is missing."""
    result: dict[str, Any] = {}
    stack: list[tuple[int, dict[str, Any]]] = [(-1, result)]

    for raw_line in text.splitlines():
        line = raw_line
        if "#" in line:
            line = line.split("#", 1)[0]
        line_stripped = line.rstrip()
        if not line_stripped or line_stripped.isspace():
            continue

        indent = len(line) - len(line.lstrip())
        content = line.strip()
        if not content or ":" not in content:
            continue

        key, _, val = content.partition(":")
        key = key.strip()
        val = val.strip()

        while stack and stack[-1][0] >= indent:
            stack.pop()

        parent = stack[-1][1]

        if not val:
            new_dict: dict[str, Any] = {}
            parent[key] = new_dict
            stack.append((indent, new_dict))
        else:
            if val in ("null", "None", "~"):
                parsed_val: Any = None
            elif val.lower() == "true":
                parsed_val = True
            elif val.lower() == "false":
                parsed_val = False
            elif (val.startswith('"') and val.endswith('"')) or (
                val.startswith("'") and val.endswith("'")
            ):
                parsed_val = val[1:-1]
            else:
                parsed_val = val
            parent[key] = parsed_val

    return result


def _ensure_env_loaded() -> None:
    try:
        from telemetry_paths import load_telemetry_env

        load_telemetry_env()
    except Exception:
        pass


def load_config() -> dict[str, ProviderConfig]:
    """Load and cache provider configuration from YAML."""
    global _config_cache
    if _config_cache is not None:
        return _config_cache

    _ensure_env_loaded()

    with open(_config_path(), encoding="utf-8") as f:
        text = f.read()
        if yaml is not None:
            raw = yaml.safe_load(text)
        else:
            raw = _parse_simple_yaml(text)

    _config_cache = {}
    for name, cfg in raw.get("sources", {}).items():
        _config_cache[name] = ProviderConfig(
            name=name,
            env_enabled=cfg.get("env_enabled", ""),
            data_dir=cfg.get("data_dir", ""),
            rtk_cwd=cfg.get("rtk_cwd"),
            env_home=cfg.get("env_home"),
            label=cfg.get("label", name),
            env_stats=cfg.get("env_stats"),
        )
    return _config_cache


def get_provider(name: str) -> ProviderConfig | None:
    """Get configuration for a specific provider."""
    return load_config().get(name)


def is_enabled(name: str) -> bool:
    """Check if provider is enabled via environment variable.

    Disabled by default if env var is not set or empty.
    """
    provider = get_provider(name)
    if not provider:
        return False

    value = os.environ.get(provider.env_enabled, "").strip().lower()
    if not value:
        return False
    return value in ("1", "true", "yes", "on")


def get_enabled_providers() -> list[dict[str, Any]]:
    """Get list of all enabled providers as JSON-serializable dicts.

    If no provider is explicitly enabled via environment variable, automatically enable
    providers whose data directory exists on disk, or fall back to 'cursor'.
    """
    from telemetry_db import fetch_events_from_db

    all_configs = load_config()
    providers = [p for p in all_configs.values() if is_enabled(p.name)]

    if not providers:
        for p in all_configs.values():
            d = get_data_dir(p.name)
            if d is not None and d.is_dir():
                providers.append(p)

    if not providers:
        cursor = get_provider("cursor")
        if cursor:
            providers = [cursor]

    result = []
    for p in providers:
        try:
            count = len(fetch_events_from_db(p.name))
        except Exception:
            count = 0
        result.append(
            {
                "id": p.name,
                "label": p.label,
                "event_count": count,
            }
        )
    return result


def get_data_dir(name: str) -> Path | None:
    """Get resolved data directory for a provider.

    1. Check direct env_stats override (can be a comma-separated list of env vars)
    2. Check env_home override (can be a comma-separated list of env vars)
    3. Fall back to expanding ~ in data_dir
    """
    provider = get_provider(name)
    if not provider:
        return None

    # Check if direct env_stats override exists
    if provider.env_stats:
        for var in provider.env_stats.split(","):
            val = os.environ.get(var.strip(), "").strip()
            if val:
                return Path(val).expanduser()

    # Check if env_home override exists
    if provider.env_home:
        for var in provider.env_home.split(","):
            val = os.environ.get(var.strip(), "").strip()
            if val:
                return Path(val).expanduser() / "token-telemetry"

    # Default: expand ~ in data_dir
    return Path(provider.data_dir).expanduser()


def get_rtk_cwd(name: str) -> Path | None:
    """Get resolved RTK working directory for a provider.

    If env_home is set and the env var exists, use it.
    Otherwise expand ~ in rtk_cwd.
    """
    provider = get_provider(name)
    if not provider or not provider.rtk_cwd:
        return None

    # Check if env_home override exists
    if provider.env_home:
        for var in provider.env_home.split(","):
            val = os.environ.get(var.strip(), "").strip()
            if val:
                return Path(val).expanduser()

    # Default: expand ~ in rtk_cwd
    return Path(provider.rtk_cwd).expanduser()


def get_all_providers() -> list[ProviderConfig]:
    """Get list of all configured providers (enabled or not)."""
    return list(load_config().values())
