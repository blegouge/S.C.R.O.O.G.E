# AGENT

## Project Purpose

This workspace is a personal Cursor configuration and automation hub. It contains:
- global AI rules (`rules/*.mdc`)
- reusable Cursor skills (`skills/`)
- MCP server configuration (`mcp.json`)
- local runtime/project metadata under `projects/`
- installed editor extensions under `extensions/`

The goal is to standardize and automate AI-assisted workflows (especially Jira/Confluence flows).

## Technical Stack

- Main format: Markdown (`.md`, `.mdc`) and JSON (`mcp.json`)
- Tooling: Cursor Rules + Cursor Skills + MCP servers
- Runtime integrations: Node-based MCP servers (`npx`, `node`) and remote Atlassian MCP endpoint
- OS context: macOS (darwin), shell is zsh

## High-Level Architecture

- `mcp.json`: central MCP server registry and environment wiring (includes **`code-review-graph`** MCP for all workspaces — not only per-project `.cursor/mcp.json`).
- **Code review graph (global)**: CLI `code-review-graph` ; MCP in `mcp.json` via **`uvx code-review-graph serve`** (`uv`/`uvx` required in PATH for MCP — see `docs/CODE-REVIEW-GRAPH-INSTALLATION-GUIDE.md` §1b) ; multi-repo registry `~/.code-review-graph/registry.json`. Per-repo `build` required. Hooks: `hooks/crg-*.sh`. Rule: `rules/code-review-graph.mdc`.
- `.cursorignore` (workspace root): reduces Cursor index noise (`projects/`, `extensions/`, transcripts, caches in this hub).
- **S.C.R.O.O.G.E.** (`~/www/private/SCROOGE`) + **`hooks/token-telemetry.py`**: proxy sizes (`postToolUse`, `afterAgentResponse`) plus **LOC heuristics** (`afterFileEdit`, `afterTabFileEdit`). Composer refus = non disponible via hooks publics → **`SCROOGE/README.md`**. UI: **`serve_dashboard.py`** (navigateur), **`dashboard_app.py`** + `pywebview`, ou **`.app`** macOS via **`build_macos_app.sh`** ; données persistantes dans **`~/.cursor/token-telemetry/`** (`events.jsonl`, layout, cache Diff-Only).
- **Compression stack** (global, all workspaces): default **`COMPRESSION_BACKEND=headroom`** in `compression.env` — **SmartCrusher** + **CCR** (cache `~/.cursor/projects/ccr_cache/`, retrieve via `~/.cursor/bin/ccr_retrieve.py`) + optional **Claw Compactor** (`claw`/`both`/`auto`). Modules live in **`~/www/private/SCROOGE/`** (`headroom_adapter.py`, `smart_crusher.py`, `ccr_manager.py`). Hook: `semantic-compress-pretool` on `Task`. See **`SCROOGE/COMPRESSION_README.md`**. Paths: `bin/telemetry-paths.sh`.
- `rules/`: behavioral rules (`alwaysApply: true|false` mixes fixed policy vs selective loading).
- `skills/`: globally available procedural skills used by the assistant.
- `projects/`: per-workspace generated metadata and MCP descriptors.
- `extensions/`: editor extension artifacts (vendor-managed, not part of user business code).

## Conventions

- Add new persistent assistant behaviors as focused `.mdc` files in `rules/`.
- Keep one concern per rule file whenever possible.
- Prefer clear trigger-based workflows for complex actions (for example `/jira-create ...`).
- Prefer concise, actionable instructions over long narrative text.
- Keep comments/instructions in English inside rule/skill content unless a localized output is explicitly required.

## Safety and Maintenance Notes

- **MCP secrets**: credentials live in `~/.cursor/mcp.secrets.env` (mode 600, never commit). `mcp.json` references `~/.cursor/bin/mcp-env-exec.sh` for servers that need tokens. Template: `mcp.secrets.env.example`.
- `mcp.json` must not contain API keys or passwords — rotate any token ever committed in plain text.
- Treat `projects/` and `extensions/` as generated/vendor content unless a task explicitly targets them.
- Prefer editing user-owned files (`rules/`, `skills/`, selected config files) over generated metadata.

## Existing Rule Context

Current always-on Jira-oriented rules already include:
- `rules/jira-create.mdc`: draft-first Jira ticket creation with explicit user approval before creation.
- `rules/jira-prompter.mdc`: Jira-to-prompt workflow with optional Confluence publication and Jira backlinking.

Any new Jira automation rule should remain compatible with these two workflows and avoid conflicting triggers.

## Subagents and skills (token-aware)

**Always-on rules (5):** `subagent-usage`, `diff-only-protocol`, `token-budget-guardrail`, `mcp-availability-check`, `session-reset`. Other rules load on description match to reduce static context.

- **MCP probe + subagent masking**: `rules/mcp-availability-check.mdc` runs a **full** MCP availability check **once per calendar day** (global **`~/.cursor/mcp-daily-stamp.txt`**); later the same day, only a trivial stamp read and **no MCP status block**. Every turn: **dynamic MCP masking** — parent classifies `LOCAL_CODE | HYBRID | INTEGRATION`, injects `[MCP_ALLOWLIST]` / `[MCP_DENYLIST]` in subagent briefs (no tool schemas), subagent inherits minimal MCP only.
- **Jira + prompt improver workflows**: loaded **selectively** (`alwaysApply: false` — Cursor includes them when the task matches descriptions). Slash commands `/jira-create`, `/jira-prompting` and phrases like ticket keys (`XYZ-123`) still trigger reliably if the model attaches the rule.
- **Default prose density**: `rules/caveman-default.mdc` — terse replies by default (**French** fragments ok); verbose only for human-facing deliverables (tickets/Confluence, onboarding…) or explicit *détail / rapport / vulgarise*.
- **RTK CLI / terminal noise**: `rules/rtk-cli-tokens.mdc` (explicit RTK usage when the Shell hook does not apply; prefer RTK equivalents in snippets).
- **Post-response consumption report**: enforced by **`hooks/stop-compliance.py`** (`stop` hook, max 2 loops) + rule `consumption-report.mdc` (selective). Dashboard tracks `consumption_complete`.
- **Task brief validation**: `TASK_BRIEF_ENFORCE=deny` in `compression.env` — `preToolUse` Task blocks launches missing `Skill:`, `[CONTEXT]` excerpts, `[AC]`, MCP class/allowlist; injects `[IDEMPOTENT_CONTEXT_INJECTED]` when valid.

- **Session Reset**: `rules/session-reset.mdc` — after 10–15 messages, generate `# RESUMING SESSION` block; user starts New Chat to avoid O(N²) history cost.
- **Diff-Only (output tokens)**: `rules/diff-only-protocol.mdc` (`alwaysApply: true`) + `src/rules/diff_protocol.md` + applier `src/utils/diff_applier.py` + global hooks `hooks/diff-only-apply.py` (`afterAgentResponse`, `subagentStop`). Integration: `src/rules/diff_integration.md`.
- **Token budget guardrail**: `rules/token-budget-guardrail.mdc` + `skills/token-budget-guardrail/`; upstream report via `BLOCK_1B` in `hooks/semantic-compress-pretool.py` (`src/utils/token_budget_guardrail.py`).
- **Authoritative policy**: `rules/subagent-usage.mdc` (caps, escalation, brief skeleton); routing catalog `src/rules/skills_routing.md`; idempotency `skills/spec-driven-idempotency/`.
- **Rules ↔ skills SSOT**: `docs/RULES-SKILLS-SSOT.md` — rules = thin policy stubs; skills = full procedures; `src/rules/` = shared injectable specs.
- **`skills/subagent-playbook/`**: umbrella orchestration only; defers to those rules for limits.
- **Vendor / plugin skills** (e.g. under editor plugin cache) may be very large; rely on them only when the task matches; prefer the lean skills in `skills/` for routing.

### Skills catalog (`skills/`)

- **Token optimization / budget**: `token-budget-guardrail` (arbitrage budget / ROI)
- **Orchestration / Idempotency**: `subagent-playbook`, `spec-driven-idempotency` (parent `[CONTEXT]` → subagent; no re-scan; Diff-Only return)
- **Delivery / Safety**: `safe-output-hygiene` (PII/secrets redaction), `prompt-to-task-brief` (structuring request to avoid wandering prompts)
- **Context optimization**: `code-review-graph` (token-efficient repository context)

## Verification scenarios (after rule changes)

Run through mentally or in a short chat: (1) narrow factual question → no subagent; (2) wide repo mapping → one `explore` subagent with a tight brief; (3) Jira/incident-style request → dedicated skill first, second subagent only if an independent track remains. Confirm MCP status still appears when relevant per `rules/mcp-availability-check.mdc`.

## Onboarding (new team members)

- **Setup:** `python3 install_stack.py` — automated phased setup (hub, secrets, venv, hooks, CRG, RTK, telemetry). See the repository root `README.md`.
- **Health check:** `bin/health-check-hub.sh` (`--full` for unit tests, `--json` for automation).
