# Token telemetry (local proxy metrics)

> **Emplacement (juin 2026)** : application dans `~/www/private/TelemetryToken` ; données persistantes inchangées dans `~/.cursor/token-telemetry/` (`events.jsonl`, `dashboard-layout.json`, `diff-only-last-text.txt`). Variables : `CURSOR_TOKEN_TELEMETRY_APP`, `CURSOR_TOKEN_TELEMETRY_DATA_DIR`.


English comments per hub convention; user-facing notes can stay French elsewhere.

## What this measures

Hooks call `hooks/token-telemetry.py` after:

- **`postToolUse`** — Cursor sends JSON that usually includes tool output (already truncated/editor-dependent).
- **`afterAgentResponse`** — JSON that typically includes assistant-visible text blocks.

Additionally:

- `hooks/semantic-compress-pretool.py` writes **`subagentLaunch`** rows (Task subagent start: type, skill, **Claw Compactor** / LLMLingua, `compression_backend`, end-to-end saved tokens, correlation ids).
- `hooks/tt-subagent-stop.sh` writes **`subagentStop`** rows (summary/transcript proxy size).
- **Fallback:** when Cursor does not fire `subagentStop`, `postToolUse` with `tool_name=Task` is logged as **`subagentStop`** with `subagent_stop_source=postToolUse_fallback`.
- Diagnostic: `~/.cursor/bin/diagnose-subagent-telemetry.sh`
- `afterAgentResponse` rows may include **`input_tokens` / `output_tokens`** when Cursor exposes them.

Python walks **string fields** inside that JSON and counts characters, then derives **`approx_tokens = ceil(chars / 4)`** — a coarse proxy like “English-like GPT tokenization guess”.

For `afterAgentResponse`, the hook also extracts a structured signal for the **Consumption report** block (`consumption_present`, `consumption_complete`, `work_mode`, `tool_activity`, `token_risk`, etc.) when present in the assistant response text.

**Compliance hooks** (also in `report.py` + dashboard bandeau « Compliance hooks »):

| Event | Source | KPI |
|-------|--------|-----|
| `afterAgentResponse` | `token-telemetry.py` | `consumption_present` / `consumption_complete` (5 champs) |
| `consumptionReportCompliance` | `stop-compliance.py` | relances hook stop, ok, abandon |
| `taskBriefValidation` | `semantic-compress-pretool.py` | brief pass / denied (Task deny) |
| `subagentLaunch` | pretool | `idempotent_context_injected` |

Cursor **does not** expose provider-reported billed usage inside these payloads (often `usage`/`tokens` absent). Dashboard = **orientation**, not accountant truth.

Compare with **`rtk gain`** for **shell** compression savings.

## Edit / Tab hooks

`hooks.json` registers **`afterFileEdit`** (agent edits applied to disk) and **`afterTabFileEdit`** (Tab inline completion accepted). Rows include **`lines_added` / `lines_removed`** via `difflib` on payloads (shape varies per Cursor release).

Composer **reject** counts are **not** available from public Cursor hooks (not shown in the dashboard).

## Files

| Path | Role |
|------|------|
| `token-telemetry/icon.jpg` | navbar logo + favicon (served also as `/favicon.ico` when using `serve_dashboard.py`) |
| `~/.cursor/token-telemetry/events.jsonl` | append-only JSON log |
| `token-telemetry/dashboard.html` | Dashboard UI — dark neon “terminal” style, KPI cards, histogram + donut, tables, theme toggle & file upload |
| `token-telemetry/serve_dashboard.py` | bind `127.0.0.1:8765`; JSON log read from **`~/.cursor/token-telemetry/events.jsonl`** (same when frozen), plus `/api/rtk-gain` for RTK savings (global + project). |
| `token-telemetry/dashboard_app.py` | Fenêtre système (**pywebview**), serveur HTTP en thread. |
| `token-telemetry/requirements-desktop.txt` / `requirements-native-build.txt` | Dépendances optionnelles (webview seul vs build `.app`). |
| `token-telemetry/build_macos_app.sh` | Build **`dist/Token Telemetry.app`** (PyInstaller). |
| `token-telemetry/native_app/TokenTelemetry.spec` | Spec PyInstaller. |
| `token-telemetry/report.py` | no-server CLI totals |

## View

Terminal:

```bash
python3 ~/.cursor/token-telemetry/report.py
```

Web (after some agent turns):

```bash
python3 ~/.cursor/token-telemetry/serve_dashboard.py
# open http://127.0.0.1:8765/
```

### Application macOS (`.app` autonome)

Pour une **app dans le Finder / Dock**, sans installer Python avec pywebview vous-même : compile une fois depuis ce dossier (**macOS uniquement**) :

```bash
cd ~/.cursor/token-telemetry
./build_macos_app.sh
```

Le script :

- utilise un venv `./.venv-build` (modifiable via `TOKEN_TELEMETRY_BUILD_VENV`) ;
- installe **`requirements-native-build.txt`** (`pywebview` + `pyinstaller`) ;
- génère éventuellement **`native_app/Token Telemetry.icns`** à partir de `icon.jpg` ;
- écrit **`dist/Token Telemetry.app`** et tente une signature **ad hoc** (`codesign --sign -`) pour satisfaire WebKit.

Ensuite : glisser **`Token Telemetry.app`** dans **Applications** (ou le lancer depuis `dist/`). Les données lues restent **`~/.cursor/token-telemetry/events.jsonl`** (aligné avec les hooks Cursor) ; seuls le HTML et l’icône sont embarqués dans le bundle.

**Gatekeeper** : si macOS bloque l’ouverture (*app non vérifiée*), clic droit → **Ouvrir**, ou `xattr -dr com.apple.quarantine "/chemin/vers/Token Telemetry.app"` une fois. Pour une distribution sérieuse il faudrait un **Apple Developer ID** et `codesign` / notarization.

**Architecture** : le binaire reflète l’interpréteur utilisé lors du build (ex. Python Homebrew **x86_64** sous Rosetta ≠ natif Apple Silicon). Rebuild sur la machine cible ou avec un Python **arm64** si besoin.

### Desktop window (native WebKit wrapper)

Use this when you want a **standalone window** instead of Safari/Chrome plus a foreground terminal thread.

Install once (`pywebview`). On macOS/Homebrew Python (PEP 668), use a venv under this folder rather than `--break-system-packages`:

```bash
cd ~/.cursor/token-telemetry
python3 -m venv .venv-desktop
source .venv-desktop/bin/activate
pip install -r requirements-desktop.txt
```

Then run (with that venv activated, or invoke its interpreter explicitly):

```bash
~/.cursor/token-telemetry/.venv-desktop/bin/python ~/.cursor/token-telemetry/dashboard_app.py
```

Or from an activated shell:

```bash
python ~/.cursor/token-telemetry/dashboard_app.py
```

The HTTP server (`127.0.0.1`, default port `8765` or next free port) runs inside the same Python process until you close the window. Opening the URL in two places at once (browser + app) remains possible while that process is alive.

macOS Dock / double-click without tying up a Terminal session: wrap the same `python3 … dashboard_app.py` line in Automator (**Application**) or Shortcuts (**Run Shell Script**), optionally with `nohup … & disown`-style wrappers if you spawn it from Automator scripts that exit immediately — many users keep a pinned Automator `.app` in the Dock.

The dashboard header includes a **Grafana-like refresh control**: immediate **Rafraîchir** (loads `/api/events`) and an interval menu (**Désactivé**, **5 min**, **30 min**, **1 h**). The choice is stored in **`localStorage`**. **Charger un fichier** switches to offline JSONL and resets auto-refresh to **Désactivé**; use **Rafraîchir** again to pull live **`events.jsonl`** from the server, then re-enable an interval if you want.

RTK integration requires `rtk` to be available on the PATH used by `serve_dashboard.py`; otherwise the RTK KPI falls back to “indisponible”.

Global gains KPI combines:

- RTK global saved tokens (`rtk gain -d --format json`, including per-day `saved_tokens`)
- Hook-based Task compression saved tokens (`subagentLaunch` / legacy `preToolUseCompression`), using **`compression_input_tokens` → `compression_after_tokens`** (Claw + optional LLMLingua)

### Daily gain % chart

Bar chart (always **per calendar day**): `100 × savings / (observed + savings)` where savings = RTK daily + Task compression + Diff-Only. Stays readable when billed tokens are in the millions (May 28+ spikes).

### Counterfactual chart (observed vs without optimizations)

The trend chart plots two series per time bucket (hour or day):

| Series | Meaning |
|--------|---------|
| **Consommé (observé)** | `billed_total_tokens` on `afterAgentResponse` when present; else `input_tokens`+`output_tokens`; tool/subagent proxies elsewhere |
| **Sans optimisations (estimé)** | observed + savings attributed in that bucket |

Savings attributed per bucket:

- **RTK** — `daily[].saved_tokens` from `rtk gain -d` (full day on day view; split across active hours on hour view)
- **Task compression** — `compression_*_saved*` / input→after delta on `subagentLaunch`
- **Diff-Only** — `diff_only.estimated_chars_saved / 4` on `diffOnlyApply:*`

KPI strip **Comparatif optimisations** sums the same model over the whole log window (RTK only on calendar days that appear in the log).

This is still an **estimate** (no per-subagent Cursor billing; possible overlap between parent context and hook savings). Use for trend/gain visibility, not invoicing.

Dashboard shows per-run **claw** / **llm** badges and `compression_backend` breakdown. Rebuild **`Token Telemetry.app`** after `dashboard.html` changes if you use the bundled macOS app.

**Parity with `report.py`:** subagent KPIs (launches, stops, prompt/out proxy) and **Parent billed** (average + sum + latest) use the same aggregation as the CLI (`telemetry_metrics.summarize_report`). The web UI also exposes `GET /api/report-summary`. Optional subtitle **ce tour** shows the current session only (for context). Task launches now inherit `session_id` from recent log rows when `preToolUse` omits it (`telemetry_common.enrich_correlation`).

## Privacy / rotation

Hook payload may embed code paths or secrets if the tool echoed them — keep `events.jsonl` private; rotate/delete when needed.
