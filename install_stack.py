#!/usr/bin/env python3
"""install_stack.py - Automated, interactive, and idempotent installation of the Token Optimization Stack.

This script runs with the standard library only. It copies the reference files from
hub_files/ to all selected target HUBs (~/.cursor, ~/.gemini/antigravity, ~/.codex, etc.), prompts the user
for required MCP tokens once, rewrites configuration paths, updates rule/skill references
dynamically for the target IDE, sets up the Python venv, and runs the sanity check verification.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

# Repository root (where this script is located)
REPO_ROOT = Path(__file__).resolve().parent
HUB_FILES = REPO_ROOT / "hub_files"
CODEX_FILES = HUB_FILES / "codex"

DASHBOARD_RUNTIME_FILES = {
    ".env",
    ".env.example",
    "dashboard.html",
    "dashboard.css",
    "dashboard.js",
    "dashboard_translations.js",
    "dashboard_utils.js",
    "dashboard_api.js",
    "dashboard_charts.js",
    "dashboard_stats.js",
    "dashboard_tables.js",
    "dashboard_app.py",
    "providers_config.py",
    "providers_config.yaml",
    "report.py",
    "requirements-desktop.txt",
    "requirements-desktop.lock",
    "rtk_resolver.py",
    "serve_dashboard.py",
    "telemetry_common.py",
    "telemetry_config.py",
    "telemetry_db.py",
    "telemetry_metrics.py",
    "telemetry_paths.py",
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

# Add hub_files to sys.path for providers module
if str(HUB_FILES) not in sys.path:
    sys.path.insert(0, str(HUB_FILES))

# =============================================================================
# Provider-based hooks transformation
# =============================================================================


def _get_provider(target_name: str):
    """Get provider instance for the given target IDE name.

    Falls back to legacy transformation functions if providers module is unavailable.
    """
    try:
        from providers import get_provider

        return get_provider(target_name)
    except (ImportError, KeyError, Exception):
        # If providers module is unavailable, return None to trigger fallback
        return None


def transform_hooks_cursor_to_claude(hooks_data: dict[str, Any]) -> dict[str, Any]:
    """Transform Cursor/Gemini hooks.json format to Claude Code settings.json format.

    This is a legacy fallback function. New code should use ClaudeProvider.transform_hooks_config().
    """
    provider = _get_provider("claude")
    if provider is not None:
        # Extract the hooks dict from the full structure ({"version": 1, "hooks": {...}})
        cursor_hooks = hooks_data.get("hooks", {})
        transformed = provider.transform_hooks_config(cursor_hooks)
        # Wrap back in the expected structure for Claude
        return {"hooks": transformed}

    # Fallback to inline implementation if providers module unavailable
    from collections import defaultdict

    # Events supported by Claude Code (others will be skipped)
    CLAUDE_SUPPORTED_EVENTS = {
        "PreToolUse",
        "PostToolUse",
        "Stop",
        "SubagentStart",
        "SubagentStop",
        "SessionStart",
    }

    # Event name mapping: Cursor (camelCase) -> Claude Code (PascalCase)
    CLAUDE_EVENT_MAPPING = {
        "preToolUse": "PreToolUse",
        "postToolUse": "PostToolUse",
        "stop": "Stop",
        "subagentStop": "SubagentStop",
        "sessionStart": "SessionStart",
        "subagentStart": "SubagentStart",
    }

    # Tool/matcher name mapping: Cursor -> Claude Code
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
    """Merge new hooks into existing Claude Code settings.json without duplicates.

    This is a legacy fallback function. New code should use ClaudeProvider.merge_hooks_config().

    Args:
        existing: Full settings.json content (e.g., {"hooks": {...}})
        new_hooks: Full hooks structure (e.g., {"hooks": {...}})

    Returns:
        Full settings.json content with merged hooks
    """
    provider = _get_provider("claude")
    if provider is not None:
        # Extract hooks dicts from the full structures
        existing_hooks = existing.get("hooks", {})
        new_hooks_dict = new_hooks.get("hooks", {})

        # Merge using provider
        merged_hooks = provider.merge_hooks_config(existing_hooks, new_hooks_dict)

        # Wrap back in full structure
        return {"hooks": merged_hooks}

    # Fallback to inline implementation if providers module unavailable
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
    """Copy directory src to dst, creating parent directories and overwriting existing files (if overwrite is True).
    Prevents infinite recursion if dst is inside src.
    """
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
    for name in DASHBOARD_RUNTIME_FILES:
        src = repo_root / name
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


def main() -> int:
    print_header("Token Optimization Stack - Installer")
    print(f"Source repository root: {REPO_ROOT}")

    # Load existing .env configs from the repository root
    repo_env_file = REPO_ROOT / ".env"
    repo_env = load_env_file(repo_env_file)

    # 1. Target Hub Directory Selection
    home = Path.home()
    possible_targets = [
        home / ".cursor",
        home / ".gemini" / "antigravity",
        home / ".claude",
        home / ".hermes",
        home / ".codex",
        home / ".gemini",
    ]

    detected_targets = [t for t in possible_targets if t.exists()]
    hubs_to_install: list[Path] = []

    if not detected_targets:
        hub_choice = prompt_input(
            "No active AI directories detected. Enter custom target directory",
            default=str(possible_targets[0]),
        )
        hubs_to_install.append(Path(os.path.expanduser(hub_choice)).resolve())
    else:
        print("\nDetected AI directories:")
        for idx, t in enumerate(detected_targets, 1):
            print(f"  [{idx}] {t}")

        choices = (
            ["All detected directories"] + [str(t) for t in detected_targets] + ["Custom directory"]
        )
        selection = prompt_choice(
            "Choose installation target:", choices, default="All detected directories"
        )

        if selection == "All detected directories":
            hubs_to_install = detected_targets
        elif selection == "Custom directory":
            hub_choice = prompt_input("Enter custom target directory")
            hubs_to_install.append(Path(os.path.expanduser(hub_choice)).resolve())
        else:
            hubs_to_install = [Path(selection)]

    print(f"Target HUB directories for installation: {', '.join(str(h) for h in hubs_to_install)}")

    # 2. Codebase Root Path Selection
    default_codebase = repo_env.get("CODEBASE_ROOT") or str(home / "www")
    codebase_root = prompt_input(
        "Enter the absolute path to your active codebases directory (used by code-explorer MCP)",
        default=default_codebase,
    )
    codebase_root_path = Path(os.path.expanduser(codebase_root)).resolve()

    # 3. Compression Backend selection
    current_backend = repo_env.get("COMPRESSION_BACKEND", "claw")
    chosen_backend = prompt_choice(
        "Choose the context compression backend:",
        ["claw", "headroom", "both", "off"],
        default=current_backend,
    )

    # Note: MCP secrets (mcp.secrets.env) are now initialized from template rather than prompted.

    # Persist configurations back to the repository's `.env`
    repo_env["CODEBASE_ROOT"] = codebase_root
    repo_env["COMPRESSION_BACKEND"] = chosen_backend

    # Save target homes & stats directories in repo's .env
    for HUB in hubs_to_install:
        target_name = detect_target_name(HUB)
        if target_name == "cursor":
            repo_env["CURSOR_HOME"] = str(HUB)
            repo_env["CURSOR_STATS_DIR"] = str(HUB / "token-telemetry")
        elif target_name == "antigravity":
            repo_env["ANTIGRAVITY_HOME"] = str(HUB)
            repo_env["ANTIGRAVITY_STATS_DIR"] = str(HUB / "token-telemetry")
        elif target_name == "claude":
            repo_env["CLAUDE_HOME"] = str(HUB)
            repo_env["CLAUDE_STATS_DIR"] = str(HUB / "token-telemetry")
        elif target_name == "hermes":
            repo_env["HERMES_HOME"] = str(HUB)
            repo_env["HERMES_STATS_DIR"] = str(HUB / "token-telemetry")
        elif target_name == "codex":
            repo_env["CODEX_HOME"] = str(HUB)
            repo_env["CODEX_STATS_DIR"] = str(HUB / "token-telemetry")
        elif target_name == "gemini":
            repo_env["GEMINI_HOME"] = str(HUB)
            repo_env["GEMINI_STATS_DIR"] = str(HUB / "token-telemetry")

    save_env_file(
        repo_env_file,
        repo_env,
        comment_header="# S.C.R.O.O.G.E. Config (Autogenerated / Updated by install_stack.py)",
    )
    print(f"Updated repository environment configuration at {repo_env_file}")

    # Loop to install on each target HUB
    for HUB in hubs_to_install:
        print_header(f"Deploying Stack to Target: {HUB}")

        # Create folders
        folders = [
            "bin",
            "hooks",
            "rules",
            "skills",
            "src",
            "providers",
            "projects",
            "token-telemetry",
        ]
        for folder in folders:
            (HUB / folder).mkdir(parents=True, exist_ok=True)

        # Copy Reference Hub Components
        print("Copying hub files from repository templates...")
        for folder in ["bin", "hooks", "rules", "skills", "src", "providers"]:
            overwrite = False if folder == "skills" else True
            copy_tree_idempotent(
                HUB_FILES / folder, HUB / folder, ignore=["__pycache__"], overwrite=overwrite
            )

        # Copy docs from the repository root
        copy_tree_idempotent(REPO_ROOT / "docs", HUB / "docs")

        if (HUB_FILES / "AGENT.md").exists():
            shutil.copy2(HUB_FILES / "AGENT.md", HUB / "AGENT.md")

        if detect_target_name(HUB) == "codex":
            codex_agents = CODEX_FILES / "AGENTS.md"
            target_agents = HUB / "AGENTS.md"
            if codex_agents.exists() and not target_agents.exists():
                shutil.copy2(codex_agents, target_agents)
                print(f"Generated Codex global guidance at {target_agents}")
            elif target_agents.exists():
                print(f"Preserved existing Codex global guidance at {target_agents}")

            codex_user_skills = home / ".agents" / "skills"
            copy_tree_idempotent(
                HUB_FILES / "skills", codex_user_skills, ignore=["__pycache__"], overwrite=False
            )
            print(f"Installed Codex user skills under {codex_user_skills}")

        # Deploy only dashboard/runtime files to <HUB>/token-telemetry.
        print("Deploying S.C.R.O.O.G.E. dashboard runtime files...")
        token_telemetry_dir = HUB / "token-telemetry"
        deploy_token_telemetry_runtime(REPO_ROOT, token_telemetry_dir)
        prune_token_telemetry_runtime(token_telemetry_dir)

        # Initialize Télémétrie events.jsonl
        events_file = HUB / "token-telemetry" / "events.jsonl"
        if not events_file.exists():
            events_file.touch(exist_ok=True)
            print("Initialized empty events.jsonl log.")

        # Initialize compression.env
        comp_env_template = HUB_FILES / "compression.env.example"
        comp_env_file = HUB / "compression.env"

        comp_data = {}
        if comp_env_file.exists():
            comp_data = load_env_file(comp_env_file)
        elif comp_env_template.exists():
            comp_data = load_env_file(comp_env_template)

        comp_data["COMPRESSION_BACKEND"] = chosen_backend

        # Ensure default thresholds are present
        defaults = {
            "TASK_BRIEF_ENFORCE": "deny",
            "LLMLINGUA_HOOK_RATE": "0.5",
            "LLMLINGUA_HOOK_MIN_CHARS": "2500",
            "ADAPTIVE_CTX_TOKEN_THRESHOLD": "4000",
            "ADAPTIVE_CTX_MESSAGE_THRESHOLD": "10",
            "ADAPTIVE_CTX_STRUCTURE_MIN_INPUT_TOKENS": "2500",
            "CCR_ENABLED": "1",
            "CCR_THRESHOLD_CHARS": "4000",
            "SMART_CRUSHER_N": "10",
            "SMART_CRUSHER_M": "10",
        }
        for k, v in defaults.items():
            if k not in comp_data:
                comp_data[k] = v

        save_env_file(
            comp_env_file,
            comp_data,
            comment_header="# Token optimization context compression configuration",
        )

        # Initialize mcp.secrets.env from example if not present
        secrets_file = HUB / "mcp.secrets.env"
        if not secrets_file.exists() and (HUB_FILES / "mcp.secrets.env.example").exists():
            shutil.copy2(HUB_FILES / "mcp.secrets.env.example", secrets_file)
            try:
                secrets_file.chmod(0o600)
                print(f"Generated default secrets template at {secrets_file}")
            except Exception as exc:
                print(f"Warning: Failed to set permissions on secrets file: {exc}")

        # Determine target name/type for replacements
        target_name = detect_target_name(HUB)

        def rewrite_config_content(content: str) -> str:
            # Replace template placeholders
            content = content.replace("{{HUB}}", str(HUB))
            content = content.replace("{{CODEBASE_ROOT}}", str(codebase_root_path))
            content = content.replace("{{HOME}}", str(home))

            # Replace home folders or reference hub roots (legacy/fallbacks)
            content = content.replace("~/.cursor", str(HUB))
            content = content.replace("~/.gemini/antigravity", str(HUB))
            content = content.replace("~/.codex", str(HUB))

            # Context-sensitive replacements for IDE/Agent name
            if target_name == "cursor":
                content = content.replace("Antigravity", "Cursor")
                content = content.replace("antigravity-ide", "cursor")
                content = content.replace("antigravity", "cursor")
            elif target_name == "antigravity":
                content = content.replace("Cursor", "Antigravity")
                content = content.replace("cursor", "antigravity")
            elif target_name == "claude":
                content = content.replace("Antigravity", "Claude Code")
                content = content.replace("antigravity-ide", "claude")
                content = content.replace("antigravity", "claude")
                content = content.replace("Cursor", "Claude Code")
                content = content.replace("cursor", "claude")
            elif target_name == "hermes":
                content = content.replace("Antigravity", "Hermes")
                content = content.replace("antigravity-ide", "hermes")
                content = content.replace("antigravity", "hermes")
                content = content.replace("Cursor", "Hermes")
                content = content.replace("cursor", "hermes")
            elif target_name == "codex":
                content = content.replace("Antigravity", "Codex")
                content = content.replace("antigravity-ide", "codex")
                content = content.replace("antigravity", "codex")
                content = content.replace("Cursor", "Codex")
                content = content.replace("cursor", "codex")
            elif target_name == "gemini":
                content = content.replace("Antigravity", "Gemini CLI")
                content = content.replace("antigravity-ide", "gemini")
                content = content.replace("antigravity", "gemini")
                content = content.replace("Cursor", "Gemini CLI")
                content = content.replace("cursor", "gemini")
            return content

        # Process mcp.json & hooks.json with merge support to avoid overwriting existing configs
        # 1) mcp.json
        mcp_tpl = HUB_FILES / "mcp.json"
        mcp_out = HUB / "mcp.json"
        if mcp_tpl.exists():
            tpl_text = rewrite_config_content(mcp_tpl.read_text(encoding="utf-8"))
            try:
                tpl_data = json.loads(tpl_text)
            except Exception as e:
                print(f"Error parsing template mcp.json: {e}")
                tpl_data = {}

            if mcp_out.exists():
                try:
                    out_data = json.loads(mcp_out.read_text(encoding="utf-8"))
                except Exception as e:
                    print(f"Warning: Failed to parse existing {mcp_out}: {e}. Overwriting.")
                    out_data = {}

                if "mcpServers" not in out_data:
                    out_data["mcpServers"] = {}

                tpl_servers = tpl_data.get("mcpServers", {})
                added_servers = []
                for srv_name, srv_config in tpl_servers.items():
                    if srv_name not in out_data["mcpServers"]:
                        out_data["mcpServers"][srv_name] = srv_config
                        added_servers.append(srv_name)

                if added_servers:
                    print(f"Added new MCP servers to {mcp_out}: {', '.join(added_servers)}")
                else:
                    print(f"All MCP servers from template already present in {mcp_out}.")

                mcp_out.write_text(json.dumps(out_data, indent=2), encoding="utf-8")
            else:
                mcp_out.write_text(json.dumps(tpl_data, indent=2), encoding="utf-8")
                print(f"Generated {mcp_out}")

            if target_name == "codex":
                append_codex_mcp_config(HUB / "config.toml", tpl_data)

        # 2) hooks.json (Cursor/Gemini/Codex) or settings.json (Claude Code)
        hooks_tpl = (
            CODEX_FILES / "hooks.json"
            if target_name == "codex" and (CODEX_FILES / "hooks.json").exists()
            else HUB_FILES / "hooks.json"
        )
        if hooks_tpl.exists():
            tpl_text = rewrite_config_content(hooks_tpl.read_text(encoding="utf-8"))
            try:
                tpl_data = json.loads(tpl_text)
            except Exception as e:
                print(f"Error parsing template hooks.json: {e}")
                tpl_data = {}

            if target_name == "claude":
                # Claude Code uses settings.json with a different format
                hooks_out = HUB / "settings.json"
                claude_hooks = transform_hooks_cursor_to_claude(tpl_data)

                if hooks_out.exists():
                    try:
                        out_data = json.loads(hooks_out.read_text(encoding="utf-8"))
                    except Exception as e:
                        print(f"Warning: Failed to parse existing {hooks_out}: {e}. Overwriting.")
                        out_data = {"hooks": {}}

                    # Merge preserving existing hooks
                    merged = merge_hooks_claude(out_data, claude_hooks)

                    # Count additions
                    existing_cmds = set()
                    for groups in out_data.get("hooks", {}).values():
                        for g in groups:
                            for h in g.get("hooks", []):
                                existing_cmds.add(h.get("command"))

                    new_cmds = set()
                    for groups in merged.get("hooks", {}).values():
                        for g in groups:
                            for h in g.get("hooks", []):
                                new_cmds.add(h.get("command"))

                    added_count = len(new_cmds - existing_cmds)

                    if added_count > 0:
                        print(f"Added {added_count} new hooks to {hooks_out} (Claude Code format).")
                    else:
                        print(f"All hooks from template already present in {hooks_out}.")

                    hooks_out.write_text(json.dumps(merged, indent=2), encoding="utf-8")
                else:
                    hooks_out.write_text(json.dumps(claude_hooks, indent=2), encoding="utf-8")
                    print(f"Generated {hooks_out} (Claude Code format)")
            else:
                # Cursor/Gemini/Hermes use hooks.json with original format
                hooks_out = HUB / "hooks.json"

                if hooks_out.exists():
                    try:
                        out_data = json.loads(hooks_out.read_text(encoding="utf-8"))
                    except Exception as e:
                        print(f"Warning: Failed to parse existing {hooks_out}: {e}. Overwriting.")
                        out_data = {}

                    # Preserve version from template if missing in output
                    if "version" not in out_data and "version" in tpl_data:
                        out_data["version"] = tpl_data["version"]

                    if "hooks" not in out_data:
                        out_data["hooks"] = {}

                    tpl_hooks = tpl_data.get("hooks", {})
                    added_count = 0
                    for hook_type, hook_list in tpl_hooks.items():
                        if hook_type not in out_data["hooks"]:
                            out_data["hooks"][hook_type] = []

                        existing_list = out_data["hooks"][hook_type]
                        added_count += merge_hook_lists(existing_list, hook_list)

                    if added_count > 0:
                        print(f"Added {added_count} new hooks to {hooks_out}.")
                    else:
                        print(f"All hooks from template already present in {hooks_out}.")

                    hooks_out.write_text(json.dumps(out_data, indent=2), encoding="utf-8")
                else:
                    hooks_out.write_text(json.dumps(tpl_data, indent=2), encoding="utf-8")
                    print(f"Generated {hooks_out}")

        # Process rules, skills, hooks, and bin files to dynamically rewrite references to Cursor vs Antigravity
        print("Normalizing path and IDE references for target IDE...")
        for root_dir in [HUB / "rules", HUB / "skills", HUB / "docs", HUB / "hooks", HUB / "bin"]:
            if root_dir.exists():
                for p in root_dir.rglob("*"):
                    if p.is_file() and p.suffix in {".md", ".mdc", ".json", ".py", ".sh"}:
                        try:
                            txt = p.read_text(encoding="utf-8", errors="ignore")
                            # Normalize references
                            new_txt = rewrite_config_content(txt)
                            if new_txt != txt:
                                p.write_text(new_txt, encoding="utf-8")
                        except Exception:
                            pass

        # Create Python Virtual Environment (.venv-desktop)
        venv_dir = HUB / "token-telemetry" / ".venv-desktop"
        req_lock = HUB / "token-telemetry" / "requirements-desktop.lock"
        req_file = (
            req_lock if req_lock.is_file() else HUB / "token-telemetry" / "requirements-desktop.txt"
        )

        print(f"Setting up Python venv at {venv_dir}...")
        try:
            python_bin = "python3"
            if shutil.which("python3.12"):
                python_bin = "python3.12"

            subprocess.run(
                [python_bin, "-m", "venv", str(venv_dir)], check=True, stdout=subprocess.DEVNULL
            )
            print("Virtual environment created.")

            if sys.platform == "win32":
                venv_python = venv_dir / "Scripts" / "python.exe"
            else:
                venv_python = venv_dir / "bin" / "python"

            subprocess.run(
                [str(venv_python), "-m", "pip", "install", "--upgrade", "pip"],
                check=True,
                stdout=subprocess.DEVNULL,
            )

            if req_file.exists():
                print(f"Installing dependencies from {req_file} (this might take a few moments)...")
                subprocess.run(
                    [str(venv_python), "-m", "pip", "install", "-r", str(req_file)],
                    check=True,
                    stdout=subprocess.DEVNULL,
                )
                print("Dependencies successfully installed.")

            # Create claw-compactor global symlink or wrapper
            claw_bin_dir = HUB / "bin"
            claw_bin_dir.mkdir(parents=True, exist_ok=True)

            if sys.platform == "win32":
                wrapper = claw_bin_dir / "claw-compactor.cmd"
                wrapper.write_text(
                    f'@echo off\n"{venv_dir}\\Scripts\\claw-compactor.exe" %*\n', encoding="ascii"
                )
            else:
                target_symlink = claw_bin_dir / "claw-compactor"
                source_binary = venv_dir / "bin" / "claw-compactor"
                if target_symlink.exists() or target_symlink.is_symlink():
                    target_symlink.unlink()
                if source_binary.exists():
                    target_symlink.symlink_to(source_binary)
                else:
                    target_symlink.write_text(
                        f'#!/bin/sh\nexec "{venv_dir}/bin/claw-compactor" "$@"\n', encoding="utf-8"
                    )
                    target_symlink.chmod(0o755)

        except Exception as exc:
            print(f"Warning: Virtual environment setup failed: {exc}")

        # Execution permissions
        if sys.platform != "win32":
            for sd in [HUB / "bin", HUB / "hooks"]:
                if sd.exists():
                    for p in sd.rglob("*"):
                        if p.is_file() and p.suffix in {".sh", ".py", ""}:
                            try:
                                p.chmod(p.stat().st_mode | 0o111)
                            except Exception:
                                pass

        # Verification
        verify_script = HUB / "docs" / "verify_stack.py"
        if verify_script.exists():
            print(f"Verifying deployment at {HUB}...")
            try:
                env = dict(
                    os.environ,
                    HUB=str(HUB),
                    SCROOGE_TOKEN_TELEMETRY_DATA_DIR=str(HUB / "token-telemetry"),
                    CODEX_TOKEN_TELEMETRY_DATA_DIR=str(HUB / "token-telemetry"),
                    CURSOR_TOKEN_TELEMETRY_DATA_DIR=str(HUB / "token-telemetry"),
                )
                res = subprocess.run(
                    [sys.executable, str(verify_script)], capture_output=True, text=True, env=env
                )
                print(res.stdout)
            except Exception as exc:
                print(f"Verification failed: {exc}")

    # 11. Optional Daemon Launch for serve_dashboard.py (outside the loop, single launch)
    print_header("Dashboard Service")
    run_db = prompt_input(
        "Would you like to start the S.C.R.O.O.G.E. dashboard in the background? (y/n)", default="y"
    )
    if run_db.lower().startswith("y") and hubs_to_install:
        first_hub = hubs_to_install[0]
        venv_dir = first_hub / "token-telemetry" / ".venv-desktop"
        pid_file = first_hub / "token-telemetry" / "dashboard.pid"
        log_file = first_hub / "token-telemetry" / "dashboard.log"

        # Stop existing dashboard daemon if running
        if pid_file.exists():
            try:
                old_pid = int(pid_file.read_text(encoding="utf-8").strip())
                print(f"Stopping existing dashboard process (PID {old_pid})...")
                os.kill(old_pid, 15)
                pid_file.unlink(missing_ok=True)
            except Exception:
                pass

        if sys.platform == "win32":
            print("Windows Background service start...")
            try:
                venv_python = venv_dir / "Scripts" / "python.exe"
                cmd = [str(venv_python), str(first_hub / "token-telemetry" / "serve_dashboard.py")]
                proc = subprocess.Popen(
                    cmd,
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS,
                    env=dict(
                        os.environ,
                        SCROOGE_TOKEN_TELEMETRY_DATA_DIR=str(first_hub / "token-telemetry"),
                        CURSOR_TOKEN_TELEMETRY_DATA_DIR=str(first_hub / "token-telemetry"),
                        CODEX_TOKEN_TELEMETRY_DATA_DIR=str(first_hub / "token-telemetry"),
                    ),
                )
                pid_file.write_text(str(proc.pid), encoding="utf-8")
                print("Dashboard started in background. Visit: http://127.0.0.1:8765/")
            except Exception as exc:
                print(f"Failed to start dashboard: {exc}")
        else:
            print("macOS/Linux Background daemon start...")
            try:
                venv_python = venv_dir / "bin" / "python"
                log_file.parent.mkdir(parents=True, exist_ok=True)
                log_fh = open(log_file, "a", encoding="utf-8")
                cmd = [str(venv_python), str(first_hub / "token-telemetry" / "serve_dashboard.py")]
                proc = subprocess.Popen(
                    cmd,
                    stdout=log_fh,
                    stderr=subprocess.STDOUT,
                    start_new_session=True,
                    env=dict(
                        os.environ,
                        SCROOGE_TOKEN_TELEMETRY_DATA_DIR=str(first_hub / "token-telemetry"),
                        CURSOR_TOKEN_TELEMETRY_DATA_DIR=str(first_hub / "token-telemetry"),
                        CODEX_TOKEN_TELEMETRY_DATA_DIR=str(first_hub / "token-telemetry"),
                    ),
                )
                pid_file.write_text(str(proc.pid), encoding="utf-8")
                print("Dashboard started in background. Visit: http://127.0.0.1:8765/")
            except Exception as exc:
                print(f"Failed to start dashboard: {exc}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
