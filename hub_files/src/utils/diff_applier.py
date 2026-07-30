#!/usr/bin/env python3
"""
Parse and apply Diff-Only SEARCH/REPLACE blocks from agent text.

Deterministic: no LLM round-trip. Raises DiffApplyError when SEARCH is missing or ambiguous.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import UTC
from pathlib import Path

MARKER_SEARCH = "<<<<<<< SEARCH"
MARKER_SEP = "======="
MARKER_REPLACE = ">>>>>>> REPLACE"

_PATH_RE = re.compile(
    r"(?im)^(?:path|file)\s*:\s*(?P<path>.+?)\s*$",
)
_BLOCK_RE = re.compile(
    rf"{re.escape(MARKER_SEARCH)}\s*\n(?P<search>.*?)\n{re.escape(MARKER_SEP)}\s*\n"
    rf"(?P<replace>.*?)\n{re.escape(MARKER_REPLACE)}",
    re.DOTALL,
)


class DiffApplyError(Exception):
    """Base error for diff application failures."""


class SearchNotFoundError(DiffApplyError):
    """SEARCH snippet not found in target file."""


class AmbiguousSearchError(DiffApplyError):
    """SEARCH snippet matches more than once — add more context lines."""


class WorkspaceNotFoundError(DiffApplyError):
    """Could not resolve a workspace root for a relative path."""


@dataclass(frozen=True, slots=True)
class DiffBlock:
    """One SEARCH/REPLACE hunk."""

    path: str
    search: str
    replace: str
    line_number: int = 0  # 1-based line of path: in source text (for errors)


@dataclass(slots=True)
class ApplyStats:
    """Token proxy savings for one apply run."""

    blocks_parsed: int = 0
    blocks_applied: int = 0
    files_touched: int = 0
    original_file_chars: int = 0
    patch_output_chars: int = 0
    replace_line_count: int = 0
    estimated_chars_saved: int = 0

    def to_log_dict(self) -> dict[str, int]:
        return {
            "blocks_parsed": self.blocks_parsed,
            "blocks_applied": self.blocks_applied,
            "files_touched": self.files_touched,
            "original_file_chars": self.original_file_chars,
            "patch_output_chars": self.patch_output_chars,
            "replace_line_count": self.replace_line_count,
            "estimated_chars_saved": self.estimated_chars_saved,
        }


@dataclass(slots=True)
class ApplyResult:
    """Outcome of applying all blocks in a text blob."""

    applied: list[tuple[str, Path]] = field(default_factory=list)
    stats: ApplyStats = field(default_factory=ApplyStats)
    errors: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def _strip_markdown_fences(text: str) -> str:
    """Remove accidental ``` wrappers around hunks."""
    stripped = text.strip()
    if stripped.startswith("```") and stripped.endswith("```"):
        inner = stripped.split("\n", 1)
        if len(inner) == 2:
            body = inner[1]
            if body.endswith("```"):
                body = body[: body.rfind("```")].rstrip("\n")
            return body
    return text


def _normalize_newlines(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def extract_response_text(payload: dict) -> str:
    """Pull assistant/subagent text from hook JSON."""
    for key in ("text", "summary", "response", "content"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value

    message = payload.get("message")
    if isinstance(message, str) and message.strip():
        return message
    if isinstance(message, dict):
        for key in ("content", "text", "value"):
            value = message.get(key)
            if isinstance(value, str) and value.strip():
                return value
            if isinstance(value, list):
                chunks: list[str] = []
                for part in value:
                    if isinstance(part, str) and part.strip():
                        chunks.append(part)
                    elif isinstance(part, dict):
                        piece = part.get("text") or part.get("content")
                        if isinstance(piece, str) and piece.strip():
                            chunks.append(piece)
                if chunks:
                    return "\n".join(chunks)

    parts: list[str] = []
    for value in _walk_strings(payload):
        if MARKER_SEARCH in value or "path:" in value.lower():
            parts.append(value)
    return "\n\n".join(parts)


def _walk_strings(obj: object, depth: int = 0) -> Iterable[str]:
    if depth > 12:
        return
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for value in obj.values():
            yield from _walk_strings(value, depth + 1)
    elif isinstance(obj, list):
        for item in obj[:80]:
            yield from _walk_strings(item, depth + 1)


def resolve_workspace_roots(payload: dict) -> list[Path]:
    """Resolve workspace folder(s) from hook payload and environment."""
    roots: list[Path] = []

    def _add(path: str | Path) -> None:
        candidate = Path(path).expanduser()
        if candidate.is_dir() and candidate not in roots:
            roots.append(candidate.resolve())

    for key in ("workspace_roots", "workspaceRoots"):
        value = payload.get(key)
        if isinstance(value, list):
            for item in value:
                if isinstance(item, str) and item.strip():
                    _add(item)

    for key in (
        "workspace",
        "workspaceRoot",
        "workspace_root",
        "projectPath",
        "project_root",
        "rootPath",
        "cwd",
        "folder",
    ):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            _add(value)

    for env_key in ("CURSOR_WORKSPACE", "CURSOR_PROJECT_DIR", "WORKSPACE_FOLDER"):
        env_val = __import__("os").environ.get(env_key, "").strip()
        if env_val:
            _add(env_val)

    cwd = Path.cwd()
    cursor_home = Path.home() / ".cursor"
    if cwd.resolve() != cursor_home.resolve() and cwd.is_dir():
        _add(cwd)

    return roots


def parse_blocks(text: str) -> list[DiffBlock]:
    """
    Parse path-prefixed SEARCH/REPLACE hunks from agent output.

    Supports multiple hunks per file; reuses the last path: when omitted.
    """
    cleaned = _strip_markdown_fences(text)
    if MARKER_SEARCH not in cleaned:
        return []

    blocks: list[DiffBlock] = []
    current_path = ""
    lines = cleaned.splitlines()
    idx = 0
    while idx < len(lines):
        path_match = _PATH_RE.match(lines[idx])
        if path_match:
            current_path = path_match.group("path").strip().strip("\"'")
            idx += 1
            continue

        if lines[idx].strip() == MARKER_SEARCH:
            start_line = idx + 1
            idx += 1
            search_lines: list[str] = []
            while idx < len(lines) and lines[idx].strip() != MARKER_SEP:
                search_lines.append(lines[idx])
                idx += 1
            if idx >= len(lines) or lines[idx].strip() != MARKER_SEP:
                break
            idx += 1
            replace_lines: list[str] = []
            while idx < len(lines) and lines[idx].strip() != MARKER_REPLACE:
                replace_lines.append(lines[idx])
                idx += 1
            if idx >= len(lines) or lines[idx].strip() != MARKER_REPLACE:
                break
            if not current_path:
                continue
            blocks.append(
                DiffBlock(
                    path=current_path,
                    search="\n".join(search_lines),
                    replace="\n".join(replace_lines),
                    line_number=start_line,
                )
            )
            idx += 1
            continue
        idx += 1

    if blocks:
        return blocks

    # Fallback: regex scan (path immediately before each block)
    last_path = ""
    for match in _BLOCK_RE.finditer(cleaned):
        prefix = cleaned[: match.start()]
        path_matches = list(_PATH_RE.finditer(prefix))
        if path_matches:
            last_path = path_matches[-1].group("path").strip().strip("\"'")
        if last_path:
            blocks.append(
                DiffBlock(
                    path=last_path,
                    search=match.group("search"),
                    replace=match.group("replace"),
                    line_number=prefix.count("\n") + 1,
                )
            )
    return blocks


def _resolve_file(path_str: str, roots: list[Path]) -> Path:
    raw = Path(path_str.strip().strip("\"'"))
    if raw.is_absolute():
        return raw.resolve()
    if not roots:
        raise WorkspaceNotFoundError(f"No workspace root available for relative path '{path_str}'")
    for root in roots:
        candidate = (root / raw).resolve()
        if candidate.exists():
            return candidate
    return (roots[0] / raw).resolve()


def _count_occurrences(haystack: str, needle: str) -> int:
    if not needle:
        return 0
    count = start = 0
    while True:
        pos = haystack.find(needle, start)
        if pos == -1:
            return count
        count += 1
        start = pos + max(1, len(needle))
    return count


def _apply_one(
    file_path: Path,
    search: str,
    replace: str,
) -> tuple[str, bool]:
    """
    Apply a single hunk. Returns (new_content, used_normalized_match).
    """
    if file_path.exists():
        original = file_path.read_text(encoding="utf-8")
    else:
        original = ""

    if not search and not original:
        return replace, False

    if not search and original:
        raise DiffApplyError(f"{file_path}: empty SEARCH on existing file — provide context lines")

    if search in original:
        count = _count_occurrences(original, search)
        if count > 1:
            raise AmbiguousSearchError(
                f"{file_path}: SEARCH matches {count} times — add 3–8 unique context lines"
            )
        return original.replace(search, replace, 1), False

    norm_orig = _normalize_newlines(original)
    norm_search = _normalize_newlines(search)
    norm_replace = _normalize_newlines(replace)
    if norm_search in norm_orig:
        count = _count_occurrences(norm_orig, norm_search)
        if count > 1:
            raise AmbiguousSearchError(
                f"{file_path}: SEARCH matches {count} times (normalized) — add context"
            )
        updated = norm_orig.replace(norm_search, norm_replace, 1)
        return updated, True

    raise SearchNotFoundError(f"{file_path}: SEARCH not found — verify verbatim copy from disk")


def apply_blocks(
    blocks: list[DiffBlock],
    workspace_roots: list[Path],
    *,
    dry_run: bool = False,
) -> ApplyResult:
    """Apply all hunks; aggregate stats and errors."""
    result = ApplyResult()
    result.stats.blocks_parsed = len(blocks)
    if not blocks:
        return result

    touched_files: set[Path] = set()
    file_original_chars: dict[Path, int] = {}

    for block in blocks:
        try:
            target = _resolve_file(block.path, workspace_roots)
        except WorkspaceNotFoundError as exc:
            result.errors.append(str(exc))
            continue

        if target not in file_original_chars:
            if target.exists():
                file_original_chars[target] = len(target.read_text(encoding="utf-8"))
            else:
                file_original_chars[target] = 0

        patch_chars = len(block.search) + len(block.replace)
        result.stats.patch_output_chars += patch_chars
        result.stats.replace_line_count += (
            0 if not block.replace else len(block.replace.splitlines())
        )

        try:
            current = target.read_text(encoding="utf-8") if target.exists() else ""
            new_content, _normalized = _apply_one(target, block.search, block.replace)
            if not dry_run:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(new_content, encoding="utf-8")
            result.applied.append((block.path, target))
            touched_files.add(target)
            result.stats.blocks_applied += 1
        except SearchNotFoundError as exc:
            result.errors.append(f"{block.path} (line ~{block.line_number}): {exc}")
        except AmbiguousSearchError as exc:
            result.errors.append(f"{block.path} (line ~{block.line_number}): {exc}")
        except DiffApplyError as exc:
            result.errors.append(f"{block.path}: {exc}")

    result.stats.files_touched = len(touched_files)
    result.stats.original_file_chars = sum(file_original_chars.values())
    result.stats.estimated_chars_saved = max(
        0,
        result.stats.original_file_chars - result.stats.patch_output_chars,
    )
    return result


def apply_text(
    text: str,
    workspace_roots: list[Path],
    *,
    dry_run: bool = False,
) -> ApplyResult:
    """Parse and apply blocks from raw agent text."""
    blocks = parse_blocks(text)
    return apply_blocks(blocks, workspace_roots, dry_run=dry_run)


def log_savings(stats: ApplyStats, *, stream=None) -> None:
    """Print token proxy savings to stderr (visible in Hooks output channel)."""
    stream = stream or sys.stderr
    msg = (
        "[diff-only] "
        f"blocks={stats.blocks_applied}/{stats.blocks_parsed} "
        f"files={stats.files_touched} "
        f"original_chars={stats.original_file_chars} "
        f"patch_chars={stats.patch_output_chars} "
        f"saved≈{stats.estimated_chars_saved} chars "
        f"replace_lines={stats.replace_line_count}"
    )
    stream.write(msg + "\n")
    stream.flush()


def append_telemetry(stats: ApplyStats, event: str, errors: list[str]) -> None:
    """Append one row to token-telemetry events.jsonl."""
    from datetime import datetime

    row = {
        "ts": datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "event": event,
        "diff_only": stats.to_log_dict(),
        "diff_errors": errors[:20],
    }
    log_dir = Path.home() / ".cursor" / "token-telemetry"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "events.jsonl"
    with log_file.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def main(argv: list[str] | None = None) -> int:
    """CLI: python diff_applier.py [--dry-run] [text-file|-]"""
    import argparse

    parser = argparse.ArgumentParser(description="Apply Diff-Only SEARCH/REPLACE blocks")
    parser.add_argument(
        "input",
        nargs="?",
        default="-",
        help="Text file with blocks, or '-' for stdin",
    )
    parser.add_argument("--dry-run", action="store_true", help="Parse only, do not write")
    parser.add_argument(
        "--workspace",
        action="append",
        dest="workspaces",
        default=[],
        help="Workspace root (repeatable)",
    )
    args = parser.parse_args(argv)

    if args.input == "-":
        text = sys.stdin.read()
    else:
        text = Path(args.input).read_text(encoding="utf-8")

    roots = [Path(p).expanduser().resolve() for p in args.workspaces]
    if not roots:
        roots = [Path.cwd().resolve()]

    result = apply_text(text, roots, dry_run=args.dry_run)
    log_savings(result.stats)
    if result.errors:
        for err in result.errors:
            print(f"ERROR: {err}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
