# Subagent quick reference

This memo provides simple phrases you can type in Antigravity to trigger the right workflow.

## When to use the playbook

Use `subagent-playbook` when:

- you are not sure which workflow fits yet
- your request mixes several needs
- you want a more open-ended orchestration

Examples:

- "Help me pick the right subagent strategy to investigate this ticket and its impacts."
- "I want a broad analysis that combines code, Git history, and UI behavior."

## Dedicated skills and copy-paste prompts

### `jira-ticket-triage`

When:

- before implementing a Jira ticket
- to understand scope, dependencies, and risks

Examples:

- "Triage this Jira ticket before implementation and tell me impacted files, dependencies, and risks."
- "Analyze this Jira ticket and give me technical entry points before I start."

### `jira-to-execution-prompt`

When:

- turning a ticket into a solid execution prompt

Examples:

- "Turn this Jira ticket into an execution prompt with technical repo context."
- "Prepare what I need to turn this Jira into instructions ready for another agent."

### `production-incident-analysis`

When:

- production incident
- degraded behavior or live anomaly

Examples:

- "Analyze this production incident and suggest suspicious code areas and hypotheses."
- "I have a production bug; help me investigate likely causes before writing code."

### `bug-hypothesis-comparison`

When:

- you are unsure which of several causes applies

Examples:

- "Compare these three bug hypotheses and tell me which is most credible."
- "I want a comparative analysis of several possible causes before changing code."

### `pr-review-preparation`

When:

- preparing a deeper review
- finding regressions or missing tests

Examples:

- "Prepare a smart review of this PR with regression risks and missing tests."
- "Review this branch like a PR review and surface risky areas."

### `functional-domain-mapping`

When:

- understanding a functional domain
- taking over a legacy feature

Examples:

- "Map this functional domain in the repo."
- "Help me understand this legacy area, its entry points, and dependencies."

### `business-flow-documentation`

When:

- documenting an end-to-end business flow

Examples:

- "Document this business flow end to end in the system."
- "Explain technically how data moves between front end, back end, and database."

### `pre-estimation-diagnosis`

When:

- before estimating
- when true scope is unclear

Examples:

- "Run a pre-estimation diagnosis to find the real scope of this ticket."
- "Before sizing, give me minimal scope, extended scope, and unknowns."

### `browser-ui-testing`

When:

- replaying a UI journey
- validating a visual or functional regression

Examples:

- "Test this UI flow in the browser and report behavior gaps."
- "Replay this front-end scenario and tell me what does not happen as expected."

### `multi-source-investigation`

When:

- several sources must be cross-checked
- code + Git + browser + docs + observability

Examples:

- "Run a multi-source investigation on this problem and produce a cross-cutting synthesis."
- "I want an analysis that combines code, Git history, and UI behavior."

### `observability-assisted-investigation`

When:

- linking code to Grafana, Datadog, or Elasticsearch

Examples:

- "Correlate code hypotheses with observable signals in Grafana or Datadog."
- "Help me tie this application behavior to logs, metrics, or dashboards."

### Delivery and quality (compact)

| Skill | When |
|-------|------|
| `safe-output-hygiene` | Paste logs/config/ticket; scrub secrets and PII. |
| `prompt-to-task-brief` | Vague ask; need goal/scope/acceptance before coding. |
| `lightweight-tech-spec` | Multi-option or cross-service change; design first. |
| `test-plan-for-change` | What to test for this patch. |
| `ship-ready-commit` | Commits, branch, PR body before push. |
| `api-change-checklist` | REST/RPC contract change. |
| `data-migration-impact` | DB schema/data rollout. |
| `instrumentation-and-dashboards` | Logs/metrics/dashboards for new behavior. |
| `dependency-change-risk` | Bump or new library. |
| `ui-quality-pass` | a11y + i18n on UI code. |

## Mental shortcut

- Jira ticket before code: `jira-ticket-triage`
- Jira ticket to prompt: `jira-to-execution-prompt`
- Live incident: `production-incident-analysis`
- Several possible causes: `bug-hypothesis-comparison`
- PR review: `pr-review-preparation`
- Understand an area of the repo: `functional-domain-mapping`
- Explain a flow: `business-flow-documentation`
- Size before estimating: `pre-estimation-diagnosis`
- Test a UI flow: `browser-ui-testing`
- Cross several sources: `multi-source-investigation`
- Link code and observability: `observability-assisted-investigation`
- Vague prompt: `prompt-to-task-brief` → then execute
- Secrets in output: `safe-output-hygiene`
- Ship: `ship-ready-commit` + `test-plan-for-change`
