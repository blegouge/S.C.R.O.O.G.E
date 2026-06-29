---
name: token-budget-guardrail
description: >-
  Deterministic token-budget arbitration before heavy agent work—ROI gates for
  large reads and explore subagents, two-strike loop halt, upstream guardrail
  report. Use before broad file reads, explore Task launches, repeated test/diff
  failures, or when token spend risk is high.
---

# Token Budget Guardrail

**SSOT for procedure** — the always-on rule `rules/token-budget-guardrail.mdc` only states hard gates; this file holds the full workflow.

Run this **budget arbitration phase** before expensive context consumption.

## When to run

- Before **Read** on any file **> 500 lines** (or unknown size—check `wc -l` / `rtk` equivalent first).
- Before launching a **`explore`** subagent (`Task` with `subagent_type: explore`).
- Before a **second retry** on the same failing track (tests, Diff-Only apply, subagent patch).
- At the **start of a heavy turn** (repo-wide mapping, parallel tools, long shell output).

## Phase 0 — Upstream report (pipeline)

For **Task / subagent** launches, the global hook injects `[BLOCK_1B_TOKEN_BUDGET_GUARDRAIL]` immediately after `[BLOCK_1_STATIC]`. Treat that block as **binding pre-flight context**—do not ignore it.

For **parent agent** turns, emit a short inline **Budget guardrail** section (3–6 lines) before the first high-cost tool in the turn.

## 1. ROI analysis (mandatory gate)

**Stop** and complete this checklist before a large read or `explore` subagent:

| Question | If "no" → prefer first |
|----------|-------------------------|
| Do I know the **exact symbol, path, or error string**? | `rtk grep` / `rtk find` with tight pattern + path |
| Can one **scoped search** answer the question? | `rtk grep` (not full file read) |
| Is **`code-review-graph`** available and cheaper for blast radius? | `code-review-graph detect-changes` / graph query |
| Is the target file **≤ 500 lines** or do I only need a **line range**? | `Read` with `offset` + `limit`, or `rtk read` |

**Approved cheap probes (examples):**

```bash
rtk grep 'SymbolName' --glob 'src/**/*.ts' --head 30
rtk find '**/FooService*' --maxdepth 6
wc -l path/to/large/file.ts   # only to decide range read vs full read
```

**Escalate to large Read or `explore` only when** you record:

- what cheap probes already ran,
- what they failed to answer,
- the **minimal** extra scope needed.

## 2. Loop halt (two-strike rule)

Track consecutive failures **per track** (same test command, same Diff-Only target file, same subagent brief):

| Streak | Action |
|--------|--------|
| 0–1 | One focused retry allowed with a **changed hypothesis** (not identical prompt/command). |
| **≥ 2** | **Halt** — no automatic 3rd attempt. |

On halt, return to the user:

1. **Impasse** — what was tried (commands, paths, subagent type).
2. **Last error** — concise symptom (no huge logs).
3. **Human decision** — pick direction: different approach, more data, or explicit "retry once more".

Reset the streak when the user gives a **new instruction** or you switch to an **independent** workstream.

Optional Task input for pipeline honesty (parent → subagent):

```json
{
  "guardrail_state": {
    "failure_streak": 2,
    "last_failure_kind": "diff-only"
  }
}
```

## 3. Upstream report template (parent agent)

Use when about to spend heavily:

```markdown
### Budget guardrail
- **Intent**: [one line]
- **ROI**: [cheap probe planned | large read/explore justified because …]
- **Loop streak**: [0|1|2+] on track `[name]`
- **Decision**: [proceed | halt for human]
```

## Integration map

| Layer | Role |
|-------|------|
| `rules/token-budget-guardrail.mdc` | Always-on policy stub (gates only) |
| This skill | **SSOT** — procedure + examples |
| `src/utils/token_budget_guardrail.py` | Deterministic report builder (hook / middleware) |
| `hooks/semantic-compress-pretool.py` | Injects `BLOCK_1B` after `BLOCK_1_STATIC` on `Task` |

See also `docs/RULES-SKILLS-SSOT.md`.

## Compatibility

- Defer to `rules/subagent-usage.mdc` for caps; this skill adds **pre-spend** gates.
- Pair with `rules/rtk-cli-tokens.mdc` and `skills/code-review-graph` before `explore`.
- On loop halt, still append `rules/consumption-report.mdc` with `Token risk level: high` and `Optimization applied: halted after 2 failures`.
