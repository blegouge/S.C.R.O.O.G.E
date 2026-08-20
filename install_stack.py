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

# Repository root (where this script is located)
REPO_ROOT = Path(__file__).resolve().parent
HUB_FILES = REPO_ROOT / "hub_files"
CODEX_FILES = HUB_FILES / "codex"

from install_helpers import (
    append_codex_mcp_config,
    copy_tree_idempotent,
    deploy_token_telemetry_runtime,
    detect_target_name,
    load_env_file,
    merge_hook_lists,
    merge_hooks_claude,
    print_header,
    prompt_choice,
    prompt_input,
    prune_token_telemetry_runtime,
    save_env_file,
    transform_hooks_cursor_to_claude,
)


def find_uvx() -> Path | None:
    """Locate uvx on PATH or in common install dirs."""
    found = shutil.which("uvx")
    if found:
        return Path(found).absolute()
    names = ("uvx.exe", "uvx") if sys.platform == "win32" else ("uvx",)
    candidates = [
        Path.home() / ".local" / "bin",
        Path.home() / ".cargo" / "bin",
        Path("/opt/homebrew/bin"),
        Path("/usr/local/bin"),
    ]
    if sys.platform == "win32":
        local = os.environ.get("LOCALAPPDATA", "")
        if local:
            candidates.append(Path(local) / "Programs" / "uv")
    for directory in candidates:
        for name in names:
            path = directory / name
            if path.is_file():
                return path.absolute()
    return None


def ensure_uv_uvx() -> Path | None:
    """Idempotent: install uv (provides uvx) if missing, with user confirmation."""
    print_header("uv / uvx")
    existing = find_uvx()
    if existing:
        print(f"uvx already present: {existing}")
        return existing

    print("uv/uvx is required to launch the code-review-graph MCP server.")
    if sys.platform == "darwin" and shutil.which("brew"):
        method = "brew install uv"
    elif sys.platform == "win32" and shutil.which("winget"):
        method = "winget install -e --id astral-sh.uv"
    elif sys.platform == "win32":
        method = "PowerShell: irm https://astral.sh/uv/install.ps1 | iex"
    else:
        method = "curl -LsSf https://astral.sh/uv/install.sh | sh"
    print(f"Proposed install ({sys.platform}): {method}")

    answer = prompt_input("Install uv/uvx now? (y/n)", default="y")
    if not answer.lower().startswith("y"):
        print("Skipped uv/uvx install.")
        return None

    try:
        if sys.platform == "darwin" and shutil.which("brew"):
            subprocess.run(["brew", "install", "uv"], check=True)
        elif sys.platform == "win32" and shutil.which("winget"):
            subprocess.run(
                [
                    "winget",
                    "install",
                    "-e",
                    "--id",
                    "astral-sh.uv",
                    "--accept-package-agreements",
                    "--accept-source-agreements",
                ],
                check=True,
            )
        elif sys.platform == "win32":
            subprocess.run(
                "powershell -ExecutionPolicy ByPass -c "
                '"irm https://astral.sh/uv/install.ps1 | iex"',
                check=True,
                shell=True,
            )
        else:
            cmd = (
                "curl -LsSf https://astral.sh/uv/install.sh | sh"
                if shutil.which("curl")
                else "wget -qO- https://astral.sh/uv/install.sh | sh"
            )
            subprocess.run(cmd, check=True, shell=True)
    except (subprocess.CalledProcessError, OSError) as exc:
        print(f"Warning: uv/uvx install failed: {exc}")
        return None

    # Refresh PATH for this process (official installer uses ~/.local/bin)
    extras = [
        str(Path.home() / ".local" / "bin"),
        str(Path.home() / ".cargo" / "bin"),
        "/opt/homebrew/bin",
        "/usr/local/bin",
    ]
    os.environ["PATH"] = os.pathsep.join(extras + [os.environ.get("PATH", "")])
    uvx = find_uvx()
    if uvx:
        print(f"uvx installed at {uvx}")
    else:
        print("Warning: install finished but uvx not found — open a new terminal and re-run.")
    return uvx


def find_npx() -> Path | None:
    """Locate npx on PATH (absolute path required for IDE-launched MCP).

    Do not Path.resolve() through symlinks: npm's ``npx`` often links to
    ``npx-cli.js``, which is not a valid MCP ``command`` binary.
    """
    found = shutil.which("npx")
    if found:
        return Path(found).absolute()
    return None


def find_node_bin() -> Path | None:
    """Directory containing ``node`` (needed because npx shebang uses env node)."""
    found = shutil.which("node")
    if found:
        return Path(found).absolute().parent
    npx = find_npx()
    if npx is not None:
        sibling = npx.parent / ("node.exe" if sys.platform == "win32" else "node")
        if sibling.is_file():
            return npx.parent
    return None


def mcp_path_env(node_bin: Path | None) -> str:
    """PATH prefix so IDE-launched npx can find node."""
    parts: list[str] = []
    if node_bin is not None:
        parts.append(str(node_bin))
    parts.extend(
        [
            "/opt/homebrew/bin",
            "/usr/local/bin",
            "/usr/bin",
            "/bin",
        ]
    )
    # Dedupe preserving order
    seen: set[str] = set()
    out: list[str] = []
    for p in parts:
        if p not in seen:
            seen.add(p)
            out.append(p)
    return os.pathsep.join(out)


def ensure_mcp_git_tokens(secrets_file: Path) -> None:
    """Prompt for empty GitHub/GitLab tokens; idempotent if already set."""
    if not secrets_file.is_file():
        return
    data = load_env_file(secrets_file)
    changed = False

    print_header("MCP git host tokens")
    print(f"Secrets file: {secrets_file}")

    gh = (data.get("GITHUB_PERSONAL_ACCESS_TOKEN") or "").strip()
    if not gh:
        val = prompt_input(
            "GitHub personal access token (empty to skip)",
            default="",
        ).strip()
        if val:
            data["GITHUB_PERSONAL_ACCESS_TOKEN"] = val
            changed = True
            print("GitHub token saved.")
        else:
            print("GitHub token left empty (github MCP will stay unavailable).")
    else:
        print("GitHub token already set (skipping).")

    gl = (data.get("GITLAB_TOKEN") or "").strip()
    if not gl:
        val = prompt_input(
            "GitLab token (empty to skip)",
            default="",
        ).strip()
        if val:
            data["GITLAB_TOKEN"] = val
            changed = True
            print("GitLab token saved.")
        else:
            print("GitLab token left empty (gitlab MCP will stay unavailable).")
    else:
        print("GitLab token already set (skipping).")

    if changed:
        save_env_file(
            secrets_file,
            data,
            comment_header="# MCP secrets (managed by install_stack.py) — never commit",
        )
        try:
            secrets_file.chmod(0o600)
        except OSError:
            pass


def select_desktop_requirements(token_telemetry_dir: Path) -> Path:
    """Choose a requirements file compatible with the current platform.

    Lock files are platform-specific because GUI dependencies such as PyObjC
    are only valid on macOS. If a lock for the current platform is absent, fall
    back to the portable input requirements and let pip resolve local wheels.
    """
    req_txt = token_telemetry_dir / "requirements-desktop.txt"
    platform_lock_names = {
        "darwin": "requirements-desktop-macos.lock",
        "linux": "requirements-desktop-linux.lock",
        "win32": "requirements-desktop-windows.lock",
    }
    req_lock = token_telemetry_dir / platform_lock_names.get(sys.platform, "")
    if req_lock.is_file():
        return req_lock
    if req_txt.is_file():
        return req_txt
    return req_txt


def main() -> int:
    print_header("Token Optimization Stack - Installer")
    print(f"Source repository root: {REPO_ROOT}")

    # Load existing .env configs from the repository root
    repo_env_file = REPO_ROOT / ".env"
    repo_env = load_env_file(repo_env_file)

    # 1. Target Hub Directory Selection
    home = Path.home()
    possible_targets = [
        home / ".claude",
        home / ".gemini",
        home / ".gemini" / "antigravity",
        home / ".hermes",
        home / ".codex",
        home / ".cursor",
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
        if target_name == "claude":
            repo_env["CLAUDE_HOME"] = str(HUB)
            repo_env["CLAUDE_STATS_DIR"] = str(HUB / "token-telemetry")
        elif target_name == "gemini":
            repo_env["GEMINI_HOME"] = str(HUB)
            repo_env["GEMINI_STATS_DIR"] = str(HUB / "token-telemetry")
        elif target_name == "antigravity":
            repo_env["ANTIGRAVITY_HOME"] = str(HUB)
            repo_env["ANTIGRAVITY_STATS_DIR"] = str(HUB / "token-telemetry")
        elif target_name == "hermes":
            repo_env["HERMES_HOME"] = str(HUB)
            repo_env["HERMES_STATS_DIR"] = str(HUB / "token-telemetry")
        elif target_name == "codex":
            repo_env["CODEX_HOME"] = str(HUB)
            repo_env["CODEX_STATS_DIR"] = str(HUB / "token-telemetry")
        elif target_name == "cursor":
            repo_env["CURSOR_HOME"] = str(HUB)
            repo_env["CURSOR_STATS_DIR"] = str(HUB / "token-telemetry")

    save_env_file(
        repo_env_file,
        repo_env,
        comment_header="# S.C.R.O.O.G.E. Config (Autogenerated / Updated by install_stack.py)",
    )
    print(f"Updated repository environment configuration at {repo_env_file}")

    # Ensure uv/uvx for code-review-graph MCP (idempotent, confirmed)
    uvx_path = ensure_uv_uvx()
    if uvx_path is None:
        uvx_path = (
            Path.home() / ".local" / "bin" / ("uvx.exe" if sys.platform == "win32" else "uvx")
        )

    npx_path = find_npx()
    if npx_path is None:
        print("Warning: npx not found on PATH — shell-executor / code-explorer / git MCP may fail.")
        npx_path = Path("npx")
    else:
        print(f"npx resolved at {npx_path}")

    node_bin = find_node_bin()
    if node_bin is None:
        print("Warning: node bin dir not found — npx MCP servers need node on PATH.")
        node_bin = Path("/usr/bin")
    else:
        print(f"node bin dir: {node_bin}")
    mcp_path_value = mcp_path_env(node_bin)

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

        if secrets_file.exists():
            ensure_mcp_git_tokens(secrets_file)

        # Determine target name/type for replacements
        target_name = detect_target_name(HUB)

        def rewrite_config_content(content: str) -> str:
            # Replace template placeholders
            content = content.replace("{{HUB}}", str(HUB))
            content = content.replace("{{CODEBASE_ROOT}}", str(codebase_root_path))
            content = content.replace("{{HOME}}", str(home))
            content = content.replace("{{UVX}}", str(uvx_path))
            content = content.replace("{{NPX}}", str(npx_path))
            content = content.replace("{{NODE_BIN}}", str(node_bin))

            # Replace home folders or reference hub roots (legacy/fallbacks)
            content = content.replace("~/.cursor", str(HUB))
            content = content.replace("~/.gemini/antigravity", str(HUB))
            content = content.replace("~/.codex", str(HUB))

            # Context-sensitive replacements for IDE/Agent name
            if target_name == "claude":
                content = content.replace("Antigravity", "Claude Code")
                content = content.replace("antigravity-ide", "claude")
                content = content.replace("antigravity", "claude")
                content = content.replace("Cursor", "Claude Code")
                content = content.replace("cursor", "claude")
            elif target_name == "gemini":
                content = content.replace("Antigravity", "Gemini CLI")
                content = content.replace("antigravity-ide", "gemini")
                content = content.replace("antigravity", "gemini")
                content = content.replace("Cursor", "Gemini CLI")
                content = content.replace("cursor", "gemini")
            elif target_name == "antigravity":
                content = content.replace("Cursor", "Antigravity")
                content = content.replace("cursor", "antigravity")
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
            elif target_name == "cursor":
                content = content.replace("Antigravity", "Cursor")
                content = content.replace("antigravity-ide", "cursor")
                content = content.replace("antigravity", "cursor")
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

            # Repair absolute uvx/npx paths + PATH (node) on re-runs.
            # Cursor launches MCP with a minimal PATH; npx shebang needs node.
            if mcp_out.is_file():
                try:
                    mcp_data = json.loads(mcp_out.read_text(encoding="utf-8"))
                    servers = mcp_data.get("mcpServers", {})
                    repaired = False
                    path_value = mcp_path_value
                    for name, srv in servers.items():
                        if not isinstance(srv, dict):
                            continue
                        cmd = srv.get("command")
                        args = srv.get("args")
                        if (
                            name == "code-review-graph"
                            and isinstance(uvx_path, Path)
                            and uvx_path.is_file()
                            and cmd != str(uvx_path)
                        ):
                            srv["command"] = str(uvx_path)
                            repaired = True
                        uses_npx = name in {"shell-executor", "code-explorer", "github", "gitlab"}
                        if isinstance(npx_path, Path) and npx_path.is_file():
                            if cmd in ("npx", "npx.cmd") or (
                                isinstance(cmd, str) and cmd.endswith("/npx")
                            ):
                                uses_npx = True
                                if cmd != str(npx_path):
                                    srv["command"] = str(npx_path)
                                    repaired = True
                            if isinstance(args, list):
                                new_args = [
                                    str(npx_path) if a in ("npx", "npx.cmd") else a for a in args
                                ]
                                if new_args != args:
                                    srv["args"] = new_args
                                    repaired = True
                                    uses_npx = True
                        if uses_npx:
                            env = srv.get("env")
                            if not isinstance(env, dict):
                                env = {}
                                srv["env"] = env
                            if env.get("PATH") != path_value:
                                env["PATH"] = path_value
                                repaired = True
                            if isinstance(node_bin, Path) and node_bin.is_dir():
                                if env.get("MCP_NODE_BIN") != str(node_bin):
                                    env["MCP_NODE_BIN"] = str(node_bin)
                                    repaired = True
                    if repaired:
                        mcp_out.write_text(json.dumps(mcp_data, indent=2), encoding="utf-8")
                        print(f"Repaired absolute MCP binary paths in {mcp_out}")
                except Exception as exc:
                    print(f"Warning: could not repair MCP paths in mcp.json: {exc}")

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
        req_file = select_desktop_requirements(HUB / "token-telemetry")

        print(f"Setting up Python venv at {venv_dir}...")
        try:
            python_bin = sys.executable
            if sys.platform != "win32" and shutil.which("python3.12"):
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
