---
name: code-review-graph
description: Uses code-review-graph to keep repository context token-efficient. Use at the start of repository-scoped work in Antigravity, especially code reviews, PR reviews, impact analysis, refactors, debugging, onboarding, architecture exploration, or when a repo has just been opened and the agent needs code context.
---

# Code Review Graph

**SSOT for procedure** — selective rule `rules/code-review-graph.mdc` is a trigger stub only.

## Purpose

Use `code-review-graph` as the first source of repository structure when the task needs codebase context. The goal is to avoid reading broad swaths of files when a graph query can identify the relevant blast radius, dependencies, tests, and architectural hotspots.

## When To Use

Use this skill for repository-scoped tasks such as:

- code review, PR review, or reviewing local changes
- impact analysis before changing code
- refactors or multi-file modifications
- debugging that may cross module boundaries
- onboarding or architecture exploration
- any newly opened repo where the agent needs context before acting

Skip it for tiny tasks where the target file or symbol is already known and reading the file directly is cheaper.

## Startup Workflow

At the start of a repository-scoped task:

1. Verify the current workspace is a git repository or a source repository.
2. Check whether `code-review-graph` is available:

```bash
code-review-graph status
```

3. If the graph is missing or stale, ask before running a potentially expensive full build unless the user explicitly asked to set up the graph. For setup requests, run:

```bash
code-review-graph build
```

4. For ongoing freshness while a repo is open, prefer watch mode:

```bash
code-review-graph watch --repo "$PWD"
```

If the agent cannot keep a long-running watcher active, refresh incrementally at the start of repository-scoped work:

```bash
code-review-graph update --repo "$PWD"
```

## Global Antigravity setup

- MCP server belongs in **`~/.gemini/antigravity/mcp.json`** (user-level), not only in `{project}/.antigravity/mcp.json`.
- Register repos: `code-review-graph register "$PWD" --alias "$(basename "$PWD")"`.
- Each repo still needs its own graph (`build` once); empty graph on a new repo is expected until then.

Use `register` only to add a repo to the multi-repo registry; it does not build or watch the graph.

## Review And Impact Workflow

For reviews or change analysis:

1. Run a graph-aware change query before broad file reads:

```bash
code-review-graph detect-changes
```

2. Use the output to identify impacted files, callers, tests, high-risk nodes, and dependency chains.
3. Read only the files recommended by the graph, plus any directly changed files.
4. Expand context manually only when the graph output is incomplete, ambiguous, or contradicted by the code.

## Agent Behavior

- Prefer graph-guided exploration over whole-repo scans.
- Treat graph results as routing evidence, not ground truth.
- Keep normal project rules first, especially `AGENT.md` or `agent.md` instructions.
- Do not modify generated graph storage unless explicitly asked.
- If `code-review-graph` is not installed, tell the user and suggest:

```bash
pipx install code-review-graph
code-review-graph install --platform antigravity
```

## Reporting

When this skill is used, briefly report:

- whether the graph was available, missing, or stale
- which command or MCP workflow guided the context selection
- which files or areas were selected because of the graph
- any known uncertainty where manual exploration was still needed
