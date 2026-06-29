# Subagent testing guide

This guide helps you verify, in simple conditions, that rules and skills steer the agent correctly.

## Goal

Validate three things:

- the right skill is chosen
- the right subagent type is used (when a subagent is warranted)
- the final answer is a synthesis, not a raw paste from a subagent

Tests 12–14 cover **delivery skills** that often use **direct tools** only; success is correct skill steering and output shape, not subagent launches.

## Test 1. Jira ticket before implementation

Prompt to run:

- "Triage this Jira ticket before implementation and give me impacted repo areas, dependencies, and risks."

What to observe:

- steer toward `jira-ticket-triage`
- mostly `explore`
- optionally `shell` if Git context helps

Success criteria:

- the answer covers scope, dependencies, risks, and entry points

## Test 2. Jira ticket to prompt

Prompt to run:

- "Turn this Jira ticket into an execution prompt with technical repo context."

What to observe:

- steer toward `jira-to-execution-prompt`
- use `explore` and possibly `generalPurpose`

Success criteria:

- the answer prepares a clear prompt base with scope and constraints

## Test 3. Production incident

Prompt to run:

- "Analyze this production incident and give me the most likely hypotheses."

What to observe:

- steer toward `production-incident-analysis`
- hypothesis-driven reasoning, not immediate certainty

Success criteria:

- hypotheses are ranked and missing evidence is called out if needed

## Test 4. Comparing causes

Prompt to run:

- "Compare three possible hypotheses for this bug and tell me which one to test first."

What to observe:

- steer toward `bug-hypothesis-comparison`
- structured comparison

Success criteria:

- clear trade-off and a discriminating test

## Test 5. PR review

Prompt to run:

- "Prepare a smart review of this PR with regression risks and missing tests."

What to observe:

- steer toward `pr-review-preparation`
- review focused on bugs, risks, tests

Success criteria:

- concrete findings and risk areas

## Test 6. Functional mapping

Prompt to run:

- "Map this functional domain in the repo."

What to observe:

- steer toward `functional-domain-mapping`
- mostly `explore`

Success criteria:

- structured domain, entries, and key modules

## Test 7. Business flow

Prompt to run:

- "Document this business flow end to end in the system."

What to observe:

- steer toward `business-flow-documentation`

Success criteria:

- clear chain of systems and transformations

## Test 8. Pre-estimation diagnosis

Prompt to run:

- "Before sizing this ticket, diagnose minimal scope, extended scope, and unknowns."

What to observe:

- steer toward `pre-estimation-diagnosis`

Success criteria:

- clearly separates certain, likely, and uncertain

## Test 9. UI flow

Prompt to run:

- "Test this UI flow in the browser and tell me where it diverges from expected."

What to observe:

- steer toward `browser-ui-testing`
- use skill `browser-ui-testing` and the browser subagent Antigravity exposes (may appear as `browser-use`)

Success criteria:

- flow is replayed and gaps are described precisely

## Test 10. Multi-source investigation

Prompt to run:

- "Run a multi-source investigation that combines code, Git history, UI behavior, and observability."

What to observe:

- steer toward `multi-source-investigation`
- multiple angles combined

Success criteria:

- sources are correlated instead of listed separately

## Test 11. Correlation with Grafana or Datadog

Prompt to run:

- "Correlate this code hypothesis with Grafana or Datadog and tell me which runtime evidence to check."

What to observe:

- steer toward `observability-assisted-investigation`
- runtime signals as validation

Success criteria:

- links code areas, services, and signals to inspect

## Test 12. Prompt to task brief (vague ask)

Prompt to run:

- "Make the checkout better."

What to observe:

- steer toward `prompt-to-task-brief`
- agent returns a **structured brief** (goal, in/out scope, acceptance criteria, open questions)
- agent does **not** start implementing before you approve the brief

Success criteria:

- brief is short and checkable; you can answer open questions or say "go" on the refined scope

## Test 13. Safe output hygiene (redaction)

Prompt to run:

- Paste the block below and ask: "Redact this for posting in a public Slack channel."

```text
curl -H "Authorization: Bearer ghp_FAKE1234567890abcdefghijklmnopqrst" https://api.example.com/v1/user
Database URL: mysql://appuser:SuperSecretPass@db.internal:3306/orders_prod
Customer email: jane.doe@company.test phone +33601020304
```

What to observe:

- steer toward `safe-output-hygiene`
- tokens, passwords, and PII are **replaced** (placeholders), not echoed verbatim
- short list of **what was redacted** and note if anything would need **rotation** if it had been real

Success criteria:

- safe paste-ready text; no recoverable secrets in the suggested message

## Test 14. Test plan for change

Prompt to run:

- "I changed the cart discount calculation in `CartService` (or describe a real file you touched). Give me a focused test plan: must-test, edge cases, what to skip, and what to automate."

What to observe:

- steer toward `test-plan-for-change`
- proportional plan (not a generic textbook); mentions **concrete** behaviors or files when inferable

Success criteria:

- actionable bullets you could run through before merge; clear split automate vs manual

## Quick validation grid

When a test passes, you should see:

- the right skill, implicit or explicit
- appropriate orchestration level
- a usable final synthesis
- little noise and little over-orchestration

When a test fails, you often see:

- a generic skill used where a specific one exists
- no real benefit from subagents
- an answer that is too vague
- an answer that looks like copy-paste from a subagent
