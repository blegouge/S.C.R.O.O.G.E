# Codex Global Guidance

## S.C.R.O.O.G.E

- Treat S.C.R.O.O.G.E as a local-only optimization and telemetry stack.
- Prefer focused reads, diff-sized edits, and explicit verification commands to reduce token usage.
- Use installed S.C.R.O.O.G.E skills when the task matches token budgeting, code review graph context, safe output hygiene, or task brief shaping.
- Prefer RTK wrappers for noisy shell commands: `rtk pytest`, `rtk rg`, `rtk git`, `rtk diff`, `rtk read`, and `rtk test` when they answer the task.
- Before large reads or broad exploration, run a cheap search/line-count probe and state the budget decision.
- Use Codex subagents only when explicitly useful for parallel read-heavy work; each subagent has its own model/tool cost.
- When spawning a subagent, provide a compact task brief with `Skill:`, `[CONTEXT]`, `[AC]`, and the minimal MCP/tool allowlist so the compression hook can validate and reduce the prompt.
- Keep secrets out of prompts, logs, MCP config, and committed files.
- When hook telemetry is incomplete, say that exact Codex token counts may be unavailable and report the nearest measured proxy.

@{{HUB}}/RTK.md
