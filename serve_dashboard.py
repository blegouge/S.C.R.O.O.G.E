#!/usr/bin/env python3
"""Tiny HTTP dashboard for Telemetry Token (localhost only)."""

from __future__ import annotations

import http.server
import json
import os
import pathlib
import re
import secrets
import shutil
import subprocess
import sys
from http.server import SimpleHTTPRequestHandler
from typing import Any

from providers_config import get_data_dir, get_enabled_providers, get_rtk_cwd
from telemetry_metrics import summarize_layer_kpis, summarize_report


def package_root() -> pathlib.Path:
    """Bundle HTML/icon: PyInstaller extract dir when frozen; else script directory."""
    if getattr(sys, "frozen", False):
        return pathlib.Path(sys._MEIPASS)  # type: ignore[attr-defined]

    return pathlib.Path(__file__).resolve().parent


def get_paths(source: str) -> tuple[pathlib.Path, pathlib.Path]:
    """Return (log_path, layout_path) for source ('cursor', 'antigravity', 'claude', 'gemini', 'hermes')."""
    d = get_data_dir(source)
    if d is None:
        # Fallback to cursor default if provider not found
        d = pathlib.Path.home() / ".cursor" / "token-telemetry"
    d.mkdir(parents=True, exist_ok=True)
    return d / "events.jsonl", d / "dashboard-layout.json"


DASH = package_root() / "dashboard.html"
ICON = package_root() / "icon.jpg"  # app logo / favicon (JPEG)
ICON_FALLBACK = package_root() / "docs" / "fr" / "assets" / "icon.jpg"
JS = package_root() / "dashboard.js"
CSS = package_root() / "dashboard.css"
HOST = os.environ.get("TELEMETRY_HOST", "127.0.0.1")
PORT = int(os.environ.get("TELEMETRY_PORT", 8765))


def icon_path() -> pathlib.Path | None:
    """Return the dashboard icon path, supporting legacy and docs asset layouts."""
    for candidate in (ICON, ICON_FALLBACK):
        if candidate.is_file():
            return candidate
    return None


def _rtk_cmd_candidates() -> list[list[str]]:
    candidates: list[list[str]] = []
    seen: set[str] = set()
    env = _patched_env()
    which_rtk = shutil.which("rtk", path=env.get("PATH"))
    env_rtk = os.environ.get("RTK_BIN", "").strip()
    common_paths = [
        env_rtk,
        which_rtk,
        "/opt/homebrew/bin/rtk",
        "/usr/local/bin/rtk",
        str(pathlib.Path.home() / ".local" / "bin" / "rtk"),
        "/usr/bin/rtk",
    ]
    for path in common_paths:
        if not path or path in seen:
            continue
        if pathlib.Path(path).is_absolute() and not pathlib.Path(path).is_file():
            continue
        seen.add(path)
        candidates.append([path])
    if not candidates:
        candidates.append(["rtk"])
    return candidates


def _patched_env() -> dict[str, str]:
    env = dict(os.environ)
    path = env.get("PATH", "")
    extras = ["/opt/homebrew/bin", "/usr/local/bin", "/usr/bin", "/bin"]
    merged = path.split(":") if path else []
    for entry in extras:
        if entry not in merged:
            merged.append(entry)
    env["PATH"] = ":".join(merged)
    return env


def _extract_json_object(text: str) -> dict[str, object] | None:
    stripped = text.strip()
    if not stripped:
        return None
    try:
        parsed = json.loads(stripped)
        if isinstance(parsed, dict):
            return parsed
        return {"data": parsed}
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{[\s\S]*\}", stripped)
    if not match:
        return None
    try:
        parsed = json.loads(match.group(0))
        if isinstance(parsed, dict):
            return parsed
        return {"data": parsed}
    except json.JSONDecodeError:
        return None


import threading
import time

_RTK_GAIN_LOCK = threading.Lock()
_RTK_GAIN_CACHE: dict[str, tuple[float, dict[str, Any]]] = {}
_RTK_CACHE_TTL = 30.0


def load_rtk_gain(project: bool = False, source: str = "cursor") -> dict[str, object]:
    cache_key = f"{project}:{source}"
    now = time.time()
    with _RTK_GAIN_LOCK:
        if cache_key in _RTK_GAIN_CACHE:
            ts, val = _RTK_GAIN_CACHE[cache_key]
            if now - ts < _RTK_CACHE_TTL:
                return val

    # -d: per-day saved_tokens for counterfactual charts in the dashboard
    args = ["gain", "-d", "--format", "json"]
    if project:
        args.append("--project")

    env = _patched_env()
    rtk_cwd = get_rtk_cwd(source)
    cwd = str(rtk_cwd) if rtk_cwd is not None else None

    errors: list[str] = []
    for base in _rtk_cmd_candidates():
        cmd = [*base, *args]
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=8,
                check=False,
                env=env,
                cwd=cwd,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            errors.append(f"{' '.join(cmd)}: {exc}")
            continue

        if proc.returncode != 0:
            err = (proc.stderr or proc.stdout or "unknown error").strip()[:400]
            errors.append(f"{' '.join(cmd)}: {err}")
            continue

        payload = _extract_json_object(proc.stdout or "")
        if payload is None:
            raw_preview = (proc.stdout or "").strip()[:400]
            errors.append(f"{' '.join(cmd)}: invalid json output ({raw_preview})")
            continue

        payload["ok"] = True
        payload["scope"] = "project" if project else "global"
        payload["rtk_command"] = " ".join(cmd)
        with _RTK_GAIN_LOCK:
            _RTK_GAIN_CACHE[cache_key] = (time.time(), payload)
        return payload

    return {
        "ok": False,
        "scope": "project" if project else "global",
        "error": "; ".join(errors)[:800] if errors else "rtk not found",
    }


def _load_dashboard_layout(layout_path: pathlib.Path) -> dict[str, object]:
    default: dict[str, object] = {"version": 1, "order": None, "collapsed": []}
    if not layout_path.is_file():
        return default
    try:
        raw = json.loads(layout_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default
    if not isinstance(raw, dict):
        return default
    order = raw.get("order")
    collapsed = raw.get("collapsed")
    return {
        "version": 1,
        "order": order if isinstance(order, list) else None,
        "collapsed": collapsed if isinstance(collapsed, list) else [],
    }


def _save_dashboard_layout(
    layout_path: pathlib.Path, payload: dict[str, object]
) -> dict[str, object]:
    order = payload.get("order")
    collapsed = payload.get("collapsed")
    clean: dict[str, object] = {
        "version": 1,
        "order": [str(x) for x in order] if isinstance(order, list) else [],
        "collapsed": [str(x) for x in collapsed] if isinstance(collapsed, list) else [],
    }
    layout_path.write_text(json.dumps(clean, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return clean


_security_token = secrets.token_hex(16)


class DashboardHandler(SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        return

    def validate_request(self) -> bool:
        # 1. Host Validation
        host = self.headers.get("Host", "")
        # Extract hostname before optional port
        host_name = host.split(":")[0].lower()
        if host_name not in ("127.0.0.1", "localhost"):
            self.send_error(400, "Invalid Host header")
            return False

        # 2. Token Validation (only for /api/* paths)
        import urllib.parse

        parsed = urllib.parse.urlparse(self.path)
        if parsed.path.startswith("/api/"):
            token = self.headers.get("X-Telemetry-Token")
            if not token:
                query = urllib.parse.parse_qs(parsed.query)
                token = query.get("token", [None])[0]
            if token != _security_token:
                self.send_error(403, "Forbidden: Invalid security token")
                return False
        return True

    def do_GET(self) -> None:  # noqa: N802
        if not self.validate_request():
            return
        import urllib.parse

        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)
        source = query.get("source", ["cursor"])[0]

        log_path, layout_path = get_paths(source)

        from telemetry_db import fetch_events_from_db, sync_source

        try:
            sync_source(source, log_path)
        except Exception as e:
            sys.stderr.write(f"[serve_dashboard] SQLite sync failed for {source}: {e}\n")

        if path == "/api/events":
            rows = fetch_events_from_db(source)
            payload = json.dumps(rows, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return
        if path == "/api/report-summary":
            rows = fetch_events_from_db(source)
            payload_obj = summarize_report(rows)
            payload_obj["ok"] = True
            payload = json.dumps(payload_obj, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return
        if path == "/api/layer-kpis":
            rows = fetch_events_from_db(source)
            rtk_gain = load_rtk_gain(project=False, source=source)
            payload_obj = summarize_layer_kpis(rows, rtk_gain=rtk_gain)
            payload_obj["ok"] = True
            payload = json.dumps(payload_obj, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return
        if path == "/api/rtk-gain":
            payload_obj = {
                "global": load_rtk_gain(project=False, source=source),
                "project": load_rtk_gain(project=True, source=source),
            }
            payload = json.dumps(payload_obj, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return
        if path == "/api/dashboard-layout":
            payload_obj = _load_dashboard_layout(layout_path)
            payload_obj["ok"] = True
            payload = json.dumps(payload_obj, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return
        if path == "/api/providers":
            providers = get_enabled_providers()
            payload = json.dumps(providers, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return
        if path in ("/", "/index.html"):
            html_content = (
                DASH.read_text(encoding="utf-8")
                if DASH.is_file()
                else "<pre>dashboard.html missing</pre>"
            )
            token_script = f"""<script>
  window.__TELEMETRY_TOKEN__ = {json.dumps(_security_token)};
  const originalFetch = window.fetch;
  window.fetch = function(input, init) {{
    if (typeof input === 'string' && input.startsWith('/api/')) {{
      init = init || {{}};
      init.headers = init.headers || {{}};
      if (init.headers instanceof Headers) {{
        init.headers.set('X-Telemetry-Token', window.__TELEMETRY_TOKEN__);
      }} else if (Array.isArray(init.headers)) {{
        init.headers.push(['X-Telemetry-Token', window.__TELEMETRY_TOKEN__]);
      }} else {{
        init.headers['X-Telemetry-Token'] = window.__TELEMETRY_TOKEN__;
      }}
    }}
    return originalFetch(input, init);
  }};
</script>"""
            if "<head>" in html_content:
                html_content = html_content.replace("<head>", f"<head>\n  {token_script}")
            else:
                html_content = html_content.replace("<body>", f"<body>\n  {token_script}")

            body = html_content.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        # Serve static files dynamically and securely
        target_file = (package_root() / path.lstrip("/")).resolve()
        pkg_root = package_root().resolve()
        if getattr(sys, "frozen", False) and pkg_root.name in ("Frameworks", "Resources", "MacOS"):
            pkg_root = pkg_root.parent
        try:
            if target_file.is_file() and target_file.is_relative_to(pkg_root):
                suffix = target_file.suffix.lower()
                safe_extensions = {".js", ".css", ".ico", ".jpg", ".png", ".html"}
                if suffix in safe_extensions:
                    mime_types = {
                        ".js": "application/javascript; charset=utf-8",
                        ".css": "text/css; charset=utf-8",
                        ".ico": "image/x-icon",
                        ".jpg": "image/jpeg",
                        ".png": "image/png",
                        ".html": "text/html; charset=utf-8",
                    }
                    content_type = mime_types.get(suffix, "application/octet-stream")
                    body = target_file.read_bytes()
                    self.send_response(200)
                    self.send_header("Content-Type", content_type)
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                    return
        except ValueError:
            pass

        if path in ("/icon.jpg", "/favicon.ico", "/docs/fr/assets/icon.jpg"):
            icon = icon_path()
            if icon is None:
                self.send_error(404, "Icon not found")
                return
            data = icon.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "image/jpeg")
            self.send_header("Cache-Control", "public, max-age=86400")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        self.send_error(404, "Not found")

    def do_POST(self) -> None:  # noqa: N802
        if not self.validate_request():
            return
        import urllib.parse

        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)
        source = query.get("source", ["cursor"])[0]

        log_path, layout_path = get_paths(source)

        if path != "/api/dashboard-layout":
            self.send_error(404, "Not found")
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            length = 0
        if length < 0 or length > 65536:
            self.send_error(400, "Invalid body")
            return
        raw = self.rfile.read(length) if length else b""
        try:
            payload_in = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            self.send_error(400, "Invalid JSON")
            return
        if not isinstance(payload_in, dict):
            self.send_error(400, "Expected JSON object")
            return
        saved = _save_dashboard_layout(layout_path, payload_in)
        payload_obj = {"ok": True, **saved}
        payload = json.dumps(payload_obj, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


def make_httpd(preferred_port: int = PORT) -> tuple[http.server.HTTPServer, int]:
    """Bind to preferred_port if free; otherwise let the OS assign a free port."""
    klass = getattr(http.server, "ThreadingHTTPServer", http.server.HTTPServer)
    try:
        httpd = klass((HOST, preferred_port), DashboardHandler)
        return httpd, preferred_port
    except OSError:
        httpd = klass((HOST, 0), DashboardHandler)
        actual = int(httpd.server_address[1])
        return httpd, actual


def main() -> None:
    providers = get_enabled_providers()
    if providers:
        paths_info = " | ".join([f"{p['label']} = {get_paths(p['id'])[0]}" for p in providers])
    else:
        paths_info = "(no providers enabled)"
    print(f"Telemetry Token: {paths_info}")
    httpd, port = make_httpd()
    print(f"Ouvre http://{HOST}:{port}/ (CTRL+C pour arrêter)")
    httpd.serve_forever()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nArrêt du serveur.")
