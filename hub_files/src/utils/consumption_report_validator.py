#!/usr/bin/env python3
"""
Detect Consumption report blocks in agent responses (EN + FR headings).
"""
from __future__ import annotations

import re
from dataclasses import dataclass


_CONSUMPTION_HEADING_RE = re.compile(
    r"(?im)"
    r"(?:"
    r"^\s{0,3}(?:##|###)\s*(?:Consumption report|Rapport de consommation)\s*$"
    r"|^\s*\*\*(?:Consumption report|Rapport de consommation)\*\*\s*$"
    r")"
)

_FIELD_PATTERNS: dict[str, re.Pattern[str]] = {
    "work_mode": re.compile(
        r"(?im)^\s*[-*]\s*\*\*(?:Work mode|Mode(?: de travail)?)\*\*:\s*(.+)$"
    ),
    "tool_activity": re.compile(
        r"(?im)^\s*[-*]\s*\*\*(?:Tool activity|Activité outils?)\*\*:\s*(.+)$"
    ),
    "token_risk": re.compile(
        r"(?im)^\s*[-*]\s*\*\*(?:Token risk level|Niveau de risque tokens?)\*\*:\s*(.+)$"
    ),
    "cost_drivers": re.compile(
        r"(?im)^\s*[-*]\s*\*\*(?:Main cost drivers|Principaux postes de coût)\*\*:\s*(.+)$"
    ),
    "optimization": re.compile(
        r"(?im)^\s*[-*]\s*\*\*(?:Optimization applied|Optimisations appliquées?)\*\*:\s*(.+)$"
    ),
}


@dataclass(frozen=True, slots=True)
class ConsumptionReportStatus:
    present: bool
    complete: bool
    missing_fields: tuple[str, ...]
    work_mode: str = ""
    tool_activity: str = ""
    token_risk: str = ""
    cost_drivers: str = ""
    optimization: str = ""
    exact_unknown: bool = False


def analyze_consumption_report(text: str) -> ConsumptionReportStatus:
    blob = text or ""
    fields: dict[str, str] = {}
    for name, pattern in _FIELD_PATTERNS.items():
        match = pattern.search(blob)
        if match:
            fields[name] = match.group(1).strip()

    has_heading = bool(_CONSUMPTION_HEADING_RE.search(blob))
    has_any_field = bool(fields)
    present = has_heading or has_any_field

    required = ("work_mode", "tool_activity", "token_risk", "cost_drivers", "optimization")
    missing = tuple(k for k in required if k not in fields)
    complete = present and len(missing) == 0

    exact_unknown = "exact token count unavailable in this environment" in blob.lower()

    return ConsumptionReportStatus(
        present=present,
        complete=complete,
        missing_fields=missing,
        work_mode=fields.get("work_mode", ""),
        tool_activity=fields.get("tool_activity", ""),
        token_risk=fields.get("token_risk", ""),
        cost_drivers=fields.get("cost_drivers", ""),
        optimization=fields.get("optimization", ""),
        exact_unknown=exact_unknown,
    )


def build_consumption_followup(status: ConsumptionReportStatus) -> str:
    """Message instructing the agent to append a compliant Consumption report."""
    missing = ", ".join(status.missing_fields) if status.missing_fields else "entire section"
    return (
        "Hook compliance: your last user-facing reply is missing a complete **Consumption report** "
        f"({missing}). Append ONLY this block at the very end of your previous answer — "
        "do not rewrite the whole response:\n\n"
        "## Consumption report\n"
        "- **Work mode**: direct tools only | single subagent | multiple subagents\n"
        "- **Tool activity**: N tool calls (list high-cost: shell, subagents, web, large reads)\n"
        "- **Token risk level**: low | medium | high\n"
        "- **Main cost drivers**: 1-3 bullets\n"
        "- **Optimization applied**: what limited cost this turn\n"
        "- exact token count unavailable in this environment\n"
    )


CONSUMPTION_REPORT_TEMPLATE = """\
## Consumption report
- **Work mode**: {work_mode}
- **Tool activity**: {tool_activity}
- **Token risk level**: {token_risk}
- **Main cost drivers**: {cost_drivers}
- **Optimization applied**: {optimization}
- exact token count unavailable in this environment
"""
