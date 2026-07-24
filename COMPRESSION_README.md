# Semantic Prompt Compression (Claw Compactor + LLMLingua)

> **Paths in this document** use the *installed hub* layout (e.g. `~/.cursor/src/utils/…`).
> In this repository the compression engines live under `src/compaction/` and the utility
> modules under `hub_files/src/utils/` (e.g. `hub_files/src/utils/adaptive_context_manager.py`).

## Installation

```bash
cd ~/.cursor/token-telemetry
python3.12 -m venv .venv-desktop
./.venv-desktop/bin/pip install -r requirements-desktop.txt
```

Includes **Claw Compactor** (`claw-compactor[accurate]`) and optional **LLMLingua** (`llmlingua`, `transformers`, `numpy`).

Global CLI (all workspaces):

```bash
~/.cursor/bin/claw-compactor benchmark /path/to/workspace
```

Add `~/.cursor/bin` to your `PATH` if you want `claw-compactor` without the full path.

## Claw Compactor (default backend)

- Package: `claw-compactor` in `.venv-desktop`
- Adapter: `claw_compactor_adapter.py` → `compress_prompt_text(text, tags=...)`
- Engine: Fusion pipeline (14 stages, zero LLM inference)
- Env:
  - `COMPRESSION_BACKEND` — `claw` (default), `llmlingua`, `both`, `auto`, `headroom`
  - `CLAW_COMPACTOR_ENABLED` — `1` / `0`
  - `CLAW_COMPACTOR_MIN_SAVINGS_PCT` — default `3`
  - `CLAW_COMPACTOR_AGGRESSIVE` — default `1`
  - `CLAW_COMPACTOR_REWIND` — default `0` (reversible markers off for Task prompts)

## Headroom Local Engines (SmartCrusher + CCR)

- Files: `headroom_adapter.py`, `smart_crusher.py`, `ccr_manager.py`
- Adapter class: `HeadroomAdapter` (pure Python engines for environments where Rust native `headroom-py` cannot compile).
- Engines:
  - **SmartCrusher** (`smart_crusher.py`): Compresses structures recursively, retaining the first $N$ elements (schema), last $M$ (recency), and all error/exception occurrences, omitting normal logs/records.
  - **CCR Protocol (Compress-Cache-Retrieve)** (`ccr_manager.py` + `bin/ccr_retrieve.py`): Caches original blocks exceeding `CCR_THRESHOLD_CHARS` (default 4000) to `projects/ccr_cache/<sha256>.txt`, substituting them in prompt contexts with instruction placeholders. The original can be read by executing:
    `python3 ~/.cursor/bin/ccr_retrieve.py <sha256>`


## LLMLingua (optional second pass)

- File: `token_compactor.py`
- Main function: `compress_prompt_context(prompt: str, rate: float = 0.6) -> tuple[str, bool]`
- Runtime logs:
  - `Tokens Originaux`
  - `Tokens Compresses`
  - `Economie (%)`

## Adaptive Context Manager

- File: `src/utils/adaptive_context_manager.py`
- Main class: `AdaptiveContextManager`
- Core behavior:
  - Trigger compaction when history exceeds `8 messages` or `3000 tokens` (defaults).
  - Keep the 2 most recent messages intact.
  - Summarize older history into a Key-Value state dictionary.
  - Build final request in strict order:
    1. `[BLOCK_1_STATIC]` global system/rules/skills
    1b. `[BLOCK_1B_TOKEN_BUDGET_GUARDRAIL]` deterministic budget report (`src/utils/token_budget_guardrail.py`)
    2. `[BLOCK_2_SEMI_STATIC]` compacted global state (KV JSON)
    3. `[BLOCK_3_DYNAMIC_HISTORY]` recent message window
    4. `[BLOCK_4_ULTRA_DYNAMIC]` latest question + ephemeral vars

## Deterministic Static Prompt Registry

- File: `src/utils/static_prompt_registry.py`
- Builds a stable `[GLOBAL_SYSTEM_STATIC]` block from:
  - global rules: `~/.cursor/rules/*.mdc`
  - global skills: `~/.cursor/skills/**/SKILL.md`
- Stable sort is enforced to maximize cache hit probability across calls.

## Flash KV Summarizer

- File: `src/utils/flash_kv_summarizer.py`
- Factory: `src/utils/summarizer_factory.py`
- Modes:
  - `heuristic` (local, no API)
  - `flash` (small LLM extraction)
  - `auto` (flash then heuristic fallback)
- Providers: Ollama local, OpenAI mini, Anthropic Haiku (auto-detected via env)

## Middleware

- File: `examples/compression_middleware.py`
- Class: `PromptCompressionMiddleware`
- Use `before_llm_call(payload)` to:
  - route messages through `AdaptiveContextManager`,
  - maintain cache-friendly block ordering,
  - and apply LLMLingua compression only on non-system message content.

## Global Cursor Hook (all workspaces)

Configured in `~/.cursor/hooks.json`:

- `preToolUse` + matcher `Task`
- command: `./hooks/semantic-compress-pretool.sh`
- script: `~/.cursor/hooks/semantic-compress-pretool.py`

Behavior:

- Applies automatically to every subagent launch from Cursor, regardless of workspace.
- Rebuilds Task prompts in a deterministic block order for cache saturation.
- Compacts history when adaptive thresholds are reached (`8 messages` or `3000 tokens` by default).
- Compresses only the `[BLOCK_3_DYNAMIC_HISTORY]` section when:
  - dynamic block length >= `min_chars_to_compress` (default `1200`)
  - content type looks like `code`, `logs`, or `subagent` output
- Default compressor: **Claw Compactor** (`COMPRESSION_BACKEND=claw`)
- Rewrites Task input via `updated_input.prompt`.

Environment tuning:

- `COMPRESSION_BACKEND` (default `claw`)
- `LLMLINGUA_HOOK_RATE` (default `0.6`)
- `LLMLINGUA_HOOK_MIN_CHARS` (default `1200`)
- `ADAPTIVE_CTX_MESSAGE_THRESHOLD` (default `8`)
- `ADAPTIVE_CTX_TOKEN_THRESHOLD` (default `3000`)
- `ADAPTIVE_CTX_RECENT_WINDOW` (default `6`)

Example:

```bash
export LLMLINGUA_HOOK_RATE=0.55
export LLMLINGUA_HOOK_MIN_CHARS=900
```

### Persistent config (recommended for Cursor)

Terminal `export` is **not** inherited by Cursor hooks. Use **`~/.cursor/compression.env`** instead (loaded by `hooks/semantic-compress-pretool.sh`):

```bash
cp ~/.cursor/compression.env.example ~/.cursor/compression.env
# edit COMPRESSION_BACKEND=both
```

No Cursor restart required — the hook sources this file on every Task launch.

## Compression Rate Tuning

- `rate=0.75` -> conservative (recommended for complex code, migrations, intricate logic).
- `rate=0.60` -> balanced default (good quality/savings trade-off).
- `rate=0.45` -> aggressive (best for noisy logs, repetitive traces, verbose sub-agent outputs).
- `rate<0.45` -> risky for precision-sensitive tasks (refactor details, edge-case debugging, strict API contracts).

## Practical Strategy

1. Start with `rate=0.6`.
2. Run your existing checks/tests on the generated answer.
3. If quality drops, increase toward `0.7-0.8`.
4. If quality remains stable, decrease in small steps (`-0.05`) to gain more token savings.

## Notes

- First run may download the model from Hugging Face.
- If one model alias fails, the utility automatically falls back to a compatible LLMLingua-2 model name.
- Keep compression for large blocks only (example threshold: `min_chars_to_compress=1200`).
- Cursor limitation: `beforeSubmitPrompt` can validate/block only. It cannot rewrite the main user prompt text yet.
