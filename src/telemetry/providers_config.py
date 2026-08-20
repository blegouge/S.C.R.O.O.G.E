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
    providers whose data directory exists on disk, or fall back to 'claude'.
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
        claude = get_provider("claude")
        if claude:
            providers = [claude]

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


def get_home_dir(name: str) -> Path:
    """Get resolved home directory for an agent provider."""
    provider = get_provider(name)
    if provider and provider.env_home:
        for var in provider.env_home.split(","):
            val = os.environ.get(var.strip(), "").strip()
            if val:
                return Path(val).expanduser()

    defaults: dict[str, Path] = {
        "claude": Path.home() / ".claude",
        "gemini": Path.home() / ".gemini",
        "antigravity": Path.home() / ".gemini" / "antigravity",
        "hermes": Path.home() / ".hermes",
        "codex": Path.home() / ".codex",
        "cursor": Path.home() / ".cursor",
    }
    return defaults.get(name, Path.home() / f".{name}")


def find_rtk_binary() -> str | None:
    """Locate rtk executable on PATH or in common install paths."""
    import shutil

    env_rtk = os.environ.get("RTK_BIN", "").strip()
    if env_rtk and Path(env_rtk).is_file():
        return env_rtk
    found = shutil.which("rtk")
    if found:
        return found
    candidates = [
        Path("/opt/homebrew/bin/rtk"),
        Path("/usr/local/bin/rtk"),
        Path.home() / ".local" / "bin" / "rtk",
        Path.home() / ".cargo" / "bin" / "rtk",
        Path("/usr/bin/rtk"),
    ]
    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)
    return None


def inspect_agent_status(source: str) -> dict[str, Any]:
    """Inspect disk state, configurations, and telemetry activity for an agent provider."""
    provider = get_provider(source)
    if not provider:
        return {"ok": False, "error": f"Unknown provider: {source}"}

    home = get_home_dir(source)
    data_dir = get_data_dir(source)

    # 1. Telemetry Data & Logs
    events_count = 0
    last_event_ts: str | None = None
    if data_dir:
        try:
            from telemetry_db import fetch_events_from_db

            events = fetch_events_from_db(source)
            events_count = len(events)
            if events:
                last_event_ts = str(events[-1].get("ts") or events[-1].get("timestamp") or "")
        except Exception:
            pass

    telemetry_active = is_enabled(source) or (events_count > 0)
    telemetry_installed = data_dir is not None and data_dir.is_dir()

    if telemetry_active:
        telemetry_status = "active"
        telemetry_detail = f"{events_count} events recorded"
    elif telemetry_installed:
        telemetry_status = "installed"
        telemetry_detail = "Directory present, 0 events logged"
    else:
        telemetry_status = "missing"
        telemetry_detail = "Data directory missing"

    # 2. Hooks & Event Interceptors
    hooks_file = home / "hooks.json"
    settings_file = home / "settings.json"
    hooks_dir = home / "hooks"
    hooks_installed = (
        hooks_file.is_file()
        or settings_file.is_file()
        or (hooks_dir.is_dir() and any(hooks_dir.iterdir()))
    )
    hooks_active = events_count > 0 and hooks_installed

    if hooks_active:
        hooks_status = "active"
        hooks_detail = "Hooks registered & active"
    elif hooks_installed:
        hooks_status = "installed"
        hooks_detail = "Hook settings/scripts found"
    else:
        hooks_status = "missing"
        hooks_detail = "No hook settings found"

    # 3. RTK (Reduction Token Kit)
    rtk_bin = find_rtk_binary()
    rtk_cwd = get_rtk_cwd(source)
    rtk_cwd_exists = rtk_cwd is not None and rtk_cwd.is_dir()

    if rtk_bin and (rtk_cwd_exists or events_count > 0):
        rtk_status = "active"
        rtk_detail = "RTK binary found & working dir active"
    elif rtk_bin or rtk_cwd_exists:
        rtk_status = "installed"
        rtk_detail = "RTK binary present" if rtk_bin else "RTK working dir found"
    else:
        rtk_status = "missing"
        rtk_detail = "RTK CLI not found"

    # 4. Context Rules (.mdc / AGENTS.md / rules)
    rules_dir = home / "rules"
    mdc_files = list(rules_dir.glob("*.mdc")) if rules_dir.is_dir() else []
    agents_md = home / "AGENTS.md"
    cursorrules = home / ".cursorrules"
    rules_count = (
        len(mdc_files) + (1 if agents_md.is_file() else 0) + (1 if cursorrules.is_file() else 0)
    )

    if rules_count > 0:
        rules_status = "active"
        rules_detail = f"{rules_count} rule file(s) found"
    else:
        rules_status = "missing"
        rules_detail = "No rule file found"

    # 5. Agent Skills (SKILL.md)
    skills_dir = home / "skills"
    skills_count = 0
    if skills_dir.is_dir():
        skills_count = len(list(skills_dir.rglob("SKILL.md")))

    if skills_count > 0:
        skills_status = "active"
        skills_detail = f"{skills_count} skill(s) installed"
    else:
        skills_status = "missing"
        skills_detail = "No skill installed"

    # 6. Token Compactor Stack
    compactor_installed = False
    if data_dir and data_dir.is_dir():
        compactor_files = [
            "claw_compactor_adapter.py",
            "smart_crusher.py",
            "ccr_manager.py",
            "token_compactor.py",
        ]
        compactor_installed = any((data_dir / f).is_file() for f in compactor_files)

    if compactor_installed and events_count > 0:
        compactor_status = "active"
        compactor_detail = "Compactor stack active"
    elif compactor_installed:
        compactor_status = "installed"
        compactor_detail = "Compactor scripts present"
    else:
        compactor_status = "missing"
        compactor_detail = "Compactor stack missing"

    # 7. MCP Integration
    mcp_json = home / "mcp.json"
    mcp_dir = home / "mcp"
    mcp_installed = mcp_json.is_file() or (mcp_dir.is_dir() and any(mcp_dir.iterdir()))
    if mcp_installed:
        mcp_status = "active"
        mcp_detail = "MCP configuration present"
    else:
        mcp_status = "missing"
        mcp_detail = "No MCP server configured"

    items = [
        {
            "id": "telemetry",
            "label_key": "itemTelemetry",
            "status": telemetry_status,
            "detail": telemetry_detail,
        },
        {"id": "hooks", "label_key": "itemHooks", "status": hooks_status, "detail": hooks_detail},
        {"id": "rtk", "label_key": "itemRtk", "status": rtk_status, "detail": rtk_detail},
        {"id": "rules", "label_key": "itemRules", "status": rules_status, "detail": rules_detail},
        {
            "id": "skills",
            "label_key": "itemSkills",
            "status": skills_status,
            "detail": skills_detail,
        },
        {
            "id": "compactor",
            "label_key": "itemCompactor",
            "status": compactor_status,
            "detail": compactor_detail,
        },
        {"id": "mcp", "label_key": "itemMcp", "status": mcp_status, "detail": mcp_detail},
    ]

    active_count = sum(1 for item in items if item["status"] == "active")
    installed_count = sum(1 for item in items if item["status"] in ("active", "installed"))
    total_count = len(items)

    return {
        "ok": True,
        "source": source,
        "label": provider.label,
        "home": str(home),
        "data_dir": str(data_dir) if data_dir else None,
        "active_count": active_count,
        "installed_count": installed_count,
        "total_count": total_count,
        "events_count": events_count,
        "last_event_ts": last_event_ts,
        "items": items,
    }


def find_hub_files_root() -> Path:
    """Find absolute path to hub_files directory."""
    if getattr(sys, "frozen", False):
        meipass = Path(getattr(sys, "_MEIPASS", "."))
        if (meipass / "hub_files").is_dir():
            return meipass / "hub_files"
        return meipass
    this_dir = Path(__file__).resolve().parent
    for p in (this_dir, this_dir.parent, this_dir.parent.parent):
        if (p / "hub_files").is_dir():
            return p / "hub_files"
    return Path.cwd() / "hub_files"


def install_agent_component(source: str, component: str = "all") -> dict[str, Any]:
    """Install or deploy missing components (hooks, rules, skills, compactor, mcp, rtk, telemetry) for an agent."""
    import shutil

    provider = get_provider(source)
    if not provider:
        return {"ok": False, "error": f"Unknown provider: {source}"}

    home = get_home_dir(source)
    data_dir = get_data_dir(source) or (home / "token-telemetry")
    hub_files = find_hub_files_root()
    repo_root = hub_files.parent if hub_files.name == "hub_files" else hub_files

    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    from install_helpers import copy_tree_idempotent, deploy_token_telemetry_runtime

    def _safe_copy(src_file: Path, dst_file: Path) -> None:
        if not src_file.is_file():
            return
        try:
            if src_file.resolve() == dst_file.resolve():
                return
        except Exception:
            pass
        try:
            shutil.copy2(src_file, dst_file)
        except shutil.SameFileError:
            pass
        except Exception as copy_err:
            print(f"Warning: safe copy failed {src_file} -> {dst_file}: {copy_err}")

    try:
        home.mkdir(parents=True, exist_ok=True)
        data_dir.mkdir(parents=True, exist_ok=True)

        installed_items: list[str] = []

        # 1. Telemetry Data & Logs
        if component in ("all", "telemetry"):
            events_file = data_dir / "events.jsonl"
            events_file.touch(exist_ok=True)
            os.environ[provider.env_enabled] = "1"
            installed_items.append("telemetry")

        # 2. Hooks & Event Interceptors
        if component in ("all", "hooks"):
            hooks_dst = home / "hooks"
            hooks_dst.mkdir(parents=True, exist_ok=True)
            if (hub_files / "hooks").is_dir():
                copy_tree_idempotent(hub_files / "hooks", hooks_dst, overwrite=True)
            _safe_copy(hub_files / "hooks.json", home / "hooks.json")
            installed_items.append("hooks")

        # 3. RTK Working Directory
        if component in ("all", "rtk"):
            rtk_cwd = get_rtk_cwd(source) or home
            rtk_cwd.mkdir(parents=True, exist_ok=True)
            installed_items.append("rtk")

        # 4. Context Rules (.mdc / AGENTS.md)
        if component in ("all", "rules"):
            rules_dst = home / "rules"
            rules_dst.mkdir(parents=True, exist_ok=True)
            if (hub_files / "rules").is_dir():
                copy_tree_idempotent(hub_files / "rules", rules_dst, overwrite=True)
            _safe_copy(hub_files / "AGENT.md", home / "AGENT.md")
            installed_items.append("rules")

        # 5. Agent Skills (SKILL.md)
        if component in ("all", "skills"):
            skills_dst = home / "skills"
            skills_dst.mkdir(parents=True, exist_ok=True)
            if (hub_files / "skills").is_dir():
                copy_tree_idempotent(hub_files / "skills", skills_dst, overwrite=False)
            installed_items.append("skills")

        # 6. Token Compactor Stack
        if component in ("all", "compactor"):
            try:
                deploy_token_telemetry_runtime(repo_root, data_dir)
            except Exception:
                pass
            installed_items.append("compactor")

        # 7. MCP Integration
        if component in ("all", "mcp"):
            _safe_copy(hub_files / "mcp.json", home / "mcp.json")
            mcp_dst = home / "mcp"
            mcp_dst.mkdir(parents=True, exist_ok=True)
            installed_items.append("mcp")

        # Re-inspect to get updated status
        updated_status = inspect_agent_status(source)

        return {
            "ok": True,
            "source": source,
            "installed": installed_items,
            "status": updated_status,
        }
    except Exception as exc:
        return {"ok": False, "source": source, "error": str(exc)}
