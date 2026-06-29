---
name: prompt-to-task-brief
description: Turns a vague user request into a structured task brief—goal, scope, constraints, acceptance criteria, out-of-scope—without executing the work. Use when the ask is broad, ambiguous, or missing success criteria.
---

# Prompt to Task Brief

Use as the first step when execution would otherwise guess wrong or waste tokens.

## Goal

Produce a single clear brief the user can approve before coding or subagents.

## Output sections

1. **Goal**: one sentence outcome.
2. **In scope**: concrete deliverables.
3. **Out of scope**: explicit exclusions.
4. **Constraints**: tech, time, compatibility, “must not change X”.
5. **Acceptance criteria**: checkable bullets.
6. **Open questions**: numbered; minimal set blocking start.

## Rules

- **Do not** implement the task in the same turn unless the user then approves this brief.
- Keep the brief shorter than a full spec; use `lightweight-tech-spec` if design is still wide open.

## Expected return

Markdown bullets the user can reply “go” to.

## Prompt template

```text
The user's ask is below. Rewrite it as a task brief: goal, in/out scope, constraints, acceptance criteria, open questions. Do not implement yet.
```
