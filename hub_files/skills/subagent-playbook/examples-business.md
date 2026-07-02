# Business-oriented subagent examples

This document describes realistic scenarios from product, delivery, review, and investigation work.

## 1. Vague Jira ticket before development

Situation:

- a Jira ticket arrives with few technical details
- you need to know whether it is front end, back end, data, or mixed

Useful request:

- "Triage this Jira ticket before implementation and give me impacted files, dependencies, risks, and the most likely entry point."

Expected skill:

- `jira-ticket-triage`

Expected outcome:

- areas of the repo to open first
- involved components or services
- edge-case risks
- unknowns to clarify before development

## 2. Jira ticket to agent prompt

Situation:

- you want to hand a ticket to another agent or prepare a clean execution

Useful request:

- "Turn this Jira ticket into an execution prompt with repo context, constraints, and likely acceptance criteria."

Expected skill:

- `jira-to-execution-prompt`

Expected outcome:

- usable prompt
- technical scope
- conventions to follow
- blind spots in the ticket

## 3. Production incident with multiple layers

Situation:

- behavior degrades in production
- you do not know whether the issue is front end, back end, an external call, or data

Useful request:

- "Analyze this production incident: suggest suspicious code areas, most likely hypotheses, and safe next checks."

Expected skill:

- `production-incident-analysis`

Expected outcome:

- ranked hypotheses
- code leads
- missing evidence to gather
- most useful next check

## 4. Bug with three possible causes

Situation:

- you hesitate between bad mapping, a recent regression, or a business rule issue

Useful request:

- "Compare these three bug hypotheses and tell me which is most credible, with evidence for and against."

Expected skill:

- `bug-hypothesis-comparison`

Expected outcome:

- comparison per hypothesis
- confidence level
- fastest discriminating test

## 5. Risky PR review

Situation:

- a PR touches several sensitive areas
- you want more than a plain diff review

Useful request:

- "Prepare a smart review of this PR with possible regressions, risky behaviors, and missing tests."

Expected skill:

- `pr-review-preparation`

Expected outcome:

- review hotspots
- functional risks
- test gaps
- areas needing careful reading

## 6. Taking over a legacy domain

Situation:

- you are taking over an old or poorly documented scope

Useful request:

- "Map this functional domain in the repo and explain entry points, key modules, and dependencies."

Expected skill:

- `functional-domain-mapping`

Expected outcome:

- overview
- local architecture
- boundary of the scope
- integrations

## 7. Documenting a business flow

Situation:

- you need to understand how information crosses several layers

Useful request:

- "Document this business flow end to end, from front end through persistence and visible outcomes."

Expected skill:

- `business-flow-documentation`

Expected outcome:

- readable sequence
- involved systems
- data transformations
- possible failure points

## 8. Pre-estimation diagnosis

Situation:

- someone asks for a quick estimate
- you want to avoid underestimating because the real scope is hidden

Useful request:

- "Run a pre-estimation diagnosis and separate minimal scope, extended scope, and unknowns that could blow up cost."

Expected skill:

- `pre-estimation-diagnosis`

Expected outcome:

- clearer sizing
- blockers
- real impact surface

## 9. Verifying a UI flow

Situation:

- a ticket or QA says a flow no longer works

Useful request:

- "Test this UI flow in the browser, replay the steps, and tell me where behavior diverges from expected."

Expected skill:

- `browser-ui-testing`

Expected outcome:

- replayed scenario
- observed behavior
- precise blocker
- suspicious screens or states

## 10. Cross investigation: code, Git, observability

Situation:

- the problem cannot be explained by code alone
- you want to combine diff, history, UI behavior, logs, or dashboards

Useful request:

- "Run a multi-source investigation on this problem and cross code, Git history, UI, and observability to produce a solid hypothesis."

Expected skill:

- `multi-source-investigation`

Expected outcome:

- facts per source
- correlations
- contradictions
- best current explanation

## 11. Code and runtime signals

Situation:

- you need to connect a technical hypothesis with Grafana, Datadog, or Elasticsearch

Useful request:

- "Correlate code hypotheses with observable signals in Grafana, Datadog, or Elasticsearch and tell me where to look."

Expected skill:

- `observability-assisted-investigation`

Expected outcome:

- most likely services or code areas
- metrics, logs, or dashboards to check
- most useful signal to confirm the lead
