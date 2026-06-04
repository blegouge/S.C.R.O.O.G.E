# Rules ↔ Skills — single source of truth (SSOT)

English procedure text; French notes OK in user-facing docs elsewhere.

## Three layers

| Layer | Path | Role | Loaded when |
|-------|------|------|-------------|
| **Policy stub** | `rules/*.mdc` | Hard gates, triggers, cross-rule pointers | Static context (`alwaysApply` or description match) |
| **Procedure** | `skills/*/SKILL.md` | Full workflow, examples, checklists | Agent reads skill on task match |
| **Shared spec** | `src/rules/*.md` | Brief injection, routing catalog, diff format | Referenced by rules, skills, hooks |

**Rule:** procedure lives in **one** place. Rules must not duplicate skill body text; skills must not duplicate always-on caps (defer to `subagent-usage.mdc`).

## Paired artifacts (maintained)

| Policy stub | Canonical source | Notes |
|-------------|------------------|-------|
| `rules/token-budget-guardrail.mdc` | `skills/token-budget-guardrail/SKILL.md` | ROI gate, two-strike, BLOCK_1B |
| `rules/code-review-graph.mdc` | `skills/code-review-graph/SKILL.md` | Graph-first repo context |
| `rules/diff-only-protocol.mdc` | `src/rules/diff_protocol.md` | SEARCH/REPLACE output + applier |
| `rules/subagent-skill-routing.mdc` | `src/rules/skills_routing.md` | Skill → subagent type catalog |
| `rules/subagent-usage.mdc` | (self — caps/brief skeleton) | Idempotency detail → `skills/spec-driven-idempotency/` |
| `rules/consumption-report.mdc` | (self — hook-validated format) | No skill; format enforced by `stop-compliance.py` |

## When adding or changing behavior

1. **New workflow** → add `skills/<name>/SKILL.md` first; add a **thin** rule only if it must be always-on or description-triggered.
2. **Routing row** → edit `src/rules/skills_routing.md` only; do not duplicate the table in `subagent-skill-routing.mdc`.
3. **Subagent brief injectable spec** → `src/rules/` (like `diff_protocol.md`).
4. Run `bin/health-check-hub.sh` — SSOT checks verify stubs point at existing canonical files.

## Orchestration

- **`skills/subagent-playbook/`** — umbrella when request is broad; defers caps to `subagent-usage.mdc`, routing to `skills_routing.md`.
- **`skills/spec-driven-idempotency/`** — parent `[CONTEXT]` / subagent no re-scan; pair with domain skills after triage.

## Verification

```bash
~/.cursor/bin/health-check-hub.sh          # includes ssot_* checks
~/.cursor/bin/health-check-hub.sh --full   # + unit tests
```
