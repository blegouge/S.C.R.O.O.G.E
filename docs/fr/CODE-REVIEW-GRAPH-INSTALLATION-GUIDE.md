# Code Review Graph — Installation Guide (Antigravity, global mode)

> Structure inspired by [RTK - Installation Guide](https://voyageprive.atlassian.net/wiki/spaces/companydepartment/pages/2444099649/RTK+-+Installation+Guide) (VPG Confluence).
> Upstream project: [tirth8205/code-review-graph](https://github.com/tirth8205/code-review-graph).

---

## What is Code Review Graph and why use it?

**Code Review Graph** (CRG) is a local tool that builds a **knowledge graph** of your repository (files, symbols, calls, dependencies) and exposes that graph to the assistant via **CLI** and **MCP**.

Instead of reading dozens of files at random for a review or refactor, the agent queries the graph (`detect-changes`, impact, callers, related tests) and reads only the **high-risk area**.

### Why it is useful for us

- **Fewer exploration tokens**: graph routing avoids broad repo scans (roughly 40–70% fewer file reads on cross-cutting tasks, depending on repo size).
- **More reliable reviews and impact analysis**: pre-merge impact checks, multi-module debugging, legacy mapping.
- **Complements RTK**: RTK compresses **Shell output**; CRG reduces the need to **read large amounts of code** — both stack together.

### Example: before / after

**Before CRG** — the agent chains `grep`, `find`, and partial reads across folders to guess the impact of a change.

**After CRG** — one targeted command:

```bash
code-review-graph detect-changes
```

→ impacted files, callers, tests, and dependency chains; file reads limited to that list.

---

## Prerequisites

| Prerequisite | Required for | Details |
|--------------|--------------|---------|
| OS | everything | macOS or Linux (guide tested on macOS) |
| Git | graph | Source repo with `.git` |
| Python 3.10+ | CLI / MCP | Base for `pipx` or `uv` |
| **`uv` + `uvx`** | **MCP (default VPG config)** | Antigravity runs `uvx code-review-graph serve` — **without `uvx` on PATH, the MCP server will not start** |
| `code-review-graph` (CLI) | CLI + pipx MCP variant | Installed via `pipx` or `uv tool`; separate from `uvx` as the server launcher |
| Antigravity | MCP | Access to **Settings → Tools & MCP** |

> **Two binaries, two roles**
> - **`code-review-graph`**: manual commands / hooks (`build`, `status`, `detect-changes`).
> - **`uvx`**: **launcher** Antigravity uses to start the **MCP server** (`uvx code-review-graph serve`). Having the pipx CLI alone is not enough if `mcp.json` points at `uvx` and `uv` is not installed.

---

## Step 1 — Install the CLI

### macOS (recommended)

```bash
pipx install code-review-graph
pipx ensurepath
```

Reload your shell or open a new terminal, then:

```bash
code-review-graph --version
```

Expected version: **2.x** (e.g. `code-review-graph 2.3.5` or newer).

### Alternative (without pipx)

```bash
uv tool install code-review-graph
```

### Coder / restricted environment

```bash
pip install --user code-review-graph
export PATH="$HOME/.local/bin:$PATH"
code-review-graph --version
```

---

## Step 1b — Install `uv` / `uvx` (required for the VPG MCP)

The recommended MCP config below uses **`"command": "uvx"`**. Antigravity literally runs `uvx code-review-graph serve` when starting the server. If `uvx` is missing, the MCP status stays in error or the server does not appear — **even if** `code-review-graph --version` already works in your terminal via pipx.

### macOS

```bash
brew install uv
```

### Coder / install script

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Validate before configuring MCP

```bash
which uvx
uvx --version
uvx code-review-graph --version
```

All three commands must succeed. The last one may download CRG on first run (`uv` cache) — that is expected.

---

## Step 2 — **Global** installation for Antigravity

> **Important**: `code-review-graph install --platform antigravity` writes by default to **`{project}/.antigravity/mcp.json`**, not the global user config. For the MCP in **all** Antigravity workspaces, configure **`~/.gemini/antigravity/mcp.json`**.

### 2.1 — Global MCP server

Edit **`~/.gemini/antigravity/mcp.json`** and add (or merge) the following entry under `mcpServers`.

#### Default VPG config (requires `uvx` — Step 1b)

```json
"code-review-graph": {
  "command": "uvx",
  "args": [
    "code-review-graph",
    "serve"
  ],
  "type": "stdio"
}
```

| Field | Role |
|-------|------|
| `command: "uvx"` | **uv** binary — must be on Antigravity’s `PATH` (not only your interactive terminal) |
| `args[0]: "code-review-graph"` | PyPI package launched by uvx |
| `args[1]: "serve"` | MCP stdio server mode |

#### Variant without `uvx` (pipx / `~/.local/bin` only)

If you **cannot** install `uv` (proxy, machine policy), use an explicit path to the CLI:

```json
"code-review-graph": {
  "command": "/Users/<you>/.local/bin/code-review-graph",
  "args": ["serve"],
  "type": "stdio"
}
```

Or, if `code-review-graph` is already on the `PATH` Antigravity sees:

```json
"code-review-graph": {
  "command": "code-review-graph",
  "args": ["serve"],
  "type": "stdio"
}
```

> On macOS, Antigravity’s inherited `PATH` may differ from the terminal (e.g. no Homebrew). If startup fails, prefer the **absolute path** from `which code-review-graph`.

**Do not** duplicate the same server in `{project}/.antigravity/mcp.json` when a global entry exists — Antigravity would load the MCP twice.

### 2.2 — Antigravity hooks (automatic refresh)

Hooks update the graph after edits and show status at session start. Install at **user level**:

```bash
code-review-graph install --platform antigravity \
  --no-skills \
  --no-instructions \
  -y \
  --repo "$HOME"
```

Effects:

- Scripts in `~/.gemini/antigravity/hooks/crg-*.sh`
- Merge into `~/.gemini/antigravity/hooks.json` (`afterFileEdit`, `sessionStart`, `beforeShellExecution` on `git commit`)

> If you already have custom hooks (RTK, telemetry, etc.), the installer **merges** without overwriting existing entries.

### 2.3 — Rules and skills (VPG hub / optional for the team)

On a machine already set up with the VPG hub, these files guide the agent:

| File | Role |
|------|------|
| `~/.gemini/antigravity/rules/code-review-graph.mdc` | Graph routing before broad exploration |
| `~/.gemini/antigravity/skills/code-review-graph/SKILL.md` | Agent workflow (status → detect-changes → targeted reads) |

For a from-scratch install outside the hub, copy these files from the internal tooling repo or generate them with:

```bash
code-review-graph install --platform antigravity -y --repo /path/to/your-repo
```

then **move** the MCP config to `~/.gemini/antigravity/mcp.json` as in §2.1.

### 2.4 — Multi-repo registry (optional but recommended)

The global registry lists known repos (`~/.code-review-graph/registry.json`):

```bash
cd /path/to/my-repo
code-review-graph register "$PWD" --alias "$(basename "$PWD")"
code-review-graph repos
```

Repeat for each active repo (booking, api_service, etc.).

### 2.5 — Build the graph **per repository**

Global MCP does not replace a local **build**: each repo has its own graph under `.code-review-graph/`.

```bash
cd /path/to/my-repo
code-review-graph build
code-review-graph status
```

Expected output (example):

```text
Nodes: 14437
Edges: 26051
Files: 1090
Last updated: 2026-05-29T...
```

If `Nodes: 0` / `Last updated: never` → the graph has not been built yet in **this** repo.

---

## Step 3 — Validate everything is active

### 3.0 — Validate the MCP launcher (`uvx` or absolute path)

**If using `uvx` config (VPG default):**

```bash
which uvx
uvx code-review-graph serve --help
```

The second command should print `serve` help (then Ctrl+C if the process stays attached — quick terminal-only test).

**If MCP is red in Antigravity but OK in the terminal:** Antigravity does not see the same `PATH`. Fix with the absolute path from `which uvx` (e.g. `/opt/homebrew/bin/uvx`) in `mcp.json`:

```json
"code-review-graph": {
  "command": "/opt/homebrew/bin/uvx",
  "args": ["code-review-graph", "serve"],
  "type": "stdio"
}
```

### 3.1 — Restart Antigravity

Quit and reopen Antigravity (or **Settings → Tools & MCP** → confirm **code-review-graph** is **connected**, not “failed to start” / binary not found).

### 3.2 — Validate the CLI in a repo

```bash
cd /path/to/my-repo
code-review-graph status
```

### 3.3 — Validate MCP via the agent

Open Antigravity on the repo and ask:

> “Use the code-review-graph MCP tool to show graph stats for this repo.”

Expected: statistics (nodes, edges, files) or an explicit message to run `build`.

### 3.4 — Validate impact analysis

After local changes:

```bash
code-review-graph detect-changes
```

The agent should use this output **before** reading large parts of the source tree.

---

## Day-to-day usage

### Refresh the graph

```bash
# Incremental (changed files only)
code-review-graph update --repo "$PWD"

# Full rebuild (after large refactor or new language)
code-review-graph build
```

Antigravity hooks already run `update --skip-flows` after file edits (if §2.2 is installed).

### Watch / daemon (multiple repos)

```bash
# Single repo, dedicated terminal
code-review-graph watch --repo "$PWD"

# Multiple repos (background)
code-review-graph daemon start
code-review-graph daemon add /path/to/repo-a
code-review-graph daemon status
```

### List registered repos

```bash
code-review-graph repos
```

### Interactive graph visualization (`visualize`)

After a `build`, CRG stores the graph in a local SQLite database under **`.code-review-graph/`** in the repo. That data is optimized for MCP/CLI queries, not for human browsing. The **`visualize`** command turns the same database into an **interactive HTML explorer** so you can sanity-check what was indexed: communities, file-level structure, dependencies, and hotspots—useful after the first build, when debugging a stale or empty graph, or when onboarding on a large legacy codebase.

The HTML is written to **`.code-review-graph/graph.html`** (regenerated on each run). Open it directly in a browser, or use the built-in local server:

```bash
cd /path/to/my-repo

# Generate HTML from the current graph DB (requires build first)
code-review-graph visualize

# Generate + serve at http://localhost:8765/graph.html
code-review-graph visualize --serve
```

**Rendering modes** (larger repos: start with `community`, drill down as needed):

```bash
code-review-graph visualize --mode auto        # default: picks a sensible layout
code-review-graph visualize --mode community   # cluster / module view
code-review-graph visualize --mode file        # file-centric graph
code-review-graph visualize --mode full        # full graph (can be heavy)
```

**Export the DB graph to other tools** (optional):

```bash
code-review-graph visualize --format graphml   # → .code-review-graph/graph.graphml
code-review-graph visualize --format cypher    # → .code-review-graph/graph.cypher (Neo4j)
code-review-graph visualize --format svg       # → .code-review-graph/graph.svg
code-review-graph visualize --format obsidian  # → .code-review-graph/obsidian/
```

> **Note:** `visualize` reads the existing graph; it does not parse source files. If the page is empty or outdated, run `code-review-graph build` or `update` first, then `visualize` again.

---

## New repository onboarding (checklist)

1. `cd` to the Git clone root
2. `code-review-graph register "$PWD" --alias "$(basename "$PWD")"`
3. `code-review-graph build` (first time: a few minutes depending on size)
4. `code-review-graph status` → nodes > 0
5. Open the project in Antigravity → verify **code-review-graph** MCP (global)
6. (Optional) Ensure `.code-review-graph/` is in `.gitignore` if missing:

   ```bash
   code-review-graph install --platform antigravity --no-skills --no-hooks --no-instructions -y --repo "$PWD"
   ```

   → updates `.gitignore` without rewriting project MCP config.

---

## Troubleshooting

| Symptom | Likely cause | Action |
|---------|--------------|--------|
| **MCP does not start** / “command not found” | **`uvx` missing** while `mcp.json` uses `"command": "uvx"` | `brew install uv` → validate `which uvx` (§1b) **or** switch to `command: code-review-graph` / absolute path (§2.1) |
| MCP OK in terminal, **fails in Antigravity** | Antigravity `PATH` ≠ terminal (common on macOS) | Put absolute path from `which uvx` or `which code-review-graph` in `mcp.json` |
| CLI `code-review-graph` OK, MCP dead | pipx CLI vs `uvx` launcher confusion | Install **uv** (Step 1b) — pipx alone does not replace `uvx` for the default config |
| MCP missing in Antigravity | Entry only in `{project}/.antigravity/mcp.json` | Add §2.1 to `~/.gemini/antigravity/mcp.json`, restart Antigravity |
| MCP connected but empty graph | No `build` in this repo | `code-review-graph build` from repo root |
| `status` OK in CLI, MCP silent | Wrong cwd / wrong workspace open | Open the Git **repo root** in Antigravity |
| Duplicate MCP servers | Global + project entry | Remove entry from `{project}/.antigravity/mcp.json` |
| Stale graph | Branch switch / large merge | `code-review-graph update` or `build` |

---

## Uninstall

### Remove global MCP

Delete the `code-review-graph` block from `~/.gemini/antigravity/mcp.json`, then restart Antigravity.

### Remove hooks

Delete entries pointing to `crg-*.sh` in `~/.gemini/antigravity/hooks.json`, then:

```bash
rm -f ~/.gemini/antigravity/hooks/crg-update.sh \
      ~/.gemini/antigravity/hooks/crg-session-start.sh \
      ~/.gemini/antigravity/hooks/crg-pre-commit.sh
```

### Remove a repo from the registry

```bash
code-review-graph unregister /path/to/repo
# or by alias
code-review-graph unregister my-alias
```

### Uninstall the CLI

```bash
pipx uninstall code-review-graph
```

Local data remains in each repo (`.code-review-graph/`) and in `~/.code-review-graph/` — delete manually if needed.

---

## Global vs per-project architecture (summary)

```text
~/.gemini/antigravity/mcp.json              → code-review-graph MCP (ALL workspaces)
~/.gemini/antigravity/hooks.json            → crg-update / sessionStart (user level)
~/.code-review-graph/registry.json → registered repo list
{repo}/.code-review-graph/      → SQLite graph for THAT repo (build required)
```

| Component | Scope | Required |
|-----------|-------|----------|
| **`uv` / `uvx`** | Machine | **Yes** if MCP uses `"command": "uvx"` (VPG default) |
| CLI `code-review-graph` | Machine | Yes (build, hooks, or MCP variant without uvx) |
| MCP in `~/.gemini/antigravity/mcp.json` | Global Antigravity | Yes (global mode) |
| `register` | Global | Recommended |
| `build` / `update` | **Per repo** | Yes (once per repository) |
| Hooks `crg-*.sh` | Global Antigravity | Recommended |
| `{project}/.antigravity/mcp.json` | Project | **No** if global MCP is configured |

---

## References

- [RTK - Installation Guide](https://voyageprive.atlassian.net/wiki/spaces/companydepartment/pages/2444099649/RTK+-+Installation+Guide) — VPG structure template
- [code-review-graph (GitHub)](https://github.com/tirth8205/code-review-graph) — upstream documentation
- Internal hub: `~/.gemini/antigravity/docs/fr/ANTIGRAVITY-IA-OPTIMISATION.md` (graph + token stack section)

---

*Last updated: May 2026 — aligned with CRG 2.3.x and VPG global Antigravity configuration.*
