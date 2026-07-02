#!/usr/bin/env python3
"""Unified Configuration Manager for S.C.R.O.O.G.E. and Optimization Stack."""

from __future__ import annotations

import os
import pathlib
import sys

# Ensure path utilities are loaded first to configure base environment
import telemetry_paths


class ConfigManager:
    """Centralised settings manager resolving environment and configuration files."""

    def __init__(self, cursor_home: pathlib.Path | None = None) -> None:
        # Load .env variables first
        telemetry_paths.load_telemetry_env()

        # Resolve home path for compression.env loading
        if cursor_home:
            self._home_path = cursor_home.resolve()
        else:
            home_dir = os.getenv("ANTIGRAVITY_HOME") or os.getenv("CURSOR_HOME")
            if home_dir:
                self._home_path = pathlib.Path(home_dir).resolve()
            else:
                self._home_path = pathlib.Path(__file__).resolve().parent.parent

        self._load_compression_env()

    def _load_compression_env(self) -> None:
        """Load compression.env from the active HUB directory."""
        env_path = self._home_path / "compression.env"
        if not env_path.is_file():
            return
        try:
            for raw_line in env_path.read_text(encoding="utf-8").splitlines():
                line = raw_line.strip()
                if not line or line.startswith("#"):
                    continue
                if line.startswith("export "):
                    line = line[7:].strip()
                if "=" not in line:
                    continue
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if key and key not in os.environ:
                    os.environ[key] = value
        except OSError as exc:
            sys.stderr.write(f"[telemetry-config] Failed to read {env_path}: {exc}\n")

    def _get_env_str(self, key: str, default: str) -> str:
        return os.environ.get(key, default).strip()

    def _get_env_int(self, key: str, default: int) -> int:
        val = os.environ.get(key, "").strip()
        if not val:
            return default
        try:
            return int(val)
        except ValueError:
            return default

    def _get_env_float(self, key: str, default: float) -> float:
        val = os.environ.get(key, "").strip()
        if not val:
            return default
        try:
            return float(val)
        except ValueError:
            return default

    def _get_env_bool(self, key: str, default: bool) -> bool:
        val = os.environ.get(key, "").strip().lower()
        if not val:
            return default
        return val in ("1", "true", "yes", "on")

    @property
    def compression_backend(self) -> str:
        return self._get_env_str("COMPRESSION_BACKEND", "claw").lower()

    @property
    def task_brief_enforce(self) -> str:
        return self._get_env_str("TASK_BRIEF_ENFORCE", "deny").lower()

    @property
    def llmlingua_hook_rate(self) -> float:
        return self._get_env_float("LLMLINGUA_HOOK_RATE", 0.6)

    @property
    def llmlingua_hook_min_chars(self) -> int:
        return self._get_env_int("LLMLINGUA_HOOK_MIN_CHARS", 1200)

    @property
    def adaptive_ctx_token_threshold(self) -> int:
        return self._get_env_int("ADAPTIVE_CTX_TOKEN_THRESHOLD", 4000)

    @property
    def adaptive_ctx_message_threshold(self) -> int:
        return self._get_env_int("ADAPTIVE_CTX_MESSAGE_THRESHOLD", 10)

    @property
    def adaptive_ctx_structure_min_input_tokens(self) -> int:
        return self._get_env_int("ADAPTIVE_CTX_STRUCTURE_MIN_INPUT_TOKENS", 2500)

    @property
    def ccr_enabled(self) -> bool:
        return self._get_env_bool("CCR_ENABLED", True)

    @property
    def ccr_threshold_chars(self) -> int:
        return self._get_env_int("CCR_THRESHOLD_CHARS", 4000)

    @property
    def smart_crusher_n(self) -> int:
        return self._get_env_int("SMART_CRUSHER_N", 10)

    @property
    def smart_crusher_m(self) -> int:
        return self._get_env_int("SMART_CRUSHER_M", 10)

    @property
    def llmlingua_blocking_init(self) -> bool:
        return self._get_env_bool("LLMLINGUA_BLOCKING_INIT", False)


# Global config instance initialized on import
config = ConfigManager()
