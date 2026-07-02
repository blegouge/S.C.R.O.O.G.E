#!/usr/bin/env python3
"""install_stack.py - Automated, interactive, and idempotent installation of the Token Optimization Stack.

This script runs with the standard library only. It copies the reference files from
hub_files/ to all selected target HUBs (~/.cursor or ~/.gemini/antigravity), prompts the user
for required MCP tokens once, rewrites configuration paths, updates rule/skill references
dynamically for the target IDE, sets up the Python venv, and runs the sanity check verification.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

# Repository root (where this script is located)
REPO_ROOT = Path(__file__).resolve().parent
HUB_FILES = REPO_ROOT / "hub_files"

# =============================================================================
# Claude Code hooks format transformation
# Cursor/Gemini use hooks.json, Claude Code uses settings.json with different structure
# =============================================================================

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
    # These events are NOT supported by Claude Code (will be skipped):
    # "afterAgentResponse", "afterFileEdit", "afterTabFileEdit", "beforeShellExecution"
}

# Tool/matcher name mapping: Cursor -> Claude Code
CLAUDE_TOOL_MAPPING = {
    "Shell": "Bash",
    "shell": "Bash",
}


def transform_hooks_cursor_to_claude(hooks_data: dict[str, Any]) -> dict[str, Any]:
    """Transform Cursor/Gemini hooks.json format to Claude Code settings.json format.

    Cursor format:
        {"version": 1, "hooks": {"preToolUse": [{"command": "...", "matcher": "Shell"}]}}

    Claude Code format:
        {"hooks": {"PreToolUse": [{"matcher": "Bash", "hooks": [{"type": "command", "command": "..."}]}]}}
    """
    result: dict[str, Any] = {"hooks": {}}
    source_hooks = hooks_data.get("hooks", {})

    for event_name, items in source_hooks.items():
        # Map event name (preToolUse -> PreToolUse)
        claude_event = CLAUDE_EVENT_MAPPING.get(event_name)
        if claude_event is None:
            # Fallback: capitalize first letter
            claude_event = event_name[0].upper() + event_name[1:]

        # Skip events not supported by Claude Code
        if claude_event not in CLAUDE_SUPPORTED_EVENTS:
            continue

        # Group hooks by matcher
        by_matcher: dict[str, list[dict[str, str]]] = defaultdict(list)

        for item in items:
            matcher = item.get("matcher", "*")
            # Map tool names (Shell -> Bash)
            matcher = CLAUDE_TOOL_MAPPING.get(matcher, matcher)
            # Build Claude Code hook entry
            hook_entry = {"type": "command", "command": item["command"]}
            by_matcher[matcher].append(hook_entry)

        # Build the grouped structure
        result["hooks"][claude_event] = [
            {"matcher": matcher, "hooks": hooks_list}
            for matcher, hooks_list in by_matcher.items()
        ]

    return result


def merge_hooks_claude(existing: dict[str, Any], new_hooks: dict[str, Any]) -> dict[str, Any]:
    """Merge new hooks into existing Claude Code settings.json without duplicates.

    Preserves existing hooks and adds new ones (matched by command path).
    """
    result: dict[str, Any] = {"hooks": {}}

    # Copy existing hooks
    for event, groups in existing.get("hooks", {}).items():
        result["hooks"][event] = [
            {"matcher": g["matcher"], "hooks": list(g.get("hooks", []))}
            for g in groups
        ]

    # Merge new hooks
    for event, groups in new_hooks.get("hooks", {}).items():
        if event not in result["hooks"]:
            result["hooks"][event] = []

        existing_groups = result["hooks"][event]

        for new_group in groups:
            new_matcher = new_group["matcher"]

            # Find existing group with same matcher
            target_group = None
            for eg in existing_groups:
                if eg["matcher"] == new_matcher:
                    target_group = eg
                    break

            if target_group is None:
                # Add new matcher group
                existing_groups.append({
                    "matcher": new_matcher,
                    "hooks": list(new_group.get("hooks", []))
                })
            else:
                # Merge hooks into existing group (avoid duplicates by command)
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


def copy_tree_idempotent(src: Path, dst: Path, ignore=None, overwrite: bool = True) -> None:
    """Copy directory src to dst, creating parent directories and overwriting existing files (if overwrite is True).
    Prevents infinite recursion if dst is inside src.
    """
    if not src.exists():
        return
    src_abs = src.resolve()
    dst_abs = dst.resolve()
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
        if s.is_dir():
            copy_tree_idempotent(s, d, ignore, overwrite=overwrite)
        else:
            if not overwrite and d.exists():
                continue
            try:
                shutil.copy2(s, d)
            except shutil.SameFileError:
                pass


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
        home / ".gemini",
    ]

    detected_targets = [t for t in possible_targets if t.exists()]
    hubs_to_install: list[Path] = []

    if not detected_targets:
        hub_choice = prompt_input(
            "No active AI directories detected. Enter custom target directory",
            default=str(possible_targets[0])
        )
        hubs_to_install.append(Path(os.path.expanduser(hub_choice)).resolve())
    else:
        print("\nDetected AI directories:")
        for idx, t in enumerate(detected_targets, 1):
            print(f"  [{idx}] {t}")
            
        choices = ["All detected directories"] + [str(t) for t in detected_targets] + ["Custom directory"]
        selection = prompt_choice("Choose installation target:", choices, default="All detected directories")
        
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
        default=default_codebase
    )
    codebase_root_path = Path(os.path.expanduser(codebase_root)).resolve()

    # 3. Compression Backend selection
    current_backend = repo_env.get("COMPRESSION_BACKEND", "claw")
    chosen_backend = prompt_choice(
        "Choose the context compression backend:",
        ["claw", "headroom", "both", "off"],
        default=current_backend
    )

    # 4. Configure interactive secrets (mcp.secrets.env) - Ask once
    print_header("MCP Secret Tokens Setup")
    # Collect existing secrets from any possible target directory to use as defaults
    existing_secrets = {}
    for pt in possible_targets:
        target_secrets_file = pt / "mcp.secrets.env"
        if target_secrets_file.exists():
            existing_secrets.update(load_env_file(target_secrets_file))

    secret_vars = [
        ("GRAFANA_API_TOKEN", "Grafana API Token"),
        ("ES_USERNAME", "Elasticsearch catalog Username"),
        ("ES_PASSWORD", "Elasticsearch catalog Password"),
        ("MYSQL_PASSWORD", "MySQL Database Password"),
        ("DD_API_KEY", "Datadog API Key"),
        ("DD_APP_KEY", "Datadog App Key"),
        ("GITHUB_PERSONAL_ACCESS_TOKEN", "GitHub Personal Access Token"),
        ("GITLAB_TOKEN", "GitLab Personal Token"),
    ]

    new_secrets = {}
    print("Please enter the credentials for each integration (press Enter to skip or keep existing):")
    for var_name, description in secret_vars:
        prev_val = existing_secrets.get(var_name, "")
        masked_prev = f"{prev_val[:4]}...{prev_val[-4:]}" if len(prev_val) > 8 else prev_val
        prompt_desc = f"{description} ({var_name})"
        
        user_val = input(f"  {prompt_desc} [{masked_prev if prev_val else 'empty'}]: ").strip()
        if not user_val:
            new_secrets[var_name] = prev_val
        else:
            new_secrets[var_name] = user_val

    # Persist configurations back to the repository's `.env`
    repo_env["CODEBASE_ROOT"] = codebase_root
    repo_env["COMPRESSION_BACKEND"] = chosen_backend
    
    # Save target homes & stats directories in repo's .env
    for HUB in hubs_to_install:
        hub_str = str(HUB).lower()
        if "cursor" in hub_str:
            repo_env["CURSOR_HOME"] = str(HUB)
            repo_env["CURSOR_STATS_DIR"] = str(HUB / "token-telemetry")
        elif "antigravity" in hub_str:
            repo_env["ANTIGRAVITY_HOME"] = str(HUB)
            repo_env["GEMINI_STATS_DIR"] = str(HUB / "token-telemetry")
        elif "claude" in hub_str:
            repo_env["CLAUDE_HOME"] = str(HUB)
            repo_env["CLAUDE_STATS_DIR"] = str(HUB / "token-telemetry")
        elif "hermes" in hub_str:
            repo_env["HERMES_HOME"] = str(HUB)
            repo_env["HERMES_STATS_DIR"] = str(HUB / "token-telemetry")
        elif "gemini" in hub_str:
            repo_env["GEMINI_HOME"] = str(HUB)
            repo_env["GEMINI_STATS_DIR"] = str(HUB / "token-telemetry")

    save_env_file(
        repo_env_file,
        repo_env,
        comment_header="# S.C.R.O.O.G.E. Config (Autogenerated / Updated by install_stack.py)"
    )
    print(f"Updated repository environment configuration at {repo_env_file}")

    # Loop to install on each target HUB
    for HUB in hubs_to_install:
        print_header(f"Deploying Stack to Target: {HUB}")

        # Create folders
        folders = ["bin", "hooks", "rules", "skills", "src", "projects", "token-telemetry"]
        for folder in folders:
            (HUB / folder).mkdir(parents=True, exist_ok=True)

        # Copy Reference Hub Components
        print("Copying hub files from repository templates...")
        for folder in ["bin", "hooks", "rules", "skills", "src"]:
            overwrite = False if folder == "skills" else True
            copy_tree_idempotent(HUB_FILES / folder, HUB / folder, ignore=["__pycache__"], overwrite=overwrite)

        # Copy docs from the repository root
        copy_tree_idempotent(REPO_ROOT / "docs", HUB / "docs")

        if (HUB_FILES / "AGENT.md").exists():
            shutil.copy2(HUB_FILES / "AGENT.md", HUB / "AGENT.md")

        # Copy current telemetry repository contents to <HUB>/token-telemetry
        print("Deploying local S.C.R.O.O.G.E. files...")
        ignore_patterns = {".git", ".venv-build", ".venv-desktop", "build", "dist", "hub_files"}
        copy_tree_idempotent(REPO_ROOT, HUB / "token-telemetry", ignore=ignore_patterns)

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
            comment_header="# Token optimization context compression configuration"
        )

        # Write secrets to target hub
        secrets_file = HUB / "mcp.secrets.env"
        save_env_file(
            secrets_file,
            new_secrets,
            comment_header="# Loaded by bin/mcp-env-exec.sh before starting MCP servers"
        )
        try:
            secrets_file.chmod(0o600)
            print(f"Secured secrets file at {secrets_file}")
        except Exception as exc:
            print(f"Warning: Failed to set permissions on secrets file: {exc}")

        # Determine target name/type for replacements
        target_name = "antigravity"
        hub_str = str(HUB).lower()
        if "cursor" in hub_str:
            target_name = "cursor"
        elif "antigravity" in hub_str:
            target_name = "antigravity"
        elif "claude" in hub_str:
            target_name = "claude"
        elif "hermes" in hub_str:
            target_name = "hermes"
        elif "gemini" in hub_str:
            target_name = "gemini"

        def rewrite_config_content(content: str) -> str:
            # Replace template placeholders
            content = content.replace("{{HUB}}", str(HUB))
            content = content.replace("{{CODEBASE_ROOT}}", str(codebase_root_path))
            content = content.replace("{{HOME}}", str(home))

            # Replace home folders or reference hub roots (legacy/fallbacks)
            content = content.replace("/Users/blegouge/.gemini/antigravity", str(HUB))
            content = content.replace("/Users/blegouge/.cursor", str(HUB))
            content = content.replace("~/.cursor", str(HUB))
            content = content.replace("~/.gemini/antigravity", str(HUB))
            content = content.replace("/Users/blegouge/www", str(codebase_root_path))
            content = content.replace("/Users/blegouge", str(home))
            
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

        # 2) hooks.json (Cursor/Gemini) or settings.json (Claude Code)
        hooks_tpl = HUB_FILES / "hooks.json"
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
                        # We match a hook by its 'command' property, or check if the exact dict matches.
                        for h_item in hook_list:
                            is_present = False
                            h_cmd = h_item.get("command")
                            for ext_item in existing_list:
                                if ext_item == h_item:
                                    is_present = True
                                    break
                                if h_cmd and ext_item.get("command") == h_cmd:
                                    is_present = True
                                    break
                            if not is_present:
                                existing_list.append(h_item)
                                added_count += 1

                    if added_count > 0:
                        print(f"Added {added_count} new hooks to {hooks_out}.")
                    else:
                        print(f"All hooks from template already present in {hooks_out}.")

                    hooks_out.write_text(json.dumps(out_data, indent=2), encoding="utf-8")
                else:
                    hooks_out.write_text(json.dumps(tpl_data, indent=2), encoding="utf-8")
                    print(f"Generated {hooks_out}")

        # Process rules and skills to dynamically rewrite references to Cursor vs Antigravity
        print("Normalizing rule and skill naming references for target IDE...")
        for root_dir in [HUB / "rules", HUB / "skills", HUB / "docs"]:
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
        req_file = HUB / "token-telemetry" / "requirements-desktop.txt"

        print(f"Setting up Python venv at {venv_dir}...")
        try:
            python_bin = "python3"
            if shutil.which("python3.12"):
                python_bin = "python3.12"
            
            subprocess.run([python_bin, "-m", "venv", str(venv_dir)], check=True, stdout=subprocess.DEVNULL)
            print("Virtual environment created.")

            if sys.platform == "win32":
                venv_python = venv_dir / "Scripts" / "python.exe"
            else:
                venv_python = venv_dir / "bin" / "python"

            subprocess.run([str(venv_python), "-m", "pip", "install", "--upgrade", "pip"], check=True, stdout=subprocess.DEVNULL)

            if req_file.exists():
                print(f"Installing dependencies from {req_file} (this might take a few moments)...")
                subprocess.run([str(venv_python), "-m", "pip", "install", "-r", str(req_file)], check=True, stdout=subprocess.DEVNULL)
                print("Dependencies successfully installed.")

            # Create claw-compactor global symlink or wrapper
            claw_bin_dir = HUB / "bin"
            claw_bin_dir.mkdir(parents=True, exist_ok=True)
            
            if sys.platform == "win32":
                wrapper = claw_bin_dir / "claw-compactor.cmd"
                wrapper.write_text(
                    f'@echo off\n"{venv_dir}\\Scripts\\claw-compactor.exe" %*\n',
                    encoding="ascii"
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
                        f'#!/bin/sh\nexec "{venv_dir}/bin/claw-compactor" "$@"\n',
                        encoding="utf-8"
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
                env = dict(os.environ, HUB=str(HUB), CURSOR_TOKEN_TELEMETRY_DATA_DIR=str(HUB / "token-telemetry"))
                res = subprocess.run([sys.executable, str(verify_script)], capture_output=True, text=True, env=env)
                print(res.stdout)
            except Exception as exc:
                print(f"Verification failed: {exc}")

    # 11. Optional Daemon Launch for serve_dashboard.py (outside the loop, single launch)
    print_header("Dashboard Service")
    run_db = prompt_input("Would you like to start the S.C.R.O.O.G.E. dashboard in the background? (y/n)", default="y")
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
                subprocess.Popen(
                    cmd,
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS,
                    env=dict(os.environ, CURSOR_TOKEN_TELEMETRY_DATA_DIR=str(first_hub / "token-telemetry"))
                )
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
                subprocess.Popen(
                    cmd,
                    stdout=log_fh,
                    stderr=subprocess.STDOUT,
                    start_new_session=True,
                    env=dict(os.environ, CURSOR_TOKEN_TELEMETRY_DATA_DIR=str(first_hub / "token-telemetry"))
                )
                print("Dashboard started in background. Visit: http://127.0.0.1:8765/")
            except Exception as exc:
                print(f"Failed to start dashboard: {exc}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
