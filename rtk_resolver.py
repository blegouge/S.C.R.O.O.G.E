#!/usr/bin/env python3
"""Resolve RTK binary for TelemetryToken (terminal, frozen .app, minimal PATH)."""

from __future__ import annotations

import json
import os
import pathlib
import shutil
import subprocess
from typing import Any

from telemetry_paths import resolve_data_dir

_CACHE_NAME = "rtk-resolver-cache.json"
_PROBE_ARGS = ["gain", "-d", "--format", "json"]


def _compression_env_paths() -> list[pathlib.Path]:
    home = pathlib.Path.home()
    return [
        home / ".cursor" / "compression.env",
        home / ".gemini" / "antigravity" / "compression.env",
    ]


def _read_env_file_value(key: str) -> str:
    for env_path in _compression_env_paths():
        if not env_path.is_file():
            continue
        for raw_line in env_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, value = line.partition("=")
            if k.strip() == key:
                return value.strip().strip('"').strip("'")
    return ""


def _patched_env() -> dict[str, str]:
    env = dict(os.environ)
    path = env.get("PATH", "")
    merged = path.split(":") if path else []
    extras = [
        str(pathlib.Path.home() / ".local" / "bin"),
        "/opt/homebrew/bin",
        "/usr/local/bin",
        "/usr/bin",
        "/bin",
    ]
    for entry in extras:
        if entry and entry not in merged:
            merged.append(entry)
    env["PATH"] = ":".join(merged)
    return env


def rtk_candidate_bins() -> list[str]:
    """Ordered RTK executable paths (deduped)."""
    seen: set[str] = set()
    out: list[str] = []

    def add(path: str | None) -> None:
        if not path:
            return
        expanded = str(pathlib.Path(path).expanduser())
        if expanded in seen:
            return
        seen.add(expanded)
        out.append(expanded)

    add(os.environ.get("RTK_BIN", "").strip())
    add(_read_env_file_value("RTK_BIN"))

    cache_path = resolve_data_dir() / _CACHE_NAME
    if cache_path.is_file():
        try:
            cached = json.loads(cache_path.read_text(encoding="utf-8"))
            if isinstance(cached, dict) and cached.get("ok") is True:
                add(str(cached.get("rtk_bin") or ""))
        except (OSError, json.JSONDecodeError):
            pass

    env = _patched_env()
    add(shutil.which("rtk", path=env.get("PATH")))

    for path in (
        "/opt/homebrew/bin/rtk",
        "/usr/local/bin/rtk",
        str(pathlib.Path.home() / ".local/bin/rtk"),
        "/usr/bin/rtk",
    ):
        if pathlib.Path(path).is_file():
            add(path)

    add("rtk")
    return out


def _cache_path() -> pathlib.Path:
    return resolve_data_dir() / _CACHE_NAME


def _write_cache(rtk_bin: str) -> None:
    payload = {
        "ok": True,
        "rtk_bin": rtk_bin,
        "updated_ts": __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z"),
    }
    path = _cache_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False) + "\n", encoding="utf-8")


def probe_rtk_bin(rtk_bin: str, *, cwd: str | None = None, timeout: float = 8.0) -> dict[str, Any]:
    env = _patched_env()
    cmd = [rtk_bin, *_PROBE_ARGS]
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
            env=env,
            cwd=cwd,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"ok": False, "rtk_bin": rtk_bin, "error": str(exc)[:400]}

    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "unknown error").strip()[:400]
        return {"ok": False, "rtk_bin": rtk_bin, "error": err, "returncode": proc.returncode}

    stripped = (proc.stdout or "").strip()
    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError:
        return {
            "ok": False,
            "rtk_bin": rtk_bin,
            "error": f"invalid json ({stripped[:120]})",
        }

    if isinstance(parsed, dict):
        _write_cache(rtk_bin)
        return {"ok": True, "rtk_bin": rtk_bin, "payload_keys": list(parsed.keys())[:12]}
    return {"ok": False, "rtk_bin": rtk_bin, "error": "json root is not an object"}


def resolve_rtk_command(*, cwd: str | None = None) -> tuple[list[str] | None, list[dict[str, Any]]]:
    """Return ([rtk_bin], attempts) — first working candidate or None."""
    attempts: list[dict[str, Any]] = []
    for candidate in rtk_candidate_bins():
        result = probe_rtk_bin(candidate, cwd=cwd, timeout=4.0)
        attempts.append(result)
        if result.get("ok") is True:
            return [candidate], attempts
    return None, attempts


def diagnose_rtk(*, cwd: str | None = None, frozen: bool | None = None) -> dict[str, Any]:
    if frozen is None:
        import sys

        frozen = bool(getattr(sys, "frozen", False))

    cmd, attempts = resolve_rtk_command(cwd=cwd)
    return {
        "frozen": frozen,
        "path_env_head": _patched_env().get("PATH", "")[:500],
        "candidates_tried": len(rtk_candidate_bins()),
        "resolved": cmd[0] if cmd else None,
        "ok": cmd is not None,
        "attempts": attempts[:12],
        "hint": (
            "Set RTK_BIN=/chemin/vers/rtk in ~/.cursor/compression.env "
            "then reopen Token Telemetry.app"
            if not cmd
            else None
        ),
    }
