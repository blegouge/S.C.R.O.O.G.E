# Subagent Workflows

These workflows provide ready-to-use orchestration patterns for the main agent.

## 1. Jira ticket triage

**Use when**
- The user wants to understand implementation scope before coding.
- The ticket is vague and needs impacted areas, dependencies, and risks.

**Recommended subagents**
- `explore`: find files, modules, APIs, and tests related to the ticket.
- `shell`: inspect branch state or recent history if git context matters.

**Return**
- Impacted files and modules
- Dependencies and coupling points
- Risks and unknowns
- Suggested implementation entry points

**Prompt skeleton**
```text
Analyze this Jira ticket before implementation.
Goal: identify impacted files, components, services, dependencies, and delivery risks.
Search broadly enough to cover the full flow, but stay focused on the ticket scope.
Return:
1. likely impacted files and directories
2. relevant services/components/APIs
3. dependencies and side effects
4. implementation risks and unknowns
5. suggested starting points
```

## 2. Jira ticket to execution prompt

**Use when**
- The user wants a strong execution prompt from a Jira ticket.
- The main agent needs repository context before drafting instructions.

**Recommended subagents**
- `explore`: map the codebase areas relevant to the ticket.
- `generalPurpose`: synthesize business intent, technical scope, and constraints.

**Return**
- Technical context
- Candidate scope
- Constraints to respect
- Acceptance criteria hints

**Prompt skeleton**
```text
Gather repository context needed to transform this Jira ticket into an execution prompt.
Identify the technical areas involved, implementation boundaries, conventions, and likely acceptance criteria.
Return:
1. business and technical context
2. target files or directories
3. constraints and conventions
4. gaps or ambiguities in the ticket
5. a concise scope summary usable in a final execution prompt
```

## 3. Production incident analysis

**Use when**
- The user reports a live issue, degraded behavior, or production anomaly.

**Recommended subagents**
- `explore`: find relevant code paths and recent touch points.
- `generalPurpose`: correlate evidence and produce hypotheses.
- `shell`: inspect local git history or repo state if useful.
- Observability MCP access can be used by the main agent or by a subagent workflow when available.

**Return**
- Most likely impacted code areas
- Hypotheses ordered by probability
- Required evidence still missing
- Safe next checks

**Prompt skeleton**
```text
Investigate this production incident.
Look for relevant code paths, recent change areas, and likely failure points.
Do not assume a single cause too early.
Return:
1. suspected code areas
2. top hypotheses with rationale
3. missing evidence needed to confirm or reject each hypothesis
4. safe next investigation steps
```

## 4. Bug hypothesis comparison

**Use when**
- There are multiple plausible causes for the same bug.
- The user wants a comparative view before changing code.

**Recommended subagents**
- Launch 2 or 3 `generalPurpose` or `explore` subagents in parallel, one per hypothesis.

**Return**
- Evidence for each hypothesis
- Weak points in each theory
- Most likely cause
- Fastest discriminating test

**Prompt skeleton**
```text
Evaluate only this hypothesis for the reported bug.
Search for supporting and contradicting evidence in the codebase.
Return:
1. evidence that supports the hypothesis
2. evidence that weakens it
3. components or files involved
4. confidence level
5. the fastest check that would validate or reject it
```

## 5. PR review preparation

**Use when**
- The user wants a stronger review than a basic diff summary.

**Recommended subagents**
- `shell`: inspect git diff, commit range, and branch state.
- `explore`: examine impacted code areas for behavior and integration risks.
- `generalPurpose`: look for missing tests or edge cases.

**Return**
- Potential regressions
- Risky behavior changes
- Missing or weak tests
- Review hotspots

**Prompt skeleton**
```text
Prepare a review of this pull request or branch.
Focus on correctness, regression risks, edge cases, and test gaps.
Return:
1. main risk areas
2. possible behavioral regressions
3. missing tests or weak validation
4. files that deserve careful review
```

## 6. Functional domain mapping

**Use when**
- The user needs to understand a business area or legacy feature.

**Recommended subagents**
- `explore`: map files, entry points, services, and related modules.
- `generalPurpose`: synthesize the domain model and responsibilities.

**Return**
- Entry points
- Main modules and responsibilities
- Data flow overview
- Important dependencies

**Prompt skeleton**
```text
Map this functional domain in the repository.
Identify entry points, main modules, cross-cutting services, and boundaries.
Return:
1. domain overview
2. important files and directories
3. main responsibilities by module
4. external dependencies or integrations
5. questions that remain unclear
```

## 7. Business flow documentation

**Use when**
- The user wants a technical explanation of an end-to-end business flow.

**Recommended subagents**
- `explore`: trace the path across front-end, backend, storage, and integrations.
- `generalPurpose`: turn the trace into a coherent explanation.

**Return**
- Step-by-step flow
- Systems involved
- Input/output transformations
- Failure points and observability hooks

**Prompt skeleton**
```text
Document this business flow end to end.
Trace how data moves through the application and connected systems.
Return:
1. ordered flow steps
2. components, services, and storage involved
3. key data transformations
4. error or failure points
5. useful observability points if present
```

## 8. Pre-estimation diagnosis

**Use when**
- The user wants to estimate a ticket but the real surface area is unclear.

**Recommended subagents**
- `explore`: find all likely impact zones.
- `generalPurpose`: separate must-change areas from possible extras.

**Return**
- Minimal scope
- Extended scope
- Key uncertainties
- Factors that change the estimate materially

**Prompt skeleton**
```text
Diagnose the likely implementation surface before estimation.
Distinguish mandatory changes from optional or uncertain work.
Return:
1. minimal implementation scope
2. additional likely impact areas
3. uncertainties and blockers
4. factors that could increase effort significantly
```

## 9. Browser-based UI testing

**Use when**
- The user wants to replay a UI flow or verify a regression visually.

**Recommended subagents**
- Browser automation subagent (see skill `browser-ui-testing`; UI label may be `browser-use`).
- `explore`: only if front-end mapping is needed and `subagent-usage.mdc` allows a second independent subagent.

**Return**
- Reproduced steps
- Actual behavior
- Expected vs actual gaps
- Screens or states worth inspecting

**Prompt skeleton**
```text
Test this UI flow in the browser.
Follow the described user journey carefully and record actual behavior.
Return:
1. steps executed
2. observed result at each key step
3. deviations from expected behavior
4. anything flaky, blocked, or unclear
```

## 10. Multi-source investigation

**Use when**
- The task spans code, Git, documentation, browser behavior, and observability.
- The user wants a coordinated investigation rather than a single-source answer.

**Recommended subagents**
- `explore`: codebase mapping
- `shell`: git and terminal inspection
- Browser subagent + skill `browser-ui-testing`: UI reproduction if relevant
- `generalPurpose`: cross-source synthesis

Keep the count minimal; follow `subagent-usage.mdc` caps (default one subagent, add others only when independent).

**Return**
- Findings by source
- Cross-source correlations
- Contradictions or missing evidence
- Recommended next action

**Prompt skeleton**
```text
Run a coordinated investigation across multiple sources.
Combine code analysis, git or shell evidence, browser behavior, and any available documentation or observability context.
Return:
1. findings by source
2. correlations across sources
3. contradictions or unknowns
4. the most likely explanation
5. the best next action
```

## 11. Delivery and quality skills (reference)

Use these **skills** (see `skills/<name>/SKILL.md`) for day-to-day prompts; prefer **direct tools** unless `subagent-skill-routing.mdc` suggests a subagent.

| Skill | Use when |
|-------|----------|
| `safe-output-hygiene` | Logs, configs, snippets, tickets may contain secrets or PII. |
| `data-migration-impact` | Schema/data migrations and rollout safety. |
| `api-change-checklist` | Endpoint or contract changes. |
| `test-plan-for-change` | Need a focused test plan after a change. |
| `instrumentation-and-dashboards` | Add logs/metrics/traces/dashboards during dev. |
| `ship-ready-commit` | Finish work: commits, branch, PR draft. |
| `lightweight-tech-spec` | Ambiguous or large design before coding. |
| `ui-quality-pass` | a11y + i18n pass on UI (with `browser-ui-testing` for journeys). |
| `dependency-change-risk` | Library add/bump/replace. |
| `prompt-to-task-brief` | User ask is vague—clarify before executing. |

## Prompt writing rules

When launching subagents from these workflows:

1. Include the user goal and any known constraints.
2. Include repository or environment context when relevant.
3. Ask for a structured return format.
4. Avoid asking a subagent to do everything at once.
5. Keep the main agent responsible for the final synthesis.
