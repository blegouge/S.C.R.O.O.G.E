---
name: spec-driven-idempotency
description: >-
  Strict idempotency between parent and subagents—embed triage code excerpts in
  [CONTEXT], forbid redundant file re-scans, return Diff-Only deltas validated
  against [AC]. Use whenever spawning a subagent after Jira triage, execution
  prompts, or any parent pass that already read the repo.
---

# Spec-Driven Idempotency

**SSOT for idempotency** — caps, escalation, and brief skeleton: `rules/subagent-usage.mdc`. Diff-Only output: `src/rules/diff_protocol.md`.

**Extends** `rules/subagent-usage.mdc` (does not relax caps or bypass `rules/token-budget-guardrail.mdc`).

**Goal:** one pass of discovery on the parent; subagents execute from a **frozen spec**, not a second repo tour.

---

## When to apply

| Situation | Apply |
|-----------|--------|
| Parent ran `jira-ticket-triage`, `jira-to-execution-prompt`, or local grep/read before `Task` | **Yes** — mandatory |
| Subagent brief lists concrete `path:` + line ranges or excerpts | **Yes** |
| Greenfield mapping (“where is module X?”) with **no** parent excerpts | **No** — use `explore` + `token-budget-guardrail` instead |
| User explicitly asks subagent to re-verify full files | **Yes** — set `RESCAN: allowed` in brief |

Parent brief line (required when spawning):

```text
Skill: spec-driven-idempotency
```

---

## The three rules (strict)

### 1. Context reuse (parent)

Before `Task`, the **parent** must materialize everything the subagent needs to act **without** reopening the same files for orientation.

**Extract from Jira triage / parent discovery:**

- Ticket key + one-line intent (if Jira).
- **Critical excerpts**: 5–40 lines per hotspot, with `path:start-end` (or `path` + signature block).
- **Signatures / types**: public methods, interfaces, DTO fields involved in the change.
- **Call graph hints**: caller → callee names (no full tree dump).
- **Known failures**: stack trace lines, test names, log snippets (redact secrets per `safe-output-hygiene`).
- **Decisions already made**: chosen approach, files **out of scope**.

**Forbidden in parent → subagent handoff:**

- “Read `src/foo.ts` and figure it out” with **no** excerpt when parent already read it.
- Pasting the entire parent chat — only the **spec blocks** below.

### 2. No re-scan (subagent)

If `[CONTEXT]` excerpts + signatures **isolate** the edit or analysis target, the subagent **must not**:

- `Read` whole files listed in `[CONTEXT]` (or run unbounded `grep` / `explore` on those paths) **for orientation**.
- Re-run `jira-ticket-triage`-style broad discovery on the same ticket scope.

**Allowed reads (narrow exceptions only):**

| Trigger | Allowed action |
|---------|----------------|
| Brief contains `RESCAN: allowed` with reason | Scoped re-read as specified |
| SEARCH/REPLACE needs bytes not in excerpt | **Single** `Read` with `offset` + `limit` covering only the hunk ± few lines |
| Excerpt is ambiguous (two matching symbols) | One targeted `rtk grep` with pattern + path; then stop |
| AC requires proving a test/file not in `[CONTEXT]` | Read **only** that path; cite why in output header |
| Implementation impossible from spec | **Halt** — return `ESCALATION` block (see below), no silent full-file scan |

### 3. Compact output contract (subagent)

Subagent output is **idempotent** relative to the brief: parent already knows `[CONTEXT]` and ticket narrative.

**Validate first:** each `[AC]` bullet → `PASS` | `FAIL` | `N/A` (one line each).

**Then return only:**

1. **AC checklist** (mandatory, ≤ 1 line per AC).
2. **Delta:** Diff-Only `path:` + SEARCH/REPLACE blocks (`src/rules/diff_protocol.md`) **or** findings that are **not** already in `[CONTEXT]` (new facts only).
3. **Optional** `ESCALATION` (if halted): missing excerpt, suggested parent snippet, minimal ask.

**Forbidden in subagent → parent return:**

- Restating ticket summary, architecture tour, or excerpts already in `[CONTEXT]`.
- “I read `foo.ts` and found…” when the finding duplicates the brief.
- Full files, large unchanged regions, or narrative recap before the diff.

**User-facing synthesis** stays on the **parent** (`subagent-usage.mdc` → After subagents).

---

## Spec brief format (parent → subagent)

Use **English** for spec sections (aligns with `jira-prompter` execution prompts). Keep French only if the user explicitly requires it for that task.

```text
Skill: spec-driven-idempotency
Skill: [domain-skill-if-any]   # e.g. jira-ticket-triage — secondary, for routing hints

Purpose: [one sentence — what the subagent must produce]

[CONTEXT]
Ticket: [KEY or n/a]
Parent pass: [jira-ticket-triage | local triage | PR diff review — date optional]

Files in play:
- path/to/A.ts (lines 40-72) — [role: e.g. delete guard]
- path/to/B.php (lines 10-18) — [role: e.g. caller]

Excerpts:
---
path: path/to/A.ts:40-72
<verbatim excerpt — exact indentation>
---
path: path/to/B.php:10-18
<signatures or excerpt>
---

Symbols:
- ClassName::methodName(args): ReturnType — [one line behavior]
- otherFn() — [call site summary if known]

Known facts (parent-confirmed):
- [bullet]
- [bullet]

Out of scope:
- [explicit exclusions]

[GOALS]
1. [ordered, testable goal]
2. [...]

[SCOPE]
- [concrete deliverables: files, tests, docs]

[CONSTRAINTS]
- [tech / compatibility / must-not-break]

[AC]
1. [checkable criterion]
2. [...]

RESCAN: forbidden   # default; or "allowed: <reason + paths>"

Deliverables:
- [files / conclusions / risks]

Output:
- AC checklist then Diff-Only hunks only (see diff_protocol.md)
- No recap of [CONTEXT]; new facts only

Stop: [explicit done condition]

guardrail_state: { "failure_streak": 0 }   # optional
```

---

## Parent workflow (after triage)

1. **Freeze** triage output into `[CONTEXT]` (excerpts + symbols), not file pointers alone.
2. **Map** each `[AC]` to a verifiable artifact (test name, log line, UI state).
3. Set `RESCAN: forbidden` unless you knowingly left a gap.
4. Launch **one** subagent (per caps) with the spec above + domain `Skill:` if needed.
5. On return: merge AC results + apply diffs; **do not** forward subagent prose verbatim to the user.

### Minimum excerpt quality

| Quality | Parent action |
|---------|----------------|
| Excerpt shows the bug line or branch to change | OK to forbid re-scan |
| Only file path, no lines | Parent must read and add excerpt **before** Task |
| Stale excerpt suspected | Parent re-reads once, updates `[CONTEXT]`, then Task |

---

## Subagent workflow

1. Parse `[AC]`, `[CONTEXT]`, `RESCAN` flag.
2. If `RESCAN: forbidden` — work from excerpts; use narrow read exceptions only (table above).
3. Implement or analyze; emit Diff-Only or factual delta.
4. Self-check: every sentence in the reply — **would the parent learn something new?** If no, delete it.

### ESCALATION block (when stuck)

```text
ESCALATION
Reason: [one line — e.g. ambiguous symbol Foo in excerpt]
Need from parent: [specific lines or signature, not "re-triage whole module"]
Suggested excerpt: path:line-line or grep pattern
```

Do **not** widen scope silently.

---

## Integration

| Layer | Role |
|-------|------|
| `rules/subagent-usage.mdc` | Caps + brief skeleton; **idempotency section** |
| `rules/subagent-skill-routing.mdc` | Route here when delegating after triage |
| `rules/diff-only-protocol.mdc` | Output shape for code changes |
| `skills/token-budget-guardrail` | Parent ROI before triage reads; subagent respects no broad re-read |
| `skills/jira-ticket-triage` | Produces raw findings → parent compresses into `[CONTEXT]` |
| `skills/jira-to-execution-prompt` | Often **is** the spec; still add excerpts before implementation subagent |
| `hooks/diff-only-apply.py` | Applies subagent hunks on `subagentStop` |

---

## Anti-patterns

| Anti-pattern | Fix |
|--------------|-----|
| Parent: “Subagent: analyze SHOP-123” | Parent triages first; embed `[CONTEXT]` |
| Subagent re-reads 400-line file “for context” | Use excerpt; range-read only the hunk |
| Subagent returns AC + 2 pages of recap | AC lines + diff only |
| Parent forwards raw subagent output to user | Parent synthesizes |
| Duplicate `explore` after parent `explore` | Same brief with frozen spec; second agent only if **independent** track |

---

## Examples

### Parent `[CONTEXT]` fragment (good)

```text
Excerpts:
---
path: library/Checker/SaleroomChecker.php:88-104
    if (!$this->isSaleLive($sale)) {
        $this->deleteAvailabilitySaleDocument($sale);
        return;
    }
---
Symbols:
- SaleroomChecker::isSaleLive(Sale $sale): bool — ELS + catalog flags
```

### Subagent return (good)

```text
AC:
1. PASS — guard added before deleteAvailability*
2. PASS — unit SaleroomCheckerTest::testDoesNotDeleteWhenLive

path: library/Checker/SaleroomChecker.php
<<<<<<< SEARCH
    if (!$this->isSaleLive($sale)) {
        $this->deleteAvailabilitySaleDocument($sale);
=======
    if (!$this->isSaleLive($sale)) {
        return;
    }
    if ($this->shouldPurgeStale($sale)) {
        $this->deleteAvailabilitySaleDocument($sale);
>>>>>>> REPLACE
```

### Subagent return (bad)

```text
I read SaleroomChecker.php. The class checks live status via isSaleLive...
[20 lines of narrative]
Here is the updated file:
<?php ... entire file ...
```

---

## Checklists

### Parent (before `Task`)

- [ ] `Skill: spec-driven-idempotency` present
- [ ] `[CONTEXT]` has verbatim excerpts with paths + line ranges
- [ ] `[AC]` is checkable without reinterpretation
- [ ] `RESCAN` set intentionally
- [ ] No duplicate subagent discovery of the same files

### Subagent (before return)

- [ ] AC checklist complete
- [ ] No file re-read violated `RESCAN: forbidden`
- [ ] No recap of `[CONTEXT]` / ticket
- [ ] Code changes are Diff-Only only
- [ ] New facts only, or `ESCALATION`
