#!/usr/bin/env python3
"""
Adaptive context management for cache-friendly LLM request assembly.

Includes an LLM-free Git pre-flight cache for BLOCK_2 semi-static KV state.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

Message = dict[str, Any]
StateDict = dict[str, str]

# Resolve home directory dynamically based on environment or script path
_HOME_DIR = (
    os.getenv("CLAUDE_HOME")
    or os.getenv("GEMINI_HOME")
    or os.getenv("ANTIGRAVITY_HOME")
    or os.getenv("HERMES_HOME")
    or os.getenv("CODEX_HOME")
    or os.getenv("CURSOR_HOME")
)
if _HOME_DIR:
    _HOME_PATH = Path(_HOME_DIR).resolve()
else:
    _HOME_PATH = Path(__file__).resolve().parent.parent.parent

CURSOR_PROJECTS_DIR = _HOME_PATH / "projects"
CACHE_SCHEMA_VERSION = 1
_CACHE_PORCELAIN_SKIP = re.compile(
    r"(?:^|\s)(?:\?\?|\sM|\sA|\sD)\s+.*(?:/|^)(?:\.cursor|\.gemini/antigravity)/projects/cache_[^/\s]+\.json",
    re.IGNORECASE,
)


@dataclass(slots=True)
class AdaptiveContextConfig:
    """Runtime thresholds and assembly options."""

    message_threshold: int = 8
    token_threshold: int = 3000
    keep_recent_messages: int = 2
    recent_history_window: int = 6
    max_state_items: int = 12
    summarizer_mode: str = "auto"  # heuristic | flash | auto
    enable_git_cache: bool = True


@dataclass(frozen=True, slots=True)
class GitRepoSnapshot:
    """Git inputs used for deterministic pre-flight cache keys."""

    branch: str
    commit_sha: str
    porcelain: str
    repo_root: str

    def signature_material(self) -> str:
        return f"{self.branch}\n{self.commit_sha}\n{self.porcelain}"


@dataclass(slots=True)
class Block2CacheEntry:
    """Persisted BLOCK_2 KV payload."""

    global_state_kv: StateDict
    history_fingerprint: str
    summarizer_mode: str
    git_snapshot: GitRepoSnapshot
    block_2_content: str = ""
    created_at: str = ""


try:
    from telemetry_common import estimate_tokens
except ImportError:
    import functools

    @functools.lru_cache(maxsize=1024)
    def estimate_tokens(text: str, model_name: str | None = None) -> int:
        """Fast, model-agnostic token proxy fallback."""
        if not text:
            return 0
        try:
            import tiktoken

            encoding = tiktoken.get_encoding("cl100k_base")
            return len(encoding.encode(text, disallowed_special=()))
        except Exception:
            return max(1, (len(text) + 3) // 4)


def estimate_messages_tokens(messages: list[Message], model_name: str | None = None) -> int:
    """Approximate token volume for a message list."""
    total = 0
    for message in messages:
        content = message.get("content")
        if isinstance(content, str):
            total += estimate_tokens(content, model_name)
        elif isinstance(content, list):
            for item in content:
                if isinstance(item, dict):
                    text = item.get("text")
                    if isinstance(text, str):
                        total += estimate_tokens(text, model_name)

    return total


def _git_cache_enabled() -> bool:
    raw = os.getenv("ADAPTIVE_CTX_GIT_CACHE", "1").strip().lower()
    return raw not in {"0", "false", "no", "off"}


def _sanitize_porcelain_for_signature(porcelain: str) -> str:
    """
    Drop adaptive-context cache artifacts from porcelain so writing a cache file
    does not invalidate the Git signature on the next hook run.
    """
    kept: list[str] = []
    for line in porcelain.splitlines():
        normalized = line.replace("\\", "/")
        path_part = normalized[3:].lstrip() if len(normalized) >= 3 else normalized
        if ".cursor/projects/cache_" in path_part and path_part.endswith(".json"):
            continue
        if ".gemini/antigravity/projects/cache_" in path_part and path_part.endswith(".json"):
            continue
        if "projects/cache_" in path_part and path_part.endswith(".json"):
            continue
        if _CACHE_PORCELAIN_SKIP.search(line):
            continue
        kept.append(line)
    return "\n".join(kept)


def _run_git(repo_root: Path, *args: str, timeout_sec: float = 2.0) -> str:
    try:
        completed = subprocess.run(
            ["git", "-C", str(repo_root), *args],
            capture_output=True,
            text=True,
            timeout=timeout_sec,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""
    if completed.returncode != 0:
        return ""
    return completed.stdout.strip()


def find_git_repo_root(start: Path | str | None) -> Path | None:
    """Return the nearest directory containing a .git folder."""
    if start is None:
        return None
    current = Path(start).expanduser().resolve()
    if not current.exists():
        return None
    probe = current if current.is_dir() else current.parent
    for candidate in (probe, *probe.parents):
        if (candidate / ".git").exists():
            return candidate
    return None


def collect_git_repo_snapshot(repo_root: Path | str | None) -> GitRepoSnapshot | None:
    """
    Build a Git snapshot from branch, HEAD SHA, and porcelain status.

    Returns None when the path is not inside a Git repository.
    """
    root = find_git_repo_root(repo_root)
    if root is None:
        return None

    branch = _run_git(root, "rev-parse", "--abbrev-ref", "HEAD") or "UNKNOWN"
    commit_sha = _run_git(root, "rev-parse", "HEAD") or "UNKNOWN"
    raw_porcelain = _run_git(root, "status", "--porcelain") or ""
    porcelain = _sanitize_porcelain_for_signature(raw_porcelain)
    return GitRepoSnapshot(
        branch=branch,
        commit_sha=commit_sha,
        porcelain=porcelain,
        repo_root=str(root),
    )


def compute_git_signature(snapshot: GitRepoSnapshot) -> str:
    """Fast deterministic hash for cache file naming."""
    digest = hashlib.sha256(snapshot.signature_material().encode("utf-8")).hexdigest()
    return digest[:16]


def format_block_2_content(global_state: StateDict) -> str:
    """Match build_cache_friendly_messages BLOCK_2 wire format."""
    payload = json.dumps(global_state, ensure_ascii=False, sort_keys=True)
    return f"[GLOBAL_STATE_KV]\n{payload}"


class GitPreflightCache:
    """
    LLM-free pre-flight cache for BLOCK_2 semi-static KV state.

    Files live under ~/.cursor/projects/cache_<git_signature>.json
    """

    def __init__(self, projects_dir: Path | None = None) -> None:
        self.projects_dir = projects_dir or CURSOR_PROJECTS_DIR

    def cache_path(self, git_signature: str) -> Path:
        return self.projects_dir / f"cache_{git_signature}.json"

    def load(
        self,
        git_signature: str,
        *,
        history_fingerprint: str,
        summarizer_mode: str,
    ) -> Block2CacheEntry | None:
        path = self.cache_path(git_signature)
        if not path.is_file():
            return None
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        if not isinstance(raw, dict):
            return None
        if raw.get("version") != CACHE_SCHEMA_VERSION:
            return None
        if raw.get("git_signature") != git_signature:
            return None
        if raw.get("history_fingerprint") != history_fingerprint:
            return None
        if raw.get("summarizer_mode") != summarizer_mode:
            return None

        kv = raw.get("global_state_kv")
        if not isinstance(kv, dict):
            return None
        state: StateDict = {}
        for key, value in kv.items():
            if isinstance(key, str) and value is not None:
                state[key] = str(value)[:240]

        git_blob = raw.get("git")
        snapshot = GitRepoSnapshot(
            branch="UNKNOWN",
            commit_sha="UNKNOWN",
            porcelain="",
            repo_root="",
        )
        if isinstance(git_blob, dict):
            snapshot = GitRepoSnapshot(
                branch=str(git_blob.get("branch", "UNKNOWN")),
                commit_sha=str(git_blob.get("commit_sha", "UNKNOWN")),
                porcelain=str(git_blob.get("porcelain", "")),
                repo_root=str(git_blob.get("repo_root", "")),
            )

        block_2 = raw.get("block_2_content")
        if not isinstance(block_2, str) or not block_2.strip():
            block_2 = format_block_2_content(state)

        return Block2CacheEntry(
            global_state_kv=state,
            history_fingerprint=history_fingerprint,
            summarizer_mode=summarizer_mode,
            git_snapshot=snapshot,
            block_2_content=block_2,
            created_at=str(raw.get("created_at", "")),
        )

    def save(
        self,
        git_signature: str,
        entry: Block2CacheEntry,
    ) -> Path | None:
        self.projects_dir.mkdir(parents=True, exist_ok=True)
        path = self.cache_path(git_signature)
        payload = {
            "version": CACHE_SCHEMA_VERSION,
            "git_signature": git_signature,
            "git": {
                "branch": entry.git_snapshot.branch,
                "commit_sha": entry.git_snapshot.commit_sha,
                "porcelain": entry.git_snapshot.porcelain,
                "repo_root": entry.git_snapshot.repo_root,
            },
            "history_fingerprint": entry.history_fingerprint,
            "summarizer_mode": entry.summarizer_mode,
            "global_state_kv": entry.global_state_kv,
            "block_2_content": entry.block_2_content,
            "created_at": entry.created_at or datetime.now(UTC).replace(microsecond=0).isoformat(),
        }
        try:
            path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
                encoding="utf-8",
            )
        except OSError:
            return None
        return path


def _flatten_text(messages: list[Message]) -> str:
    parts: list[str] = []
    for message in messages:
        role = str(message.get("role", "unknown"))
        content = message.get("content")
        if isinstance(content, str):
            snippet = content.strip()
            if snippet:
                parts.append(f"{role}: {snippet}")
    return "\n".join(parts)


def _extract_kv_pairs(text: str, max_items: int) -> StateDict:
    kv: StateDict = {}
    for line in text.splitlines():
        stripped = line.strip("- ").strip()
        if ":" not in stripped:
            continue
        key, value = stripped.split(":", 1)
        normalized_key = re.sub(r"[^A-Za-z0-9_]+", "_", key.strip()).strip("_")
        normalized_value = value.strip()
        if normalized_key.lower() in {"user", "assistant", "system"}:
            normalized_key = (
                "Last_User_Turn" if normalized_key.lower() == "user" else "Last_Assistant_Turn"
            )
        if not normalized_key or not normalized_value:
            continue
        if normalized_key in kv:
            continue
        kv[normalized_key] = normalized_value[:240]
        if len(kv) >= max_items:
            break
    return kv


def local_kv_summarizer(text: str, max_items: int = 12) -> StateDict:
    """
    Lightweight fallback summarizer without external model call.
    """
    extracted = _extract_kv_pairs(text, max_items=max_items)
    if extracted:
        return extracted

    chunks = [chunk.strip() for chunk in re.split(r"[.!?\n]+", text) if chunk.strip()]
    summary: StateDict = {}
    if chunks:
        summary["Conversation_Focus"] = chunks[0][:240]
    if len(chunks) > 1:
        summary["Latest_Constraint"] = chunks[min(1, len(chunks) - 1)][:240]
    if len(chunks) > 2:
        summary["Pending_Item"] = chunks[-1][:240]
    return summary


class AdaptiveContextManager:
    """Compacts old history and builds cache-friendly request blocks."""

    def __init__(
        self,
        config: AdaptiveContextConfig | None = None,
        summarize_fn: Callable[[str, int], StateDict] | None = None,
        git_cache: GitPreflightCache | None = None,
    ) -> None:
        self.config = config or AdaptiveContextConfig()
        self.summarize_fn = summarize_fn or local_kv_summarizer
        self.git_cache = git_cache or GitPreflightCache()

    def should_compact(
        self, history_messages: list[Message], model_name: str | None = None
    ) -> bool:
        message_count = len(history_messages)
        token_count = estimate_messages_tokens(history_messages, model_name=model_name)
        return (
            message_count > self.config.message_threshold
            or token_count > self.config.token_threshold
        )

    def history_fingerprint(
        self,
        history_messages: list[Message],
        previous_state: StateDict | None,
        *,
        summarizer_mode: str = "",
    ) -> str:
        """Stable digest so cache hits only reuse KV for the same compaction inputs."""
        payload = {
            "history": history_messages,
            "previous_state": previous_state or {},
            "message_threshold": self.config.message_threshold,
            "token_threshold": self.config.token_threshold,
            "keep_recent_messages": self.config.keep_recent_messages,
            "max_state_items": self.config.max_state_items,
            "summarizer_mode": summarizer_mode or self.config.summarizer_mode,
        }
        blob = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:24]

    def try_load_block2_cache(
        self,
        *,
        repo_root: Path | str | None,
        history_messages: list[Message],
        previous_state: StateDict | None,
        summarizer_mode: str = "",
    ) -> tuple[StateDict | None, dict[str, Any]]:
        """
        LLM-free pre-flight: load BLOCK_2 KV from disk when Git signature matches.

        Returns merged global state on hit, else None.
        """
        meta: dict[str, Any] = {
            "cache_hit": False,
            "git_signature": "",
            "cache_path": "",
        }
        if not self.config.enable_git_cache or not _git_cache_enabled():
            meta["cache_reason"] = "disabled"
            return None, meta
        if not self.should_compact(history_messages):
            meta["cache_reason"] = "below_threshold"
            return None, meta

        snapshot = collect_git_repo_snapshot(repo_root)
        if snapshot is None:
            meta["cache_reason"] = "not_git"
            return None, meta

        git_signature = compute_git_signature(snapshot)
        meta["git_signature"] = git_signature
        mode = summarizer_mode or self.config.summarizer_mode
        fingerprint = self.history_fingerprint(
            history_messages, previous_state, summarizer_mode=mode
        )

        entry = self.git_cache.load(
            git_signature,
            history_fingerprint=fingerprint,
            summarizer_mode=mode,
        )
        if entry is None:
            meta["cache_reason"] = "miss"
            meta["cache_path"] = str(self.git_cache.cache_path(git_signature))
            return None, meta

        merged_state: StateDict = dict(previous_state or {})
        merged_state.update(entry.global_state_kv)
        meta.update(
            {
                "cache_hit": True,
                "cache_reason": "hit",
                "cache_path": str(self.git_cache.cache_path(git_signature)),
                "git_branch": snapshot.branch,
                "git_commit": snapshot.commit_sha[:12],
            }
        )
        return merged_state, meta

    def persist_block2_cache(
        self,
        *,
        repo_root: Path | str | None,
        history_messages: list[Message],
        previous_state: StateDict | None,
        merged_state: StateDict,
        summarizer_mode: str = "",
    ) -> dict[str, Any]:
        """Write BLOCK_2 KV to ~/.cursor/projects/cache_<git_signature>.json."""
        meta: dict[str, Any] = {"cache_saved": False}
        if not self.config.enable_git_cache or not _git_cache_enabled():
            return meta

        snapshot = collect_git_repo_snapshot(repo_root)
        if snapshot is None:
            return meta

        git_signature = compute_git_signature(snapshot)
        mode = summarizer_mode or self.config.summarizer_mode
        fingerprint = self.history_fingerprint(
            history_messages, previous_state, summarizer_mode=mode
        )
        entry = Block2CacheEntry(
            global_state_kv=dict(merged_state),
            history_fingerprint=fingerprint,
            summarizer_mode=mode,
            git_snapshot=snapshot,
            block_2_content=format_block_2_content(merged_state),
        )
        saved_path = self.git_cache.save(git_signature, entry)
        if saved_path is not None:
            meta.update(
                {
                    "cache_saved": True,
                    "git_signature": git_signature,
                    "cache_path": str(saved_path),
                }
            )
        return meta

    def compact_history(
        self,
        history_messages: list[Message],
        previous_state: StateDict | None = None,
        *,
        repo_root: Path | str | None = None,
        summarizer_mode: str = "",
        model_name: str | None = None,
    ) -> tuple[list[Message], StateDict, dict[str, int | bool | str]]:
        """
        Compact old messages into key-value state when thresholds are exceeded.

        When Git pre-flight cache hits, summarizer_fn is not invoked.
        """
        previous_state = previous_state or {}
        if not history_messages:
            return [], previous_state, {"compacted": False, "tokens": 0, "messages": 0}

        token_count = estimate_messages_tokens(history_messages, model_name=model_name)
        if not self.should_compact(history_messages, model_name=model_name):
            return (
                history_messages,
                previous_state,
                {
                    "compacted": False,
                    "tokens": token_count,
                    "messages": len(history_messages),
                },
            )

        split_index = max(0, len(history_messages) - self.config.keep_recent_messages)
        stale_messages = history_messages[:split_index]
        recent_messages = history_messages[split_index:]

        cached_state, cache_meta = self.try_load_block2_cache(
            repo_root=repo_root,
            history_messages=history_messages,
            previous_state=previous_state,
            summarizer_mode=summarizer_mode,
        )
        if cached_state is not None:
            stats: dict[str, int | bool | str] = {
                "compacted": True,
                "tokens": token_count,
                "messages": len(history_messages),
                "cache_hit": True,
                "summarizer_skipped": True,
            }
            for key, value in cache_meta.items():
                stats[key] = value  # type: ignore[assignment]
            return recent_messages, cached_state, stats

        stale_blob = _flatten_text(stale_messages)
        kv_summary = self.summarize_fn(stale_blob, self.config.max_state_items)

        merged_state: StateDict = dict(previous_state)
        merged_state.update(kv_summary)

        save_meta = self.persist_block2_cache(
            repo_root=repo_root,
            history_messages=history_messages,
            previous_state=previous_state,
            merged_state=merged_state,
            summarizer_mode=summarizer_mode,
        )

        stats = {
            "compacted": True,
            "tokens": token_count,
            "messages": len(history_messages),
            "cache_hit": False,
            "summarizer_skipped": False,
        }
        for key, value in {**cache_meta, **save_meta}.items():
            stats[key] = value  # type: ignore[assignment]
        return recent_messages, merged_state, stats

    def build_cache_friendly_messages(
        self,
        *,
        static_system_block: str,
        global_state: StateDict | None,
        history_messages: list[Message],
        latest_user_message: str,
        ephemeral: dict[str, Any] | None = None,
    ) -> list[Message]:
        """
        Build final request messages in strict cache-friendly order:
        1) static, 2) semi-static state, 3) recent dynamic history, 4) latest ultra-dynamic input.
        """
        state_payload = global_state or {}
        ephemeral = ephemeral or {}
        recent_window = max(0, self.config.recent_history_window)
        recent_history = history_messages[-recent_window:] if recent_window else []

        block_1 = static_system_block.strip()
        block_2 = json.dumps(state_payload, ensure_ascii=False, sort_keys=True)
        block_4_payload = {
            "latest_user_message": latest_user_message,
            "ephemeral": ephemeral,
        }
        block_4 = json.dumps(block_4_payload, ensure_ascii=False)

        output: list[Message] = []
        output.append({"role": "system", "content": block_1})
        output.append({"role": "system", "content": f"[GLOBAL_STATE_KV]\n{block_2}"})
        output.extend(recent_history)
        output.append({"role": "user", "content": f"[LATEST_INPUT]\n{block_4}"})
        return output
