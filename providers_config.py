#!/usr/bin/env python3
"""Load and access provider configuration from providers_config.yaml."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Optional

import yaml


@dataclass
class ProviderConfig:
    """Configuration for a telemetry provider."""
    name: str
    env_enabled: str
    data_dir: str
    rtk_cwd: Optional[str]
    env_home: Optional[str]
    label: str
    env_stats: Optional[str] = None


_config_cache: dict[str, ProviderConfig] | None = None


def _config_path() -> Path:
    return Path(__file__).parent / "providers_config.yaml"


def load_config() -> dict[str, ProviderConfig]:
    """Load and cache provider configuration from YAML."""
    global _config_cache
    if _config_cache is not None:
        return _config_cache

    with open(_config_path(), encoding="utf-8") as f:
        raw = yaml.safe_load(f)

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


def get_enabled_providers() -> list[dict[str, str]]:
    """Get list of all enabled providers as JSON-serializable dicts."""
    providers = [p for p in load_config().values() if is_enabled(p.name)]
    return [{"id": p.name, "label": p.label} for p in providers]


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
