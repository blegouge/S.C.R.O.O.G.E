# install_helpers.py - Shared installation utility functions and hook configuration transformers.
from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from typing import Any

# Global definitions
DASHBOARD_RUNTIME_FILES = {
    # File name -> Relative source directory in repo
    ".env": ".",
    ".env.example": ".",
    "dashboard.html": "dashboard",
    "dashboard.css": "dashboard",
    "dashboard.js": "dashboard",
    "dashboard_layout.js": "dashboard",
    "dashboard_report.js": "dashboard",
    "dashboard_render.js": "dashboard",
    "dashboard_translations.js": "dashboard",
    "dashboard_utils.js": "dashboard",
    "dashboard_api.js": "dashboard",
    "dashboard_charts.js": "dashboard",
    "dashboard_stats.js": "dashboard",
    "dashboard_tables.js": "dashboard",
    "dashboard_app.py": "dashboard",
    "providers_config.py": "src/telemetry",
    "providers_config.yaml": "src/telemetry",
    "report.py": "cli",
    "requirements-desktop.txt": ".",
    "requirements-desktop-linux.lock": ".",
    "requirements-desktop-macos.lock": ".",
    "requirements-desktop-windows.lock": ".",
    "rtk_resolver.py": "src/telemetry",
    "serve_dashboard.py": "dashboard",
    "telemetry_common.py": "src/telemetry",
    "telemetry_config.py": "src/telemetry",
    "telemetry_db.py": "src/telemetry",
    "telemetry_metrics.py": "src/telemetry",
    "telemetry_paths.py": "src/telemetry",
    "claw_compactor_adapter.py": "src/compaction",
    "headroom_adapter.py": "src/compaction",
    "token_compactor.py": "src/compaction",
    "smart_crusher.py": "src/compaction",
    "ccr_manager.py": "src/compaction",
}

TOKEN_TELEMETRY_PRESERVE_NAMES = {
    ".venv-desktop",
    "dashboard-layout.json",
    "dashboard.log",
    "dashboard.pid",
    "events.jsonl",
    "icon.jpg",
    "telemetry.db",
    "telemetry.db-shm",
    "telemetry.db-wal",
    "__pycache__",
}


def get_provider(target_name: str) -> Any:
    """Get provider instance for the given target IDE name."""
    try:
        from providers import get_provider as get_ide_provider

        return get_ide_provider(target_name)
    except (ImportError, KeyError, Exception):
        return None


def transform_hooks_cursor_to_claude(hooks_data: dict[str, Any]) -> dict[str, Any]:
    """Transform Cursor/Gemini hooks.json format to Claude Code settings.json format."""
    provider = get_provider("claude")
    if provider is not None:
        cursor_hooks = hooks_data.get("hooks", {})
        transformed = provider.transform_hooks_config(cursor_hooks)
        return {"hooks": transformed}

    from collections import defaultdict

    CLAUDE_SUPPORTED_EVENTS = {
        "PreToolUse",
        "PostToolUse",
        "Stop",
        "SubagentStart",
        "SubagentStop",
        "SessionStart",
    }

    CLAUDE_EVENT_MAPPING = {
        "preToolUse": "PreToolUse",
        "postToolUse": "PostToolUse",
        "stop": "Stop",
        "subagentStop": "SubagentStop",
        "sessionStart": "SessionStart",
        "subagentStart": "SubagentStart",
    }

    CLAUDE_TOOL_MAPPING = {"Shell": "Bash", "shell": "Bash"}

    result: dict[str, Any] = {"hooks": {}}
    source_hooks = hooks_data.get("hooks", {})

    for event_name, items in source_hooks.items():
        claude_event = CLAUDE_EVENT_MAPPING.get(event_name)
        if claude_event is None:
            claude_event = event_name[0].upper() + event_name[1:]
        if claude_event not in CLAUDE_SUPPORTED_EVENTS:
            continue

        by_matcher: dict[str, list[dict[str, str]]] = defaultdict(list)
        for item in items:
            matcher = item.get("matcher", "*")
            matcher = CLAUDE_TOOL_MAPPING.get(matcher, matcher)
            hook_entry = {"type": "command", "command": item["command"]}
            by_matcher[matcher].append(hook_entry)

        result["hooks"][claude_event] = [
            {"matcher": matcher, "hooks": hooks_list} for matcher, hooks_list in by_matcher.items()
        ]

    return result


def merge_hooks_claude(existing: dict[str, Any], new_hooks: dict[str, Any]) -> dict[str, Any]:
    """Merge new hooks into existing Claude Code settings.json without duplicates."""
    provider = get_provider("claude")
    if provider is not None:
        existing_hooks = existing.get("hooks", {})
        new_hooks_dict = new_hooks.get("hooks", {})
        merged_hooks = provider.merge_hooks_config(existing_hooks, new_hooks_dict)
        return {"hooks": merged_hooks}

    result: dict[str, Any] = {"hooks": {}}

    for event, groups in existing.get("hooks", {}).items():
        result["hooks"][event] = [
            {"matcher": g["matcher"], "hooks": list(g.get("hooks", []))} for g in groups
        ]

    for event, groups in new_hooks.get("hooks", {}).items():
        if event not in result["hooks"]:
            result["hooks"][event] = []

        existing_groups = result["hooks"][event]

        for new_group in groups:
            new_matcher = new_group["matcher"]
            target_group = None
            for eg in existing_groups:
                if eg["matcher"] == new_matcher:
                    target_group = eg
                    break

            if target_group is None:
                existing_groups.append(
                    {"matcher": new_matcher, "hooks": list(new_group.get("hooks", []))}
                )
            else:
                existing_commands = {h["command"] for h in target_group.get("hooks", [])}
                for hook in new_group.get("hooks", []):
                    if hook["command"] not in existing_commands:
                        target_group["hooks"].append(hook)

    return result


def print_header(title: str) -> None:
    print("\n" + "=" * 64)
    print(f" {title}")
    print("=" * 64)


def prompt_choice(question: str, choices: list[str], default: str) -> str:
    print(f"\n{question}")
    for idx, choice in enumerate(choices, 1):
        print(f"  {idx}. {choice}")
    while True:
        try:
            val = input(f"Select option [default: {default}]: ").strip()
            if not val:
                return default
            val_idx = int(val)
            if 1 <= val_idx <= len(choices):
                return choices[val_idx - 1]
            print(f"Please enter a number between 1 and {len(choices)}.")
        except ValueError:
            print("Invalid input. Please enter a valid number.")


def prompt_input(question: str, default: str = "") -> str:
    default_show = f" [default: {default}]" if default else ""
    val = input(f"{question}{default_show}: ").strip()
    return val if val else default


def load_env_file(path: Path) -> dict[str, str]:
    """Parse a simple key-value env file."""
    if not path.exists():
        return {}
    res = {}
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, val = line.split("=", 1)
                res[key.strip()] = val.strip().strip('"').strip("'")
    return res


def save_env_file(path: Path, data: dict[str, str], comment_header: str = "") -> None:
    """Write a simple key-value env file."""
    with path.open("w", encoding="utf-8") as f:
        if comment_header:
            f.write(comment_header + "\n")
        for k, v in data.items():
            f.write(f"{k}={v}\n")


def hook_item_commands(item: dict) -> set[str]:
    """Return command identities from Cursor-style or Codex-style hook entries."""
    commands: set[str] = set()
    command = item.get("command")
    if isinstance(command, str) and command:
        commands.add(command)
    nested = item.get("hooks")
    if isinstance(nested, list):
        for handler in nested:
            if isinstance(handler, dict):
                nested_cmd = handler.get("command")
                if isinstance(nested_cmd, str) and nested_cmd:
                    commands.add(nested_cmd)
    return commands


def merge_hook_lists(existing_list: list, template_list: list) -> int:
    """Merge hook groups while preserving custom user hooks."""
    added = 0
    for h_item in template_list:
        if not isinstance(h_item, dict):
            if h_item not in existing_list:
                existing_list.append(h_item)
                added += 1
            continue

        h_matcher = h_item.get("matcher")
        h_cmds = hook_item_commands(h_item)
        is_present = False
        for ext_item in existing_list:
            if ext_item == h_item:
                is_present = True
                break
            if not isinstance(ext_item, dict):
                continue
            same_matcher = ext_item.get("matcher") == h_matcher
            ext_cmds = hook_item_commands(ext_item)
            if h_cmds and same_matcher and h_cmds.issubset(ext_cmds):
                is_present = True
                break
            if h_cmds and ext_cmds and h_cmds == ext_cmds:
                is_present = True
                break
        if not is_present:
            existing_list.append(h_item)
            added += 1
    return added


def copy_tree_idempotent(src: Path, dst: Path, ignore=None, overwrite: bool = True) -> None:
    """Copy directory src to dst, creating parent directories and overwriting existing files."""
    if not src.exists() and not src.is_symlink():
        return
    try:
        src_abs = src.resolve()
    except Exception:
        src_abs = src
    try:
        dst_abs = dst.resolve()
    except Exception:
        dst_abs = dst

    dst.mkdir(parents=True, exist_ok=True)
    for item in os.listdir(src):
        s = src / item
        d = dst / item
        if ignore and s.name in ignore:
            continue
        try:
            s_abs = s.resolve()
            if dst_abs == s_abs or dst_abs.is_relative_to(s_abs):
                continue
        except Exception:
            pass

        if s.is_symlink():
            if not overwrite and (d.exists() or d.is_symlink()):
                continue
            try:
                if d.exists() or d.is_symlink():
                    d.unlink()
                target = os.readlink(s)
                d.symlink_to(target)
            except Exception as e:
                print(f"Warning: Could not copy symlink {s} to {d}: {e}")
        elif s.is_dir():
            copy_tree_idempotent(s, d, ignore, overwrite=overwrite)
        else:
            if not overwrite and d.exists():
                continue
            if s.is_symlink() and not s.exists():
                print(f"Skipping broken symlink: {s}")
                continue
            try:
                shutil.copy2(s, d)
            except shutil.SameFileError:
                pass
            except Exception as e:
                print(f"Warning: Could not copy file {s} to {d}: {e}")


def deploy_token_telemetry_runtime(repo_root: Path, dst: Path) -> None:
    """Deploy only dashboard/runtime files into <HUB>/token-telemetry."""
    dst.mkdir(parents=True, exist_ok=True)
    for name, rel_dir in DASHBOARD_RUNTIME_FILES.items():
        src = repo_root / rel_dir / name
        if src.is_file():
            shutil.copy2(src, dst / name)

    icon_src = repo_root / "docs" / "fr" / "assets" / "icon.jpg"
    if icon_src.is_file():
        shutil.copy2(icon_src, dst / "icon.jpg")
    else:
        print(f"Warning: dashboard icon source not found: {icon_src}")


def prune_token_telemetry_runtime(dst: Path) -> None:
    """Remove old repo-copy artifacts from <HUB>/token-telemetry while preserving runtime data."""
    allowed = set(DASHBOARD_RUNTIME_FILES) | TOKEN_TELEMETRY_PRESERVE_NAMES
    if not dst.exists():
        return
    for item in dst.iterdir():
        if item.name in allowed:
            continue
        if item.is_dir():
            shutil.rmtree(item)
        else:
            item.unlink()


def detect_target_name(hub: Path) -> str:
    """Return the target provider id from a hub path."""
    hub_str = str(hub).lower()
    if "cursor" in hub_str:
        return "cursor"
    if "antigravity" in hub_str:
        return "antigravity"
    if "claude" in hub_str:
        return "claude"
    if "hermes" in hub_str:
        return "hermes"
    if "codex" in hub_str:
        return "codex"
    if "gemini" in hub_str:
        return "gemini"
    return "antigravity"


def json_to_toml_value(value: object) -> str:
    """Serialize simple JSON-like values to TOML."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, list):
        return "[" + ", ".join(json_to_toml_value(v) for v in value) + "]"
    return json.dumps(str(value))


def append_codex_mcp_config(config_path: Path, mcp_data: dict[str, object]) -> None:
    """Append missing MCP servers to Codex config.toml without parsing user settings."""
    existing = config_path.read_text(encoding="utf-8") if config_path.exists() else ""
    servers = mcp_data.get("mcpServers", {})
    if not isinstance(servers, dict):
        return

    lines: list[str] = []
    for server_name, server_config in servers.items():
        marker = f"[mcp_servers.{server_name}]"
        if marker in existing:
            continue
        if not isinstance(server_config, dict):
            continue
        lines.append("")
        lines.append(marker)
        for key in ("command", "args", "url", "cwd", "startup_timeout_sec", "tool_timeout_sec"):
            if key in server_config:
                lines.append(f"{key} = {json_to_toml_value(server_config[key])}")
        env = server_config.get("env")
        if isinstance(env, dict) and env:
            lines.append(f"[mcp_servers.{server_name}.env]")
            for env_key, env_value in env.items():
                lines.append(f"{env_key} = {json_to_toml_value(env_value)}")

    if not lines:
        print(f"All Codex MCP servers from template already present in {config_path}.")
        return

    config_path.parent.mkdir(parents=True, exist_ok=True)
    header = "\n# S.C.R.O.O.G.E. MCP servers (managed by install_stack.py)\n"
    with config_path.open("a", encoding="utf-8") as f:
        if existing and not existing.endswith("\n"):
            f.write("\n")
        f.write(header)
        f.write("\n".join(lines).lstrip())
        f.write("\n")
    print(f"Added Codex MCP server configuration to {config_path}.")
