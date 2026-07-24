<p align="center">
  <img src="docs/fr/assets/icon.jpg" alt="S.C.R.O.O.G.E. Logo" width="160" style="border-radius: 20px; box-shadow: 0 4px 20px rgba(0,0,0,0.3);" />
</p>

# 🚀 S.C.R.O.O.G.E. - Context Optimization & Telemetry Stack

> **Local Proxy Metrics & Intelligent Prompt Compression for Next-Gen IDEs**

[![Python 3.12+](https://img.shields.io/badge/Python-3.12+-blue.svg?logo=python&logoColor=white)](https://python.org)
[![Platform: macOS | Linux | Windows](https://img.shields.io/badge/Platform-macOS%20%7C%20Linux%20%7C%20Windows-lightgrey.svg)](#)
[![Supported IDEs: Cursor | Antigravity | Claude Code | Gemini | Codex](https://img.shields.io/badge/IDEs-Cursor%20%7C%20Antigravity%20%7C%20ClaudeCode%20%7C%20Gemini%20%7C%20Codex-purple.svg)](#)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

S.C.R.O.O.G.E. (Smart Context Reducer & Optimized Observability Governance Engine) is a local developer proxy metrics and optimization suite built to measure, visualize, and drastically reduce the cost of running LLM-assisted programming workflows. It automatically intercepts agent requests, applies aggressive compression strategies, and monitors workspace compliance in real-time.

---

## 📸 Dashboard Preview

### 📊 Main Metrics & Savings
The dashboard offers a dark neon "terminal-style" theme with KPI cards, real-time token histograms, and a counterfactual chart displaying observed usage versus estimated consumption without optimizations.
![Main Dashboard View](docs/fr/assets/dashboard_main.png)

---

## ✨ Key Features

1. **📊 Local S.C.R.O.O.G.E. Telemetry**
   - Logs metrics asynchronously to a local, append-only `events.jsonl` file, and syncs them incrementally into a central SQLite database (`telemetry.db`).
   - Query endpoints utilize the indexed SQLite database for fast O(log N) searches.
   - Compiles into a native **macOS Desktop App** (`.app` bundle via PyInstaller) for a standalone window dashboard.

2. **🗜️ Context Compression & Optimizations**
   - **RTK Gain**: Integrates with shell command savings (saves up to 98% on command runs, estimated).
   - **Diff-Only Protocol**: Applies SEARCH/REPLACE delta patching to avoid rewriting large source files, saving up to 95% of output tokens (estimated).
   - **Claw Compactor & LLMLingua**: Reduces dynamic context size by pruning low-information tokens before sending payloads.
   - **Headroom local engines**: `SmartCrusher` (structural pruning) and `CCR` (Compress-Cache-Retrieve) for large logs/blocks.

3. **🔄 Adaptive Context Routing**
   - Assembles requests deterministically:
     1. `BLOCK_1`: Static global rules, cursor rules, and active skills.
     2. `BLOCK_1B`: Token budget guardrails.
     3. `BLOCK_2`: Git & Workspace state.
     4. `BLOCK_3`: Compacted dynamic message history.
     5. `BLOCK_4`: Latest query.
   - Compacts history above the configured thresholds (code defaults: 8 messages / 3000 tokens; the shipped `compression.env` raises them to 10 / 4000). See [ADAPTIVE_CONTEXT_ROUTING.md](ADAPTIVE_CONTEXT_ROUTING.md).

4. **⚡ Git Pre-flight Cache**
   - Computes a signature based on `git branch + HEAD SHA + modified files`.
   - Reuses compacted workspace states instantly, bypassing redundant LLM summarization.

5. **🛡️ Compliance & Governance**
   - Blocks subagents if the task brief is invalid or lacks required parameters.
   - Validates that the agent outputs a structured consumption report at the end of each turn.
   - All hooks utilize a fail-safe execution wrapper to prevent any script crashes from blocking editor operations.

---

## 📂 Repository Structure

The Python core lives under `src/` (packaged, unit-tested), the UI under `dashboard/`, and everything deployed into an agent/IDE hub (`~/.cursor`, `~/.codex`, `~/.gemini/antigravity`, …) lives under `hub_files/`.

| Path | Description |
|---|---|
| 🛠️ [install_stack.py](install_stack.py) | Interactive, idempotent, and automated setup script. |
| 📁 [src/telemetry/](src/telemetry/) | Telemetry core: SQLite manager ([telemetry_db.py](src/telemetry/telemetry_db.py)), path/provider resolution ([telemetry_paths.py](src/telemetry/telemetry_paths.py), [providers_config.py](src/telemetry/providers_config.py)), config ([telemetry_config.py](src/telemetry/telemetry_config.py)), KPI aggregation ([telemetry_metrics.py](src/telemetry/telemetry_metrics.py)), measured-vs-modeled taxonomy ([measurement_source.py](src/telemetry/measurement_source.py)), RTK binary resolver ([rtk_resolver.py](src/telemetry/rtk_resolver.py)), shared helpers ([telemetry_common.py](src/telemetry/telemetry_common.py)). |
| 📁 [src/compaction/](src/compaction/) | Compression engines: LLMLingua ([token_compactor.py](src/compaction/token_compactor.py)), Claw adapter ([claw_compactor_adapter.py](src/compaction/claw_compactor_adapter.py)), Headroom adapter ([headroom_adapter.py](src/compaction/headroom_adapter.py)), SmartCrusher ([smart_crusher.py](src/compaction/smart_crusher.py)), CCR cache ([ccr_manager.py](src/compaction/ccr_manager.py)). |
| 📁 [src/bridge/](src/bridge/) | External log ingestion into telemetry ([hermes_telemetry_bridge.py](src/bridge/hermes_telemetry_bridge.py)). |
| 📁 [dashboard/](dashboard/) | Web SPA ([dashboard.html](dashboard/dashboard.html), JS/CSS), HTTP backend ([serve_dashboard.py](dashboard/serve_dashboard.py)), and native window loader ([dashboard_app.py](dashboard/dashboard_app.py)). |
| 📁 [cli/](cli/) | CLI reporting utilities ([report.py](cli/report.py)). |
| 📁 [hub_files/](hub_files/) | Agent/IDE integration layer deployed to the hub: `hooks/` (telemetry, Diff-Only, RTK, semantic compression, compliance), `providers/` (per-IDE detection), `rules/` (`*.mdc`), `skills/`, `src/utils/` (adaptive context manager, diff applier, guardrails, summarizers + their unit tests), and `bin/` (helper scripts). |
| 📁 [docs/](docs/) | Documentation and post-install verifier ([verify_stack.py](docs/verify_stack.py)). |
| 📁 [examples/](examples/) | Integration samples: compression middleware and flash summarizer smoke test. |
| 📁 [native_app/](native_app/) | PyInstaller spec ([SCROOGE.spec](native_app/SCROOGE.spec)) for the macOS `.app` bundle. |
| 📦 [build_macos_app.sh](build_macos_app.sh) | Builds `dist/SCROOGE.app` (PyInstaller + ad-hoc signature). |

---

## 🚀 Installation Guide

Run the automated installer from the repository root:

```bash
python3 install_stack.py
```

### What the installer does:
1. **Target Hub Selection**: Auto-detects and installs configuration templates to `~/.cursor`, `~/.gemini/antigravity`, `~/.codex`, or custom locations.
2. **Codebase Directory**: Asks for your active workspace path to configure code-explorer.
3. **Compression Backend**: Configures whether to use `claw`, `headroom`, `both`, or disable compaction.
4. **Interactive Secret Setup**: Collects your API tokens once (Grafana, GitHub, MySQL, etc.) and writes them to a secure `.env` file (`chmod 600`).
5. **Python Virtual Environment**: Creates a dedicated `.venv-desktop` environment and installs dependencies.
6. **Rule/Skill Normalization**: Rewrites references to fit the target IDE/agent, including Codex-specific hooks and MCP config (Cursor, Antigravity, Claude Code, or Codex).
7. **Verification**: Executes [docs/verify_stack.py](docs/verify_stack.py) to validate all components.
8. **Daemon Launch**: Offers to automatically start the dashboard daemon in the background on port `8765`.

Dependency locks are platform-specific. The installer uses `requirements-desktop-macos.lock`, `requirements-desktop-linux.lock`, or `requirements-desktop-windows.lock` when available, and falls back to the portable `requirements-desktop.txt` otherwise. See [docs/DEPENDENCY_LOCKS.md](docs/DEPENDENCY_LOCKS.md).

---

## ⚙️ Configuration File Overview

### 1. `compression.env`
Defines parameters and thresholds for context compression (see [hub_files/compression.env.example](hub_files/compression.env.example)):
```ini
# Token optimization context compression configuration
COMPRESSION_BACKEND=claw
# deny = block invalid briefs, warn = log only, off = skip validation
TASK_BRIEF_ENFORCE=warn
LLMLINGUA_HOOK_RATE=0.5
LLMLINGUA_HOOK_MIN_CHARS=2500
ADAPTIVE_CTX_TOKEN_THRESHOLD=4000
ADAPTIVE_CTX_MESSAGE_THRESHOLD=10
ADAPTIVE_CTX_STRUCTURE_MIN_INPUT_TOKENS=2500
CCR_ENABLED=1
CCR_THRESHOLD_CHARS=4000
SMART_CRUSHER_N=10
SMART_CRUSHER_M=10
```

### 2. `mcp.secrets.env`
Stores private credentials loaded by the MCP wrapper scripts:
```ini
GITHUB_PERSONAL_ACCESS_TOKEN=ghp_...
GRAFANA_API_TOKEN=glsa_...
MYSQL_PASSWORD=...
```

### 3. `hooks.json` & `mcp.json`
Located in your IDE/agent hub folder (e.g. `~/.cursor/` or `~/.codex/`), they define the active hooks and register the custom local MCP servers. Codex uses `~/.codex/hooks.json`, `~/.codex/config.toml`, `~/.codex/AGENTS.md`, and user skills under `~/.agents/skills`.

---

## 🖥️ Usage

### Terminal Report
Run the report CLI (from the repository root) to see a summary of your session consumption:
```bash
python3 cli/report.py
```

### Start the Dashboard Server
If you chose not to start it during installation, run:
```bash
python3 dashboard/serve_dashboard.py
# Open http://127.0.0.1:8765/
```

### Build a Standalone macOS App (`.app`)
To generate a double-clickable macOS bundle in your Dock:
```bash
./build_macos_app.sh
```
This builds `dist/SCROOGE.app` using PyInstaller, embeds the logo, and applies an ad-hoc signature.

---

## 🔒 Privacy & Rotation
All agent payloads, which may contain file paths, queries, and code outputs, are logged strictly on your local machine in `events.jsonl`.
Keep this file private, and rotate/delete it whenever necessary.
