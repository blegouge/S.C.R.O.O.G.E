#!/usr/bin/env python3
"""
Global Cursor hook: compress Task/subagent prompts before tool execution.

This script is designed for `preToolUse` and returns JSON to stdout.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Any


# Debug logging (no-op in production, enable by setting DEBUG_COMPRESS_HOOK=1)
def _debug_log(msg: str, **kwargs) -> None:
    if not os.environ.get("DEBUG_COMPRESS_HOOK"):
        return
    try:
        debug_file = Path.home() / ".claude" / "token-telemetry" / "debug-compress-hook.jsonl"
        with open(debug_file, "a") as f:
            f.write(
                json.dumps(
                    {"ts": __import__("datetime").datetime.now().isoformat(), "msg": msg, **kwargs}
                )
                + "\n"
            )
    except Exception:
        pass


_HOME_DIR = (
    os.getenv("CODEX_HOME")
    or os.getenv("ANTIGRAVITY_HOME")
    or os.getenv("CURSOR_HOME")
    or os.getenv("CLAUDE_HOME")
)
if _HOME_DIR:
    _HOME_PATH = Path(_HOME_DIR).resolve()
else:
    _HOME_PATH = Path(__file__).resolve().parent.parent

# Add module paths
TOKEN_TELEMETRY_DIR = _HOME_PATH / "token-telemetry"
if str(TOKEN_TELEMETRY_DIR) not in sys.path:
    sys.path.insert(0, str(TOKEN_TELEMETRY_DIR))
SRC_DIR = _HOME_PATH / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
PROVIDERS_DIR = _HOME_PATH / "providers"
if str(PROVIDERS_DIR.parent) not in sys.path:
    sys.path.insert(0, str(PROVIDERS_DIR.parent))

from providers import detect_provider  # pylint: disable=import-error
from telemetry_common import (  # pylint: disable=import-error
    append_event,
    enrich_correlation,
    estimate_tokens,
    extract_skill_hint,
)

from telemetry_config import config
from utils.adaptive_context_manager import (  # pylint: disable=import-error
    AdaptiveContextConfig,
    AdaptiveContextManager,
)
from utils.hook_utils import (
    extract_tool_input,
    extract_tool_name,
    hook_fail_safe,
    load_stdin_json,
)
from utils.static_prompt_registry import build_global_static_block  # pylint: disable=import-error
from utils.summarizer_factory import resolve_summarizer  # pylint: disable=import-error
from utils.task_brief_validator import (  # pylint: disable=import-error
    build_deny_message,
    inject_idempotent_tag,
    validate_task_brief,
)
from utils.token_budget_guardrail import (  # pylint: disable=import-error
    analyze_guardrail_launch,
)

# Detect active provider once at module load
_PROVIDER = detect_provider()

_debug_log("imports_ok", home_path=str(_HOME_PATH), tt_dir=str(TOKEN_TELEMETRY_DIR))

DEFAULT_RATE = config.llmlingua_hook_rate
DEFAULT_MIN_CHARS = config.llmlingua_hook_min_chars
DEFAULT_MESSAGE_THRESHOLD = config.adaptive_ctx_message_threshold
DEFAULT_TOKEN_THRESHOLD = config.adaptive_ctx_token_threshold
DEFAULT_RECENT_WINDOW = int(os.getenv("ADAPTIVE_CTX_RECENT_WINDOW", "6"))
DEFAULT_SUMMARIZER_MODE = os.getenv("ADAPTIVE_CTX_SUMMARIZER", "auto").strip().lower() or "auto"
DEFAULT_COMPRESSION_BACKEND = config.compression_backend
DEFAULT_TASK_BRIEF_ENFORCE = config.task_brief_enforce
DEFAULT_STRUCTURE_MIN_INPUT_TOKENS = config.adaptive_ctx_structure_min_input_tokens

STATIC_SYSTEM_BLOCK = build_global_static_block()

_IDEMPOTENT_TAG = "[IDEMPOTENT_CONTEXT_INJECTED]"
_BLOCK2_SECTION = re.compile(
    r"(?s)\[BLOCK_2_SEMI_STATIC\]\n(.*?)\n\n\[BLOCK_3_DYNAMIC_HISTORY\]\n",
)


def _respond(payload: dict[str, Any]) -> None:
    """Respond with format appropriate for the active IDE provider."""
    permission = payload.get("permission", "allow")
    response = _PROVIDER.format_hook_response(
        permission,
        reason=payload.get("agent_message", ""),
        updated_input=payload.get("updated_input"),
        user_message=payload.get("user_message", ""),
    )
    sys.stdout.write(response)
    sys.stdout.flush()


def _append_telemetry(
    *,
    hook_data: dict[str, Any],
    tool_input: dict[str, Any],
    prompt: str,
    input_chars: int,
    input_tokens: int,
    before_chars: int,
    after_chars: int,
    before_tokens: int,
    after_tokens: int,
    rate: float,
    min_chars: int,
    message_threshold: int,
    token_threshold: int,
    recent_window: int,
    used_llmlingua: bool,
    used_claw_compactor: bool,
    compression_backend: str,
    compacted_history: int,
    summarizer_mode: str,
    git_cache_hit: bool,
    structured_prompt: str = "",
    stats: dict[str, Any] | None = None,
    compression_mode: str = "full",
    model_name: str | None = None,
    ab_group: str = "treatment",
) -> None:

    pipeline_saved_tokens = max(0, before_tokens - after_tokens)
    pipeline_saved_chars = max(0, before_chars - after_chars)
    # End-to-end: original Task prompt vs final prompt sent to the subagent.
    end_to_end_saved_tokens = max(0, input_tokens - after_tokens)
    end_to_end_saved_chars = max(0, input_chars - after_chars)
    saved_tokens = max(pipeline_saved_tokens, end_to_end_saved_tokens)
    saved_chars = max(pipeline_saved_chars, end_to_end_saved_chars)
    saved_pct = (100.0 * saved_tokens / max(1, input_tokens)) if input_tokens else 0.0
    description = str(tool_input.get("description") or "")[:240]
    subagent_type = str(
        tool_input.get("subagent_type")
        or tool_input.get("subagentType")
        or tool_input.get("type")
        or ""
    )[:80]
    skill_hint = extract_skill_hint(prompt, description)
    stats = stats or {}
    block2_preserved = 0
    if git_cache_hit:
        match = _BLOCK2_SECTION.search(structured_prompt)
        if match:
            block2_preserved = estimate_tokens(match.group(1), model_name)

    guardrail_meta = analyze_guardrail_launch(
        subagent_type=subagent_type,
        prompt=prompt,
        description=description,
        tool_input=tool_input,
        after_tokens=after_tokens,
        model_name=model_name,
    )

    idempotent_injected = _IDEMPOTENT_TAG in prompt

    row: dict[str, Any] = {
        "event": "subagentLaunch",
        "source": _PROVIDER.name,
        "tool": "Task",
        "approx_tokens": after_tokens,
        "text_chars": after_chars,
        "raw_chars": before_chars,
        "subagent_type": subagent_type,
        "subagent_description": description,
        "skill_hint": skill_hint,
        "ab_group": ab_group,
        "compression_before_chars": before_chars,
        "compression_after_chars": after_chars,
        "compression_saved_chars": saved_chars,
        "compression_input_chars": input_chars,
        "compression_before_tokens": before_tokens,
        "compression_after_tokens": after_tokens,
        "compression_saved_tokens": saved_tokens,
        "compression_input_tokens": input_tokens,
        "compression_pipeline_saved_tokens": pipeline_saved_tokens,
        "compression_end_to_end_saved_tokens": end_to_end_saved_tokens,
        "compression_saved_pct": round(saved_pct, 2),
        "compression_used_llmlingua": used_llmlingua,
        "compression_used_claw_compactor": used_claw_compactor,
        "compression_backend": compression_backend,
        "compression_history_compacted": bool(compacted_history),
        "compression_rate": rate,
        "compression_min_chars": min_chars,
        "compression_message_threshold": message_threshold,
        "compression_token_threshold": token_threshold,
        "compression_recent_window": recent_window,
        "summarizer_mode": summarizer_mode,
        "compression_git_cache_hit": git_cache_hit,
        "git_cache_block2_tokens_preserved": block2_preserved,
        "git_cache_signature": str(stats.get("git_signature") or "")[:32],
        "idempotent_context_injected": idempotent_injected,
        "compression_mode": compression_mode,
        "compression_overhead_tokens": max(0, after_tokens - input_tokens),
    }
    row.update(guardrail_meta)
    row.update(enrich_correlation(hook_data, tool_input))
    append_event(row)


from compaction.compression_pipeline import (
    build_structured_prompt as _build_structured_prompt,
    compress_dynamic_block as _compress_dynamic_block,
    compression_backend as _compression_backend,
    content_tags as _content_tags,
    reassemble_light_prompt as _reassemble_light_prompt,
    resolve_repo_root as _resolve_repo_root,
    safe_float as _safe_float,
    safe_int as _safe_int,
    segment_prompt as _segment_prompt,
)


@hook_fail_safe(fallback_json='{"permission": "allow"}')
def main() -> None:
    _debug_log("main_start")
    data = load_stdin_json()
    name = extract_tool_name(data)
    tool_input = extract_tool_input(data)

    model_name = str(data.get("model") or tool_input.get("model") or "").strip()
    if not model_name:
        model_name = os.environ.get("CODEX_MODEL") or os.environ.get("CURSOR_MODEL") or ""
    else:
        model_name = model_name[:240]

    _debug_log("parsed", tool_name=name, has_input=bool(tool_input), model_name=model_name)

    # Only rewrite Task tool input (subagent launches).
    if name != "Task" or not tool_input:
        _debug_log("skip_not_task", tool_name=name)
        _respond({"permission": "allow"})
        return

    prompt = tool_input.get("prompt")
    if not isinstance(prompt, str) or not prompt:
        _debug_log("skip_no_prompt")
        _respond({"permission": "allow"})
        return

    _debug_log("processing", prompt_len=len(prompt))

    subagent_type = str(
        tool_input.get("subagent_type")
        or tool_input.get("subagentType")
        or tool_input.get("type")
        or ""
    )
    description = str(tool_input.get("description") or "")
    _debug_log("before_validate_brief", subagent_type=subagent_type)
    try:
        brief_result = validate_task_brief(
            prompt,
            subagent_type=subagent_type,
            description=description,
        )
        _debug_log("after_validate_brief", ok=brief_result.ok)
    except Exception as e:
        _debug_log("validate_brief_error", error=str(e), error_type=type(e).__name__)
        raise
    brief_enforce = DEFAULT_TASK_BRIEF_ENFORCE
    if brief_enforce not in {"deny", "warn", "off"}:
        brief_enforce = "deny"

    if not brief_result.ok:
        violation_blob = "; ".join(brief_result.violations)
        _debug_log("brief_invalid", violations=violation_blob[:200], enforce=brief_enforce)
        append_event(
            {
                "event": "taskBriefValidation",
                "subagent_type": brief_result.subagent_type[:80],
                "brief_valid": False,
                "brief_violations": violation_blob[:500],
                "brief_enforce": brief_enforce,
            }
        )
        if brief_enforce == "deny":
            deny_msg = build_deny_message(brief_result)
            _debug_log("returning_deny", deny_msg_preview=deny_msg[:200])
            _respond(
                {
                    "permission": "deny",
                    "agent_message": deny_msg,
                    "user_message": "Subagent Task blocked: brief incomplet (idempotence/MCP). L'agent va corriger et relancer.",
                }
            )
            return
        sys.stderr.write(f"[task-brief] WARN: {violation_blob}\n")

    prompt = inject_idempotent_tag(prompt, brief_result)

    rate = min(max(_safe_float(tool_input.get("compression_rate"), DEFAULT_RATE), 0.1), 1.0)
    min_chars = max(200, _safe_int(tool_input.get("min_chars_to_compress"), DEFAULT_MIN_CHARS))
    message_threshold = max(
        2, _safe_int(tool_input.get("message_threshold"), DEFAULT_MESSAGE_THRESHOLD)
    )
    token_threshold = max(
        300, _safe_int(tool_input.get("token_threshold"), DEFAULT_TOKEN_THRESHOLD)
    )
    recent_window = max(
        1, _safe_int(tool_input.get("recent_history_window"), DEFAULT_RECENT_WINDOW)
    )

    summarizer_mode = (
        str(tool_input.get("summarizer_mode", DEFAULT_SUMMARIZER_MODE)).strip().lower()
    )
    if summarizer_mode not in {"heuristic", "flash", "auto"}:
        summarizer_mode = DEFAULT_SUMMARIZER_MODE

    input_chars = len(prompt)
    input_tokens = estimate_tokens(prompt, model_name)
    ab_group = "treatment"
    if config.ab_test_enabled:
        import random

        if random.random() < config.ab_test_ratio:
            ab_group = "control"

    if ab_group == "control":
        compressed_prompt = prompt
        stats = {
            "messages": 0,
            "tokens": input_tokens,
            "compacted": 0,
            "cache_hit": False,
        }
        before_chars = input_chars
        before_tokens = input_tokens
        used_llmlingua = False
        used_claw_compactor = False
        compression_backend = "none"
        git_cache_hit = False
        structured_prompt = ""
        compression_mode = "control"
    else:
        structure_min = max(
            500,
            _safe_int(
                tool_input.get("structure_min_input_tokens"), DEFAULT_STRUCTURE_MIN_INPUT_TOKENS
            ),
        )
        compression_mode = "light" if input_tokens < structure_min else "full"

        history, latest = _segment_prompt(prompt)
        compression_backend = _compression_backend()
        used_llmlingua = False
        used_claw_compactor = False

        latest_tags = _content_tags(latest)
        if len(latest) >= min_chars:
            latest, used_claw, used_lingua, compression_backend = _compress_dynamic_block(
                latest, rate, latest_tags
            )
            used_claw_compactor = used_claw_compactor or used_claw
            used_llmlingua = used_llmlingua or used_lingua

        structured_prompt = ""
        stats = {}

        if compression_mode == "light":
            compressed_prompt = _reassemble_light_prompt(history, latest)
            stats = {
                "messages": len(history) + (1 if latest else 0),
                "tokens": input_tokens,
                "compacted": 0,
                "cache_hit": False,
            }
            before_chars = input_chars
            before_tokens = input_tokens
            git_cache_hit = False
        else:
            manager = AdaptiveContextManager(
                config=AdaptiveContextConfig(
                    message_threshold=message_threshold,
                    token_threshold=token_threshold,
                    recent_history_window=recent_window,
                    summarizer_mode=summarizer_mode,
                ),
                summarize_fn=resolve_summarizer(summarizer_mode),
            )
            repo_root = _resolve_repo_root(data, tool_input)
            structured_prompt, stats = _build_structured_prompt(
                manager,
                history,
                latest,
                tool_input,
                repo_root=repo_root,
                summarizer_mode=summarizer_mode,
                model_name=model_name,
            )

            compressed_prompt = structured_prompt
            compress_targets = [
                r"(?s)(\[BLOCK_2_SEMI_STATIC\]\n)(.*?)(\n\n\[BLOCK_3_DYNAMIC_HISTORY\]\n)",
                r"(?s)(\[BLOCK_3_DYNAMIC_HISTORY\]\n)(.*?)(\n\n\[BLOCK_1B_TOKEN_BUDGET_GUARDRAIL\]\n)",
                r"(?s)(\[BLOCK_4_ULTRA_DYNAMIC\]\n)(.*)\Z",
            ]
            for pattern in compress_targets:
                match = re.search(pattern, compressed_prompt)
                if not match:
                    continue
                prefix, body = match.group(1), match.group(2)
                suffix = match.group(3) if match.lastindex and match.lastindex >= 3 else ""
                tags = _content_tags(body)
                if len(body) < min_chars:
                    continue
                compacted, used_claw, used_lingua, compression_backend = _compress_dynamic_block(
                    body, rate, tags
                )
                used_claw_compactor = used_claw_compactor or used_claw
                used_llmlingua = used_llmlingua or used_lingua
                replacement = f"{prefix}{compacted}{suffix}"
                compressed_prompt = (
                    compressed_prompt[: match.start()]
                    + replacement
                    + compressed_prompt[match.end() :]
                )
            before_chars = len(structured_prompt)
            before_tokens = estimate_tokens(structured_prompt, model_name)
            git_cache_hit = bool(stats.get("cache_hit"))

    updated_input = dict(tool_input)
    updated_input["prompt"] = compressed_prompt
    after_chars = len(compressed_prompt)
    after_tokens = estimate_tokens(compressed_prompt, model_name)
    _debug_log(
        "before_telemetry",
        input_tokens=input_tokens,
        after_tokens=after_tokens,
        mode=compression_mode,
    )
    try:
        _append_telemetry(
            hook_data=data,
            tool_input=tool_input,
            prompt=prompt,
            input_chars=input_chars,
            input_tokens=input_tokens,
            before_chars=before_chars,
            after_chars=after_chars,
            before_tokens=before_tokens,
            after_tokens=after_tokens,
            rate=rate,
            min_chars=min_chars,
            message_threshold=message_threshold,
            token_threshold=token_threshold,
            recent_window=recent_window,
            used_llmlingua=used_llmlingua,
            used_claw_compactor=used_claw_compactor,
            compression_backend=compression_backend,
            compacted_history=int(stats.get("compacted", 0)),
            summarizer_mode=summarizer_mode,
            git_cache_hit=git_cache_hit,
            structured_prompt=structured_prompt,
            stats=stats,
            compression_mode=compression_mode,
            model_name=model_name,
            ab_group=ab_group,
        )

        _debug_log("telemetry_ok")
    except Exception as e:
        _debug_log("telemetry_error", error=str(e), error_type=type(e).__name__)
        raise

    cache_note = ""
    if stats.get("cache_hit"):
        cache_note = f", git_cache=hit({stats.get('git_signature', '')})"
    elif stats.get("cache_saved"):
        cache_note = f", git_cache=saved({stats.get('git_signature', '')})"

    mode_note = f"mode={compression_mode}, structure_min={structure_min}"
    sys.stderr.write(
        "[adaptive-context] "
        f"Task prompt ({mode_note}, messages={stats.get('messages', 0)}, "
        f"tokens={stats.get('tokens', input_tokens)}, compacted={stats.get('compacted', 0)}, "
        f"summarizer={summarizer_mode}, backend={compression_backend}, "
        f"claw={used_claw_compactor}, llmlingua={used_llmlingua}"
        f"{cache_note}, chars={input_chars}->{after_chars})\n"
    )
    _respond({"permission": "allow", "updated_input": updated_input})


if __name__ == "__main__":
    main()
