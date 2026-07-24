# Compression pipeline containing prompt segmentation, type detection, and adapter routing.
from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from typing import Any

# Since these files are deployed flat in token-telemetry or inside src/utils in sys.path,
# we import them as top-level modules or packages.
try:
    from utils.static_prompt_registry import build_global_static_block
except ImportError:
    # Fallback for testing environment where they might be imported differently
    from static_prompt_registry import build_global_static_block

try:
    from utils.token_budget_guardrail import build_upstream_guardrail_report
except ImportError:
    from token_budget_guardrail import build_upstream_guardrail_report

try:
    from utils.diff_applier import resolve_workspace_roots
except ImportError:
    from diff_applier import resolve_workspace_roots

# Default backend configuration
DEFAULT_COMPRESSION_BACKEND = os.getenv("COMPRESSION_BACKEND", "claw").strip().lower()

STATIC_SYSTEM_BLOCK = build_global_static_block()


def is_code_like(text: str) -> bool:
    if "```" in text:
        return True
    patterns = (
        r"\b(def|class|import|from|return)\b",
        r"\b(function|const|let|var|export|interface)\b",
        r"\bSELECT\b|\bINSERT\b|\bUPDATE\b|\bDELETE\b",
    )
    return any(re.search(pattern, text, re.IGNORECASE) for pattern in patterns)


def is_log_like(text: str) -> bool:
    if re.search(r"\b(ERROR|WARN|INFO|DEBUG|TRACE)\b", text):
        return True
    if re.search(r"\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}:\d{2}", text):
        return True
    return "Traceback (most recent call last)" in text or "Exception:" in text


def is_subagent_output_like(text: str) -> bool:
    patterns = (
        r"\bsubagent\b",
        r"\bdeliverables?\b",
        r"\bfindings?\b",
        r"\brisks?\b",
        r"\bopen questions?\b",
        r"\btest plan\b",
    )
    return any(re.search(pattern, text, re.IGNORECASE) for pattern in patterns)


def content_tags(text: str) -> set[str]:
    tags: set[str] = set()
    if is_code_like(text):
        tags.add("code")
    if is_log_like(text):
        tags.add("logs")
    if is_subagent_output_like(text):
        tags.add("subagent")
    return tags


def safe_float(value: Any, fallback: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback


def safe_int(value: Any, fallback: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


def compression_backend() -> str:
    backend = DEFAULT_COMPRESSION_BACKEND
    if backend in {"claw", "llmlingua", "both", "auto", "headroom"}:
        return backend
    return "claw"


def compress_with_claw(dynamic_block: str, tags: set[str]) -> tuple[str, bool]:
    try:
        from claw_compactor_adapter import compress_prompt_text  # type: ignore
    except ModuleNotFoundError as exc:
        sys.stderr.write(f"[adaptive-context] Claw Compactor unavailable: {exc}\n")
        return dynamic_block, False
    compacted, stats = compress_prompt_text(dynamic_block, tags=tags)
    applied = bool(stats.get("applied"))
    if applied:
        reduction = stats.get("reduction_pct", "?")
        sys.stderr.write(
            f"[adaptive-context] Claw Compactor applied "
            f"(type={stats.get('content_type', 'text')}, reduction={reduction}%)\n"
        )
    return compacted, applied


def compress_with_llmlingua(dynamic_block: str, rate: float) -> tuple[str, bool]:
    try:
        from token_compactor import compress_prompt_context  # type: ignore
    except ModuleNotFoundError as exc:
        sys.stderr.write(f"[adaptive-context] LLMLingua unavailable, skip compression: {exc}\n")
        return dynamic_block, False
    compacted_dynamic, applied = compress_prompt_context(dynamic_block, rate=rate)
    return compacted_dynamic, applied


def compress_with_headroom(dynamic_block: str, tags: set[str]) -> tuple[str, bool]:
    try:
        from headroom_adapter import compress_prompt_text  # type: ignore
    except ModuleNotFoundError as exc:
        sys.stderr.write(f"[adaptive-context] Headroom adapter unavailable: {exc}\n")
        return dynamic_block, False
    compacted, stats = compress_prompt_text(dynamic_block, tags=tags)
    applied = bool(stats.get("applied"))
    if applied:
        reduction = stats.get("reduction_pct", "?")
        sys.stderr.write(
            f"[adaptive-context] Headroom applied "
            f"(compressor={stats.get('compressor', 'none')}, reduction={reduction}%)\n"
        )
    return compacted, applied


def compress_dynamic_block(
    dynamic_block: str,
    rate: float,
    tags: set[str],
) -> tuple[str, bool, bool, str]:
    backend = compression_backend()
    used_claw = False
    used_llmlingua = False
    current = dynamic_block

    if backend == "headroom":
        current, used_headroom = compress_with_headroom(current, tags)
        used_claw = used_headroom
        return current, used_claw, used_llmlingua, backend

    if backend in {"claw", "both", "auto"}:
        current, used_claw = compress_with_claw(current, tags)
        if backend == "auto" and used_claw:
            return current, used_claw, used_llmlingua, backend

    if backend in {"llmlingua", "both"} or (backend == "auto" and not used_claw):
        current, used_llmlingua = compress_with_llmlingua(current, rate)

    if not used_claw and not used_llmlingua:
        return dynamic_block, False, False, backend
    return current, used_claw, used_llmlingua, backend


def parse_role_and_content(segment: str) -> dict[str, str]:
    match = re.match(r"^\s*(system|user|assistant)\s*:\s*(.+)$", segment, re.IGNORECASE | re.DOTALL)
    if match:
        return {"role": match.group(1).lower(), "content": match.group(2).strip()}
    return {"role": "user", "content": segment.strip()}


def segment_prompt(prompt: str) -> tuple[list[dict[str, str]], str]:
    segments = [segment.strip() for segment in re.split(r"\n\s*\n", prompt) if segment.strip()]
    if not segments:
        return [], prompt.strip()
    if len(segments) == 1:
        return [], segments[0]

    history = [parse_role_and_content(segment) for segment in segments[:-1]]
    latest = segments[-1]
    return history, latest


def reassemble_light_prompt(history: list[dict[str, str]], latest: str) -> str:
    """Rebuild prompt without BLOCK_* wrappers (light compression mode)."""
    if not history:
        return latest
    lines: list[str] = []
    for message in history:
        role = str(message.get("role", "user")).upper()
        content = str(message.get("content", "")).strip()
        if content:
            lines.append(f"{role}: {content}")
    lines.append(latest)
    return "\n\n".join(lines)


def resolve_repo_root(hook_data: dict[str, Any], tool_input: dict[str, Any]) -> Path | None:
    merged = {**hook_data, **tool_input}
    roots = resolve_workspace_roots(merged)
    return roots[0] if roots else None


def build_structured_prompt(
    manager: Any,  # AdaptiveContextManager
    history: list[dict[str, str]],
    latest: str,
    tool_input: dict[str, Any],
    *,
    repo_root: Path | None = None,
    summarizer_mode: str = "",
    model_name: str | None = None,
) -> tuple[str, dict[str, Any]]:
    existing_state = tool_input.get("global_state")
    state_dict = existing_state if isinstance(existing_state, dict) else {}

    compacted_history, merged_state, stats = manager.compact_history(
        history,
        state_dict,
        repo_root=repo_root,
        summarizer_mode=summarizer_mode,
        model_name=model_name,
    )

    ephemeral = {}
    if "timestamp" in tool_input:
        ephemeral["timestamp"] = tool_input["timestamp"]
    if "workspace" in tool_input:
        ephemeral["workspace"] = tool_input["workspace"]

    ordered_messages = manager.build_cache_friendly_messages(
        static_system_block=STATIC_SYSTEM_BLOCK,
        global_state=merged_state,
        history_messages=compacted_history,
        latest_user_message=latest,
        ephemeral=ephemeral,
    )

    block_1 = ordered_messages[0].get("content", "")
    block_2 = ordered_messages[1].get("content", "")
    dynamic_messages = ordered_messages[2:-1]
    block_4 = ordered_messages[-1].get("content", "")

    history_lines: list[str] = []
    for message in dynamic_messages:
        role = str(message.get("role", "user")).upper()
        content = str(message.get("content", "")).strip()
        if content:
            history_lines.append(f"{role}: {content}")
    block_3 = "\n".join(history_lines).strip()

    subagent_type = str(
        tool_input.get("subagent_type")
        or tool_input.get("subagentType")
        or tool_input.get("type")
        or ""
    )
    guardrail_block = build_upstream_guardrail_report(
        subagent_type=subagent_type,
        prompt=f"{block_3}\n{block_4}".strip(),
        description=str(tool_input.get("description") or ""),
        tool_input=tool_input,
        model_name=model_name,
    )

    structured_prompt = (
        "[BLOCK_1_STATIC]\n"
        f"{block_1}\n\n"
        "[BLOCK_2_SEMI_STATIC]\n"
        f"{block_2}\n\n"
        "[BLOCK_3_DYNAMIC_HISTORY]\n"
        f"{block_3}\n\n"
        "[BLOCK_1B_TOKEN_BUDGET_GUARDRAIL]\n"
        f"{guardrail_block}\n\n"
        "[BLOCK_4_ULTRA_DYNAMIC]\n"
        f"{block_4}"
    )

    return structured_prompt, stats
