# Adaptive Context Routing

This workspace now uses a hybrid token optimization pipeline:

1. Prompt caching friendly request assembly (deterministic static top block)
2. Adaptive state compaction for long histories
3. Optional LLMLingua compression on large dynamic sections

> **Paths in this document** use the *installed hub* layout (e.g. `~/.cursor/src/utils/…`,
> `~/.cursor/hooks/…`). In this repository the same files live under `hub_files/` — for
> instance `hub_files/src/utils/adaptive_context_manager.py` and
> `hub_files/hooks/semantic-compress-pretool.py`.

## Core modules

- `src/utils/adaptive_context_manager.py`
  - threshold check (`8 messages` or `3000 tokens` by default)
  - state compaction (`all except 2 most recent`)
  - final 4-block message assembly
- `src/utils/static_prompt_registry.py`
  - deterministic static block builder from global `rules/*.mdc` + `skills/**/SKILL.md`
- `hooks/semantic-compress-pretool.py`
  - global Cursor automation for `Task` tool (subagents, all workspaces)
- `examples/compression_middleware.py`
  - reference app-level integration for OpenAI/Anthropic payload builders

## Final request block order

Always assembled in this order:

1. `[BLOCK_1_STATIC]` global system + Caveman + rules + skills
1b. `[BLOCK_1B_TOKEN_BUDGET_GUARDRAIL]` deterministic budget report (`src/utils/token_budget_guardrail.py`)
2. `[BLOCK_2_SEMI_STATIC]` summarized global key-value state
3. `[BLOCK_3_DYNAMIC_HISTORY]` recent message window
4. `[BLOCK_4_ULTRA_DYNAMIC]` latest user input + ephemeral fields

## Transparent integration (app-side)

```python
from compression_middleware import PromptCompressionMiddleware

middleware = PromptCompressionMiddleware(
    default_rate=0.6,
    min_chars_to_compress=1200,
)

payload = {
    "model": "gpt-4.1-mini",
    "messages": messages,
    "global_state": {"Active_Branch": "main"},
}

optimized_payload = middleware.before_llm_call(payload)
client.responses.create(**optimized_payload)
```

## Cursor automation (global)

`hooks.json` runs:

- `preToolUse` with matcher `Task`
- command `./hooks/semantic-compress-pretool.sh`

This means all subagent launches from Cursor are auto-routed through the same hybrid optimizer in any workspace using `~/.cursor/hooks.json`.

## Flash summarizer (branchable)

- Module: `src/utils/flash_kv_summarizer.py`
- Factory: `src/utils/summarizer_factory.py`
- Modes (`ADAPTIVE_CTX_SUMMARIZER`):
  - `auto` (default): try flash model, fallback to heuristic KV extractor
  - `flash`: flash only, fallback to heuristic if empty/failure
  - `heuristic`: local only (no network)

Providers (auto-detect order):

1. `ollama` if `OLLAMA_HOST` is set or local Ollama responds
2. `openai` if `OPENAI_API_KEY` is set
3. `anthropic` if `ANTHROPIC_API_KEY` is set

### Recommended local setup (Ollama)

```bash
ollama pull llama3.2:1b
export ADAPTIVE_CTX_SUMMARIZER=auto
export OLLAMA_MODEL=llama3.2:1b
```

### Per-call override (Task tool input)

```json
{
  "summarizer_mode": "flash"
}
```

## Git pre-flight cache (BLOCK_2, LLM-free)

On each `Task` hook run, before `flash_kv_summarizer` / heuristic compaction:

1. **Signature** — SHA-256 (16 hex) of `branch + HEAD SHA + git status --porcelain` (cache files under `.cursor/projects/` are stripped from porcelain so the signature stays stable).
2. **Storage** — `~/.cursor/projects/cache_<signature>.json` with `global_state_kv`, `block_2_content`, `history_fingerprint`, `summarizer_mode`.
3. **Hit** — same Git signature **and** same history/config fingerprint → load KV from disk, skip summarizer.
4. **Miss** — compact via summarizer, then write/overwrite the cache file.

Disable with `ADAPTIVE_CTX_GIT_CACHE=0`.

## Environment tuning

- `ADAPTIVE_CTX_GIT_CACHE` (default `1`) — `0` disables Git pre-flight cache
- `ADAPTIVE_CTX_MESSAGE_THRESHOLD` (default `8`)
- `ADAPTIVE_CTX_TOKEN_THRESHOLD` (default `3000`)
- `ADAPTIVE_CTX_RECENT_WINDOW` (default `6`)
- `ADAPTIVE_CTX_SUMMARIZER` (default `auto`)
- `FLASH_SUMMARIZER_PROVIDER` (`ollama` | `openai` | `anthropic`)
- `OLLAMA_HOST` (default `http://127.0.0.1:11434`)
- `OLLAMA_MODEL` (default `llama3.2:1b`)
- `FLASH_OPENAI_MODEL` (default `gpt-4o-mini`)
- `FLASH_ANTHROPIC_MODEL` (default `claude-3-5-haiku-20241022`)
- `FLASH_SUMMARIZER_TIMEOUT_SEC` (default `8`)
- `FLASH_SUMMARIZER_MIN_CHARS` (default `400`)
- `LLMLINGUA_HOOK_RATE` (default `0.6`)
- `LLMLINGUA_HOOK_MIN_CHARS` (default `1200`)
