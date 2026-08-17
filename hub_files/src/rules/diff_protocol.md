# Diff-Only Protocol (zero intact code)

**Goal:** Minimize **output tokens**. Never echo unchanged source.

## Hard rules

1. **Forbidden in assistant output**
   - Full files, whole functions/classes, or large unchanged regions.
   - “Here is the updated file” dumps.
   - Re-printing context the reader already has.

2. **Required format** — every code change is one or more blocks:

```text
path: relative/path/from/repo/root.ext
<<<<<<< SEARCH
<exact existing lines to replace; byte-for-byte match>
=======
<replacement lines only>
>>>>>>> REPLACE
```

3. **SEARCH must match the repo (unique)**
   - Copy from the real file (same spaces, quotes, line endings).
   - Include **enough context lines** (typically **3–8**) so the snippet matches **exactly once** in the file.
   - If `diff_applier` reports *ambiguous* → widen or sharpen SEARCH; never guess.
   - One logical edit per block; use multiple blocks for multiple hunks.

4. **Special cases**
   - **New file:** omit `<<<<<<< SEARCH` / `=======`; use `path:` then only new content, or `SEARCH` empty with full content in `REPLACE`.
   - **Delete:** `REPLACE` empty.
   - **Rename:** one block on old path + note new path; or delete + add blocks.

5. **When not editing code**
   - No SEARCH/REPLACE blocks. Prose only (still terse per Caveman unless overridden).

6. **Tools vs chat (global hook)**
   - **Edit with a targeted tool first** (`StrReplace`, `ApplyPatch`, `Edit`): a hunk costs the same tokens, but the write is immediate and reviewable. The preToolUse guard never denies these; a full-file `Write` on an existing file is only nudged, and hard deny requires the marker file `<HUB>/diff-only-strict`.
   - `<HUB>/hooks/diff-only-apply.py` runs on **`afterAgentResponse`**, **`subagentStop`** and **`stop`**, parses blocks from the reply and writes files **without** a second LLM call. Use it when a tool is unavailable or denied.
   - **Duplicates are safe:** a hunk whose `REPLACE` is already on disk is counted as `blocks_already_applied` and skipped, and each response is fingerprinted so `stop` never replays what `afterAgentResponse` applied.
   - **Subagent → parent:** return **only** `path:` + SEARCH/REPLACE blocks (+ 1-line summary). No file dumps.
   - Disable hook: env `CURSOR_DIFF_ONLY_DISABLE=1` (aliases: `ANTIGRAVITY_`, `CODEX_`).

## Anti-patterns (reject)

- Wrapping blocks in markdown code fences that alter whitespace.
- `// ... unchanged ...` placeholders inside SEARCH.
- SEARCH wider than the hunk being changed.
- Guessing file content not read in this session.

## Minimal example

```text
path: src/auth.ts
<<<<<<< SEARCH
  if (!token) {
    return null;
  }
=======
  if (!token?.trim()) {
    return null;
  }
>>>>>>> REPLACE
```

## Checklist before send

- [ ] Zero unchanged lines in output?
- [ ] Each block has `path:`?
- [ ] SEARCH is exact and uniquely matchable?
- [ ] Summary ≤ 2 sentences unless user asked for detail?
