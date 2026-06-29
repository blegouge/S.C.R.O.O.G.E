---
name: subagent-playbook
description: Orchestrates Antigravity subagents for broad or multi-source analysis (Jira, incidents, PRs, mapping, browser, observability). Use when the request is ambiguous, spans multiple workflows, or needs coordinated parallel investigation—after checking narrower skills.
---

# Subagent Playbook

Use when the task is broad, multi-source, or unclear which workflow applies. For caps, escalation, and briefs, **always follow workspace rules** `subagent-usage.mdc` (they override this file). Skill routing catalog: `src/rules/skills_routing.md`.

## Principles

1. Direct tools first for narrow scope.
2. One subagent by default; second only for an independent track; parallelism per rules.
3. Every subagent gets the **brief template** from `subagent-usage.mdc`.
4. Never forward raw subagent output without synthesis.

## Subagent types

- `explore` — discovery, mapping, wide search.
- `generalPurpose` — open-ended or comparative reasoning.
- `shell` — heavy CLI/git sequences.
- Browser/UI — use **`browser-ui-testing`** and the browser subagent type Antigravity provides.

## Narrower skills (prefer these when they match)

Full list and subagent types: **`src/rules/skills_routing.md`**. Read `skills/<name>/SKILL.md` for procedure.

## Execution pattern

1. State the user goal and missing context.
2. Pick the lightest subagent count allowed by rules.
3. Run subagents with explicit deliverables and stop conditions.
4. Consolidate: scope, risks, evidence, recommended next action.

## Resources

- Routing catalog: [src/rules/skills_routing.md](../../src/rules/skills_routing.md)
- SSOT guide: [docs/RULES-SKILLS-SSOT.md](../../docs/RULES-SKILLS-SSOT.md)
- Workflows: [workflows.md](workflows.md)
- Prompts: [memo.md](memo.md)
- Examples: [examples-business.md](examples-business.md)
- Checklist: [test-guide.md](test-guide.md)
