# Skills routing catalog (SSOT)

**Consumers:** `rules/subagent-skill-routing.mdc` (pointer only), `skills/subagent-playbook/SKILL.md`.

**Caps / escalation:** always `rules/subagent-usage.mdc` first.

**Procedure:** read `skills/<name>/SKILL.md` for the chosen skill.

---

## Skill → typical subagent type

| Skill | Prefer subagent type |
|-------|----------------------|
| `safe-output-hygiene` | direct tools (no subagent unless auditing a huge dump) |
| `prompt-to-task-brief` | direct; `generalPurpose` if request is very ambiguous |
| `token-budget-guardrail` | direct; `explore` only after ROI gate (see skill) |
| `code-review-graph` | direct or MCP; before broad reads on repo-scoped work |
| `spec-driven-idempotency` | any subagent type — **parent** must embed `[CONTEXT]`; subagent avoids re-scan |
| `subagent-playbook` | per independent track; obey caps |

---

## Topic → skill (one line)

| Topic | Skill |
|-------|-------|
| Redact secrets / PII in output | `safe-output-hygiene` |
| Vague prompt → approvable brief | `prompt-to-task-brief` |
| ROI before large reads / explore | `token-budget-guardrail` |
| Graph-first repo context | `code-review-graph` |
| Parent triage → subagent without re-scan | `spec-driven-idempotency` |
| Broad / multi-workflow orchestration | `subagent-playbook` |

---

## Selection strategy

1. Simple or narrow task → **direct tools**, no skill.
2. One clear workflow → **single** dedicated skill from the table above.
3. After parent triage / reads → domain skill + **`spec-driven-idempotency`** (`[CONTEXT]` excerpts, not paths alone).
4. Ambiguous or multi-workflow → **`subagent-playbook`** (still obey `subagent-usage.mdc` caps).
