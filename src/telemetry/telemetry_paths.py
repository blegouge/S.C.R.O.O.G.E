#!/usr/bin/env python3
"""Resolve S.C.R.O.O.G.E application vs persistent data directories."""

from __future__ import annotations

import os
from pathlib import Path


def ensure_extended_path() -> None:
    """Ensure PATH contains common CLI binary directories (Homebrew, local bin, cargo) even in frozen app bundle."""
    path_env = os.environ.get("PATH", "")
    existing = path_env.split(os.pathsep) if path_env else []
    try:
        home_path = Path.home()
    except (RuntimeError, OSError):
        home_path = None
    extra_dirs = [
        str(home_path / ".local" / "bin") if home_path else "",
        str(home_path / ".cargo" / "bin") if home_path else "",
        "/opt/homebrew/bin",
        "/usr/local/bin",
        "/usr/bin",
        "/bin",
    ]
    for d in extra_dirs:
        if d and d not in existing:
            existing.append(d)
    os.environ["PATH"] = os.pathsep.join(existing)


def load_telemetry_env() -> None:
    """Load configuration from .env file if present in the app directory or parents."""
    ensure_extended_path()

    # 1. Check override
    app_override = (
        os.environ.get("SCROOGE_TOKEN_TELEMETRY_APP", "").strip()
        or os.environ.get("CLAUDE_TOKEN_TELEMETRY_APP", "").strip()
        or os.environ.get("CURSOR_TOKEN_TELEMETRY_APP", "").strip()
    )
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
    try:
        home = Path.home()
    except (RuntimeError, OSError):
        home = None

    if home:
        search_paths.append(home / ".claude")
        search_paths.append(home / ".gemini")
        search_paths.append(home / ".gemini" / "antigravity")
        search_paths.append(home / ".hermes")
        search_paths.append(home / ".codex")
        search_paths.append(home / ".cursor")
        search_paths.append(home / ".config" / "scrooge")
        search_paths.append(home / ".scrooge")

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


_this_dir = Path(__file__).resolve().parent
if _this_dir.name == "telemetry" and _this_dir.parent.name == "src":
    DEFAULT_APP_DIR = _this_dir.parent.parent
else:
    DEFAULT_APP_DIR = _this_dir

from providers_config import get_data_dir


def _path_is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.expanduser().resolve())
        return True
    except (OSError, ValueError):
        return False


# Deployment roots, longest first: ~/.gemini/antigravity is nested in ~/.gemini.
_HOME_HINTS: tuple[tuple[str, str, str], ...] = (
    ("CLAUDE_HOME", ".claude", "claude"),
    ("ANTIGRAVITY_HOME", ".gemini/antigravity", "antigravity"),
    ("GEMINI_HOME", ".gemini", "gemini"),
    ("HERMES_HOME", ".hermes", "hermes"),
    ("CODEX_HOME", ".codex", "codex"),
    ("CURSOR_HOME", ".cursor", "cursor"),
)

_EVENT_HINTS: tuple[tuple[str, str], ...] = (
    ("CLAUDE_TT_EVENT", "claude"),
    ("GEMINI_TT_EVENT", "gemini"),
    ("ANTIGRAVITY_TT_EVENT", "antigravity"),
    ("HERMES_TT_EVENT", "hermes"),
    ("CODEX_TT_EVENT", "codex"),
    ("CURSOR_TT_EVENT", "cursor"),
)


def infer_source() -> str:
    """Infer the active telemetry provider from hook/runtime context."""
    explicit = os.environ.get("SCROOGE_TELEMETRY_SOURCE", "").strip().lower()
    if explicit:
        return explicit

    # The install path is the only unambiguous signal: every agent gets its own
    # deployment root, whereas hook wrappers broadcast all *_TT_EVENT variables.
    this_dir = Path(__file__).resolve().parent
    for env_name, _rel_home, source in _HOME_HINTS:
        configured = os.environ.get(env_name, "").strip()
        if configured and _path_is_relative_to(this_dir, Path(configured)):
            return source
    try:
        home = Path.home()
    except (RuntimeError, OSError):
        home = None

    if home:
        for _env_name, rel_home, source in _HOME_HINTS:
            try:
                if _path_is_relative_to(this_dir, home / rel_home):
                    return source
            except (RuntimeError, OSError):
                pass

    # Event markers are trustworthy only when a single agent claims the event.
    claimed = {source for env_name, source in _EVENT_HINTS if os.environ.get(env_name, "").strip()}
    if len(claimed) == 1:
        return claimed.pop()

    runtime_hints = (
        ("CODEX_THREAD_ID", "codex"),
        ("CODEX_INTERNAL_ORIGINATOR_OVERRIDE", "codex"),
    )
    for env_name, source in runtime_hints:
        if os.environ.get(env_name, "").strip():
            return source

    return "claude"


def resolve_data_dir(source: str | None = None) -> Path:
    """Persistent telemetry storage (events.jsonl, layout, diff-only cache)."""
    # 1. Direct environment variable override
    override = (
        os.environ.get("SCROOGE_TOKEN_TELEMETRY_DATA_DIR", "").strip()
        or os.environ.get("CLAUDE_TOKEN_TELEMETRY_DATA_DIR", "").strip()
        or os.environ.get("CODEX_TOKEN_TELEMETRY_DATA_DIR", "").strip()
        or os.environ.get("CURSOR_TOKEN_TELEMETRY_DATA_DIR", "").strip()
    )
    if override:
        return Path(override).expanduser()
    data_dir = get_data_dir(source or infer_source())
    if data_dir is None:
        try:
            home = Path.home()
        except (RuntimeError, OSError):
            home = Path.cwd()
        src = infer_source()
        if src == "codex":
            return home / ".codex" / "token-telemetry"
        if src == "cursor":
            return home / ".cursor" / "token-telemetry"
        if src == "gemini":
            return home / ".gemini" / "token-telemetry"
        if src == "antigravity":
            return home / ".gemini" / "antigravity" / "token-telemetry"
        if src == "hermes":
            return home / ".hermes" / "token-telemetry"
        return home / ".claude" / "token-telemetry"
    return data_dir


def resolve_log_file(source: str | None = None) -> Path:
    return resolve_data_dir(source=source) / "events.jsonl"


def resolve_app_dir() -> Path:
    """Application code, venv, dashboard assets, build scripts."""
    override = (
        os.environ.get("SCROOGE_TOKEN_TELEMETRY_APP", "").strip()
        or os.environ.get("CURSOR_TOKEN_TELEMETRY_APP", "").strip()
    )
    if override:
        return Path(override).expanduser()
    return DEFAULT_APP_DIR


def resolve_venv_python() -> Path:
    return resolve_app_dir() / ".venv-desktop" / "bin" / "python"


def resolve_venv_claw_compactor() -> Path:
    return resolve_app_dir() / ".venv-desktop" / "bin" / "claw-compactor"
