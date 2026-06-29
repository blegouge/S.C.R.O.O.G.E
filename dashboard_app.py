#!/usr/bin/env python3
"""Open the telemetry dashboard in a native desktop window (no browser tab).

Starts the local HTTP handler in a background thread; shuts down when you close the window.

Install once:
  pip install -r ~/.cursor/token-telemetry/requirements-desktop.txt
"""

from __future__ import annotations

import pathlib
import sys
import threading

_ROOT = pathlib.Path(__file__).resolve().parent
_REQ = _ROOT / "requirements-desktop.txt"

try:
    import webview
except ImportError:
    sys.stderr.write(
        "Dependency missing: run\n"
        f'  pip install -r "{_REQ}"\n'
        "(or: pip install 'pywebview>=5')\n",
    )
    sys.exit(1)

from serve_dashboard import HOST, make_httpd


def main() -> None:
    httpd, port = make_httpd()
    url = f"http://{HOST}:{port}/"
    worker = threading.Thread(target=httpd.serve_forever, name="telemetry-http", daemon=True)
    worker.start()

    try:
        webview.create_window(
            "Cursor Telemetry",
            url,
            width=1280,
            height=840,
            resizable=True,
        )
        webview.start()
    finally:
        httpd.shutdown()
        worker.join(timeout=5.0)


if __name__ == "__main__":
    main()
