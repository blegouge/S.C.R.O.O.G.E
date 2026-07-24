#!/usr/bin/env python3
"""Measurement-source taxonomy: separate *measured* savings from *modeled* ones.

Rationale (P0 audit, 2026-07-24): the stack historically blended savings derived
from real API ``usage`` (billed / cache tokens, RTK before-after deltas) with
savings derived from **coefficients** and **char/4 proxies**. Presenting both as
a single "savings" number is misleading. This module is the single source of
truth that classifies each savings channel so the dashboard/report can badge
figures as ``measured`` (auditable) vs ``modeled`` (heuristic).

Policy
------
- ``measured``: backed by real API usage or an external tool's own accounting.
    * Git pre-flight cache preservation resolved from ``api_usage``.
    * RTK shell rewrite savings (RTK reports real before/after token counts).
- ``modeled``: derived from configured coefficients or char-based proxies.
    * Git cache preservation falling back to ``git_cache_savings_coefficient``.
    * Guardrail avoided tokens (coefficient / hard-coded cycle formula).
    * Diff-Only savings (``estimated_chars_saved / 4`` proxy).

This module only *reads* rows; it reuses the pure helpers of ``telemetry_metrics``
so classification logic stays consistent across report.py and the dashboard.
"""

from __future__ import annotations

from typing import Any

import telemetry_metrics as tm

MEASURED = "measured"
MODELED = "modeled"


def row_has_api_usage(row: dict[str, Any]) -> bool:
    """True when a row carries real API usage figures (billed or token counts)."""
    if isinstance(row.get("billed_total_tokens"), int):
        return True
    for key in ("cache_read_tokens", "cache_write_tokens", "input_tokens", "output_tokens"):
        value = row.get(key)
        if isinstance(value, (int, float)) and value > 0:
            return True
    return False


def classify_git_cache_source(
    row: dict[str, Any], session_usage: dict[str, dict[str, Any]] | None = None
) -> str:
    """Classify a git-cache preservation row as measured or modeled."""
    _tokens, src = tm.row_git_cache_tokens_preserved_with_source(row, session_usage)
    return MEASURED if src == "api_usage" else MODELED


def measured_vs_modeled_savings(
    rows: list[dict[str, Any]], session_usage: dict[str, dict[str, Any]] | None = None
) -> dict[str, Any]:
    """Aggregate savings split by measurement source across the event stream.

    Returns a dict with ``measured`` / ``modeled`` token sums and event counts,
    plus ``measured_pct`` (share of savings that is auditable) so the dashboard
    can badge the counterfactual honestly.
    """
    measured_tokens = 0
    modeled_tokens = 0
    measured_events = 0
    modeled_events = 0

    for row in rows:
        is_launch = tm.is_subagent_launch(row)

        # Git pre-flight cache: measured when backed by api_usage, else coefficient.
        if is_launch and tm.row_git_cache_hit(row):
            tokens, src = tm.row_git_cache_tokens_preserved_with_source(row, session_usage)
            if tokens > 0:
                if src == "api_usage":
                    measured_tokens += tokens
                    measured_events += 1
                else:
                    modeled_tokens += tokens
                    modeled_events += 1

        # Guardrail avoided tokens: coefficient / cycle formula -> modeled.
        if is_launch:
            guardrail = tm.row_guardrail_avoided_tokens(row)
            if guardrail > 0:
                modeled_tokens += guardrail
                modeled_events += 1

        # Diff-Only: chars/4 proxy -> modeled.
        diff = tm.diff_only_saved_tokens(row)
        if diff > 0:
            modeled_tokens += diff
            modeled_events += 1

        # RTK shell rewrite: real before/after token deltas -> measured.
        rtk = tm.rtk_hook_saved_tokens(row)
        if rtk > 0:
            measured_tokens += rtk
            measured_events += 1

    total = measured_tokens + modeled_tokens
    measured_pct = round(100.0 * measured_tokens / total, 2) if total else 0.0

    return {
        "measured": {"savings_tokens": measured_tokens, "events": measured_events},
        "modeled": {"savings_tokens": modeled_tokens, "events": modeled_events},
        "measured_pct": measured_pct,
        "total_savings_tokens": total,
    }
