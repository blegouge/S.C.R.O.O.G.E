---
name: safe-output-hygiene
description: Redacts secrets, credentials, and sensitive PII from assistant output and user-facing artifacts. Use when handling logs, configs, API responses, DB dumps, tickets, or any paste that might contain tokens, keys, passwords, or personal data.
---

# Safe Output Hygiene

Use before sharing, committing, or posting anything that came from code, logs, env, or tools.

## Goal

Prevent accidental leakage of secrets and unnecessary PII in chat, Jira, PRs, docs, and snippets.

## Rules (apply every time)

- **Never** echo full API keys, tokens, passwords, private keys, connection strings with credentials, or session cookies. Replace with placeholders like `***REDACTED***` or `{{SECRET}}`.
- **Redact** host + user + password in JDBC/DSN URLs; keep only safe parts (scheme, host pattern) if needed for debugging.
- **PII**: mask emails, phone numbers, government IDs, full card numbers, and free-text health/financial data unless the user explicitly needs them for a legal task—and still prefer synthetic examples.
- **Logs**: strip query params that may contain tokens (`access_token`, `session`, `key`, `sig`).
- **Tickets / Confluence**: do not paste production secrets; reference vault or secret manager process instead.

## Checklist before “copy-paste OK”

1. Scan for regex-like secrets (Bearer, `ghp_`, `glpat-`, `AKIA`, base64 blobs in auth headers, `-----BEGIN`).
2. Confirm `.env`, `mcp.json`, and similar are not attached verbatim to public channels.
3. If unsure, redact first and say what was removed.

## Expected return

When reviewing content, return:

- sanitized version (or confirmation it is safe)
- list of redaction categories applied
- anything still risky that should be rotated if it was ever exposed

## Prompt template

```text
Review this text/code/log for secrets and PII. Return a redacted version safe for Jira/Slack/Git, list what you redacted, and flag anything that should be rotated if it leaked.
```
