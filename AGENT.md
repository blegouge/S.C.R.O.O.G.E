# S.C.R.O.O.G.E.

## Purpose

Local S.C.R.O.O.G.E. application for the Cursor hub: dashboard, CLI reports, Claw Compactor venv, and macOS `.app` build. **Persistent data** stays in `~/.cursor/token-telemetry/` (see `README-DATA.md` there).

## Stack

- Python 3.12+ (`.venv-desktop` for Claw / desktop deps, `.venv-build` for PyInstaller)
- Static dashboard: `dashboard.html` + `serve_dashboard.py` (HTTP on `127.0.0.1:8765`)
- Optional native shell: `dashboard_app.py` (pywebview), `build_macos_app.sh`

## Paths (SSOT: `telemetry_paths.py`)

| Role | Default |
|------|---------|
| App | `~/www/private/SCROOGE` (`CURSOR_TOKEN_TELEMETRY_APP`) |
| Data | `~/.cursor/token-telemetry` (`CURSOR_TOKEN_TELEMETRY_DATA_DIR`) |
| Events log | `{data}/events.jsonl` (`CURSOR_TOKEN_TELEMETRY_LOG` for tests) |

Hub hooks import this package via `CURSOR_TOKEN_TELEMETRY_APP`; see `~/.cursor/bin/telemetry-paths.sh`.

## Commands

```bash
python3 ~/www/private/SCROOGE/report.py
python3 ~/www/private/SCROOGE/serve_dashboard.py
cd ~/www/private/SCROOGE && ./build_macos_app.sh
```
