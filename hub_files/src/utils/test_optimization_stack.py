#!/usr/bin/env python3
"""
Integration tests for the Cursor optimization stack (P0–P2).

Run:
  PYTHONPATH=src:token-telemetry python3 -m unittest src.utils.test_optimization_stack -v
  ~/.cursor/bin/test-optimization-stack.sh
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

CURSOR_HOME = Path(os.environ.get("CURSOR_HOME", Path.home() / ".cursor"))
SRC_DIR = CURSOR_HOME / "src"
TELEMETRY_DIR = CURSOR_HOME / "token-telemetry"
HOOKS_DIR = CURSOR_HOME / "hooks"
REPO_ROOT = Path(__file__).resolve().parents[3]

_TEST_LOG_DIR: tempfile.TemporaryDirectory[str] | None = None
_TEST_LOG_PATH: Path | None = None

for path in (TELEMETRY_DIR, SRC_DIR, REPO_ROOT):
    path_str = str(path)
    if path_str in sys.path:
        sys.path.remove(path_str)
    sys.path.insert(0, path_str)

from telemetry_metrics import (  # noqa: E402
    hook_overhead_tokens,
    hook_saved_tokens,
    is_subagent_launch,
    rtk_hook_saved_tokens,
    summarize_layer_kpis,
)
from utils.static_prompt_registry import (  # noqa: E402
    PromptRegistryPaths,
    build_global_static_block,
)

GOOD_BRIEF = """
Skill: spec-driven-idempotency
MCP task class: LOCAL_CODE
[MCP_ALLOWLIST]: code-review-graph
[CONTEXT]
src/foo.py:10-25
def bar():
    return 1
[AC]
- Tests pass
"""


def _compression_env() -> dict[str, str]:
    global _TEST_LOG_DIR, _TEST_LOG_PATH
    if _TEST_LOG_PATH is None:
        _TEST_LOG_DIR = tempfile.TemporaryDirectory(prefix="cursor-tt-")
        _TEST_LOG_PATH = Path(_TEST_LOG_DIR.name) / "events.jsonl"
    env = os.environ.copy()
    env["CURSOR_TOKEN_TELEMETRY_LOG"] = str(_TEST_LOG_PATH)

    # Inject PYTHONPATH so subprocess hooks can find telemetry_common and utils
    root_dir = Path(__file__).resolve().parent.parent.parent.parent
    src_dir = root_dir / "hub_files" / "src"
    existing_pythonpath = env.get("PYTHONPATH", "")
    new_pythonpath = [str(root_dir), str(src_dir)]
    if existing_pythonpath:
        new_pythonpath.append(existing_pythonpath)
    env["PYTHONPATH"] = os.path.pathsep.join(new_pythonpath)

    env_path = CURSOR_HOME / "compression.env"
    if env_path.is_file():
        for raw_line in env_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            env[key.strip()] = value.strip().strip('"').strip("'")
    env["CURSOR_HOME"] = str(CURSOR_HOME)
    return env


def _run_hook(
    script: str, payload: dict, *, env: dict[str, str] | None = None
) -> tuple[dict, str, str, int]:
    merged = _compression_env()
    if env:
        merged.update(env)
    proc = subprocess.run(
        [sys.executable, str(HOOKS_DIR / script)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env=merged,
        cwd=str(CURSOR_HOME),
        timeout=60,
    )
    stdout = proc.stdout.strip()
    try:
        parsed = json.loads(stdout) if stdout else {}
    except json.JSONDecodeError:
        parsed = {"_raw_stdout": stdout, "_parse_error": True}
    return parsed, proc.stderr, stdout, proc.returncode


class CompressionEnvConfigTests(unittest.TestCase):
    def test_compression_env_has_p0_settings(self) -> None:
        text = (CURSOR_HOME / "compression.env").read_text(encoding="utf-8")
        self.assertTrue(
            "COMPRESSION_BACKEND=claw" in text or "COMPRESSION_BACKEND=headroom" in text,
            "COMPRESSION_BACKEND must be claw or headroom",
        )
        self.assertIn("ADAPTIVE_CTX_STRUCTURE_MIN_INPUT_TOKENS=2500", text)
        self.assertIn("LLMLINGUA_HOOK_MIN_CHARS=2500", text)
        self.assertNotIn("COMPRESSION_BACKEND=both", text.replace("#", ""))


class HeadroomLocalTests(unittest.TestCase):
    def test_smart_crusher_anomalies(self) -> None:
        from smart_crusher import SmartCrusher, SmartCrusherConfig

        config = SmartCrusherConfig(n=1, m=1)
        crusher = SmartCrusher(config)
        data = [
            {"id": 0, "msg": "ok"},
            {"id": 1, "msg": "ok"},
            {"id": 2, "msg": "error occurred"},
            {"id": 3, "msg": "ok"},
            {"id": 4, "msg": "ok"},
        ]
        res = json.loads(crusher.compress(json.dumps(data)))
        self.assertEqual(res[0]["id"], 0)
        self.assertEqual(res[1], {"_pruned_count": 1})
        self.assertEqual(res[2]["id"], 2)
        self.assertEqual(res[3], {"_pruned_count": 1})
        self.assertEqual(res[4]["id"], 4)

    def test_ccr_compress_flow(self) -> None:
        from ccr_manager import ccr_compress

        # Set low threshold
        os.environ["CCR_THRESHOLD_CHARS"] = "50"
        payload = "A" * 60
        text = f"```\n{payload}\n```"
        compressed, applied = ccr_compress(text)
        self.assertTrue(applied)
        self.assertIn("[CCR_BLOCK:", compressed)


class HooksJsonTests(unittest.TestCase):
    def test_hooks_json_has_write_and_task_matchers(self) -> None:
        hooks = json.loads((CURSOR_HOME / "hooks.json").read_text(encoding="utf-8"))
        pre = hooks.get("hooks", {}).get("preToolUse", [])
        matchers = {h.get("matcher") for h in pre if h.get("matcher")}
        self.assertIn("Task", matchers)
        self.assertIn("Write", matchers)
        write_cmds = [h["command"] for h in pre if h.get("matcher") == "Write"]
        self.assertTrue(any("diff-only-pretool-write" in c for c in write_cmds))

    def test_codex_hooks_json_has_token_reducers(self) -> None:
        hub_files = Path(__file__).resolve().parents[2]
        hooks = json.loads((hub_files / "codex" / "hooks.json").read_text(encoding="utf-8"))
        codex_hooks = hooks.get("hooks", {})
        pre = codex_hooks.get("PreToolUse", [])
        matcher_to_commands: dict[str, list[str]] = {}
        for group in pre:
            matcher = str(group.get("matcher") or "")
            commands = [
                str(handler.get("command") or "")
                for handler in group.get("hooks", [])
                if isinstance(handler, dict)
            ]
            matcher_to_commands[matcher] = commands

        self.assertTrue(
            any("codex-rtk-pretool-bash" in cmd for cmd in matcher_to_commands.get("^Bash$", [])),
            "Codex Bash PreToolUse must run RTK rewrite hook",
        )
        self.assertTrue(
            any("semantic-compress-pretool" in cmd for cmd in matcher_to_commands.get("^Task$", [])),
            "Codex Task PreToolUse must run subagent prompt compression",
        )
        self.assertIn("UserPromptSubmit", codex_hooks)
        self.assertIn("SubagentStart", codex_hooks)
        self.assertIn("PreCompact", codex_hooks)
        self.assertIn("PostCompact", codex_hooks)


class StaticRegistryTests(unittest.TestCase):
    def test_block_is_deterministic(self) -> None:
        paths = PromptRegistryPaths(cursor_home=CURSOR_HOME)
        a = build_global_static_block(paths)
        b = build_global_static_block(paths)
        self.assertEqual(a, b)
        self.assertIn("[GLOBAL_SYSTEM_STATIC]", a)
        self.assertNotIn("Today's date", a)

    def test_skill_registry_names_only(self) -> None:
        block = build_global_static_block(PromptRegistryPaths(cursor_home=CURSOR_HOME))
        registry = block.split("GLOBAL_SKILL_REGISTRY:\n", 1)[-1]
        # Names-only lines look like "- skill-name" without ": long description"
        for line in registry.splitlines():
            if line.startswith("- ") and ": " in line[2:]:
                # Allow scope in rules only; skills should not have ": desc"
                if "/SKILL" not in line and len(line) > 80:
                    self.fail(f"Skill line looks like full description: {line[:100]}")


class TelemetryMetricsStackTests(unittest.TestCase):
    def test_hook_overhead_explicit(self) -> None:
        row = {
            "compression_input_tokens": 100,
            "compression_after_tokens": 150,
            "compression_overhead_tokens": 50,
        }
        self.assertEqual(hook_overhead_tokens(row), 50)

    def test_hook_overhead_inferred(self) -> None:
        row = {"compression_input_tokens": 100, "compression_after_tokens": 180}
        self.assertEqual(hook_overhead_tokens(row), 80)

    def test_hook_saved_end_to_end(self) -> None:
        row = {
            "compression_saved_tokens": 0,
            "compression_input_tokens": 500,
            "compression_after_tokens": 400,
        }
        self.assertEqual(hook_saved_tokens(row), 100)

    def test_subagent_launch_event_set(self) -> None:
        self.assertTrue(is_subagent_launch({"event": "subagentLaunch"}))

    def test_rtk_shell_rewrite_counts_codex_bash(self) -> None:
        rows = [
            {
                "event": "postToolUse",
                "tool": "Bash",
                "approx_tokens": 100,
            },
            {
                "event": "rtkShellRewrite",
                "tool": "Bash",
                "rtk_before_tokens": 30,
                "rtk_after_tokens": 10,
            },
        ]
        self.assertEqual(rtk_hook_saved_tokens(rows[1]), 20)
        layers = summarize_layer_kpis(rows, rtk_gain={"ok": False})
        rtk = layers["layers"]["rtk_shell"]
        self.assertEqual(rtk["observed_tokens"], 100)
        self.assertEqual(rtk["savings_tokens"], 20)
        self.assertTrue(rtk["available"])


class SemanticCompressHookTests(unittest.TestCase):
    def test_light_mode_skips_blocks(self) -> None:
        payload = {
            "tool_name": "Task",
            "tool_input": {
                "prompt": GOOD_BRIEF.strip() + "\n\nImplement fix.",
                "subagent_type": "generalPurpose",
                "description": "unit-test-light",
            },
            "workspace_roots": [str(CURSOR_HOME)],
        }
        out, stderr, _, rc = _run_hook("semantic-compress-pretool.py", payload)
        self.assertEqual(rc, 0, stderr)
        self.assertEqual(out.get("permission"), "allow")
        prompt = out.get("updated_input", {}).get("prompt", "")
        self.assertNotIn("[BLOCK_1_STATIC]", prompt)
        self.assertIn("mode=light", stderr)

    def test_full_mode_wraps_blocks_when_forced(self) -> None:
        # input must exceed structure_min (min 500 tokens ≈ 2000 chars; env default 2500 ≈ 10k chars)
        large_body = "context line for token volume.\n" * 600
        payload = {
            "tool_name": "Task",
            "tool_input": {
                "prompt": GOOD_BRIEF.strip() + "\n\n" + large_body,
                "subagent_type": "generalPurpose",
                "description": "unit-test-full",
            },
            "workspace_roots": [str(CURSOR_HOME)],
        }
        out, stderr, _, rc = _run_hook("semantic-compress-pretool.py", payload)
        self.assertEqual(rc, 0, stderr)
        prompt = out.get("updated_input", {}).get("prompt", "")
        self.assertIn("[BLOCK_1_STATIC]", prompt)
        self.assertIn("[BLOCK_1B_TOKEN_BUDGET_GUARDRAIL]", prompt)
        self.assertIn("[BLOCK_4_ULTRA_DYNAMIC]", prompt)

    def test_invalid_brief_denied(self) -> None:
        payload = {
            "tool_name": "Task",
            "tool_input": {
                "prompt": "Do something without brief sections.",
                "subagent_type": "generalPurpose",
            },
            "workspace_roots": [str(CURSOR_HOME)],
        }
        out, _, _, rc = _run_hook("semantic-compress-pretool.py", payload)
        self.assertEqual(rc, 0)
        self.assertEqual(out.get("permission"), "deny")


class WritePretoolHookTests(unittest.TestCase):
    def test_blocks_write_on_existing_file(self) -> None:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as tmp:
            tmp.write("existing content\n")
            tmp_path = tmp.name

        try:
            payload = {
                "tool_name": "Write",
                "tool_input": {"path": tmp_path, "contents": "overwrite"},
                "workspace_roots": [str(Path(tmp_path).parent)],
            }
            out, _, _, rc = _run_hook("diff-only-pretool-write.py", payload)
            self.assertEqual(rc, 0)
            self.assertEqual(out.get("permission"), "deny")
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    def test_allows_write_on_missing_file(self) -> None:
        missing = CURSOR_HOME / "token-telemetry" / ".test-write-new-file.tmp"
        missing.unlink(missing_ok=True)
        payload = {
            "tool_name": "Write",
            "tool_input": {"path": str(missing), "contents": "new"},
            "workspace_roots": [str(CURSOR_HOME)],
        }
        out, _, _, rc = _run_hook("diff-only-pretool-write.py", payload)
        self.assertEqual(rc, 0)
        self.assertEqual(out.get("permission"), "allow")
        missing.unlink(missing_ok=True)

    def test_allows_non_write_tools(self) -> None:
        payload = {"tool_name": "Read", "tool_input": {"path": "AGENT.md"}}
        out, _, _, rc = _run_hook("diff-only-pretool-write.py", payload)
        self.assertEqual(rc, 0)
        self.assertEqual(out.get("permission"), "allow")


class DiffOnlyApplyHookTests(unittest.TestCase):
    def test_apply_search_replace_block(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir) / "sample.py"
            target.write_text("def foo():\n    return 1\n", encoding="utf-8")
            text = """path: sample.py
<<<<<<< SEARCH
def foo():
    return 1
=======
def foo():
    return 2
>>>>>>> REPLACE
"""
            payload = {
                "hook_event_name": "afterAgentResponse",
                "text": text,
                "workspace_roots": [tmpdir],
            }
            proc = subprocess.run(
                [sys.executable, str(HOOKS_DIR / "diff-only-apply.py")],
                input=json.dumps(payload),
                capture_output=True,
                text=True,
                env=_compression_env(),
                timeout=30,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertIn("return 2", target.read_text(encoding="utf-8"))


class TelemetryFileLockingTests(unittest.TestCase):
    def test_concurrent_append_event(self) -> None:
        import concurrent.futures

        import telemetry_common

        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as tmp:
            tmp_path = Path(tmp.name)

        orig_log = os.environ.get("CURSOR_TOKEN_TELEMETRY_LOG")
        os.environ["CURSOR_TOKEN_TELEMETRY_LOG"] = str(tmp_path)

        try:

            def writer(idx: int) -> None:
                for j in range(10):
                    telemetry_common.append_event({"writer": idx, "index": j})

            with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
                futures = [executor.submit(writer, i) for i in range(8)]
                concurrent.futures.wait(futures)

            lines = tmp_path.read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(lines), 80)
            for line in lines:
                data = json.loads(line)
                self.assertIn("writer", data)
                self.assertIn("index", data)
        finally:
            if orig_log is not None:
                os.environ["CURSOR_TOKEN_TELEMETRY_LOG"] = orig_log
            else:
                os.environ.pop("CURSOR_TOKEN_TELEMETRY_LOG", None)
            tmp_path.unlink(missing_ok=True)


class DashboardCacheTests(unittest.TestCase):
    def test_rtk_gain_cache(self) -> None:
        import serve_dashboard

        orig_candidates = serve_dashboard._rtk_cmd_candidates
        serve_dashboard._rtk_cmd_candidates = lambda: [["echo", '{"summary": {"total_saved": 42}}']]
        serve_dashboard._RTK_GAIN_CACHE.clear()

        try:
            res1 = serve_dashboard.load_rtk_gain(project=False, source="cursor")
            self.assertTrue(res1.get("ok"))
            self.assertEqual(res1.get("summary", {}).get("total_saved"), 42)

            serve_dashboard._rtk_cmd_candidates = lambda: [
                ["echo", '{"summary": {"total_saved": 100}}']
            ]

            res2 = serve_dashboard.load_rtk_gain(project=False, source="cursor")
            self.assertEqual(res2.get("summary", {}).get("total_saved"), 42)

            serve_dashboard._RTK_CACHE_TTL = -1.0
            res3 = serve_dashboard.load_rtk_gain(project=False, source="cursor")
            self.assertEqual(res3.get("summary", {}).get("total_saved"), 100)
        finally:
            serve_dashboard._rtk_cmd_candidates = orig_candidates
            serve_dashboard._RTK_CACHE_TTL = 30.0
            serve_dashboard._RTK_GAIN_CACHE.clear()

    def test_layer_kpis_endpoint(self) -> None:
        import io
        from unittest.mock import MagicMock, patch

        import serve_dashboard

        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as tmp:
            tmp_path = Path(tmp.name)
            tmp_path.write_text(
                json.dumps({"event": "postToolUse", "tool": "Shell", "approx_tokens": 100}) + "\n",
                encoding="utf-8",
            )

        handler = MagicMock()
        handler.path = "/api/layer-kpis?source=cursor"
        handler.headers = {}
        handler.wfile = io.BytesIO()

        mock_events = [{"event": "postToolUse", "tool": "Shell", "approx_tokens": 100}]
        with (
            patch("serve_dashboard.get_paths", return_value=(tmp_path, tmp_path)),
            patch(
                "serve_dashboard.load_rtk_gain",
                return_value={"ok": True, "summary": {"total_saved": 42}},
            ),
            patch("telemetry_db.fetch_events_from_db", return_value=mock_events),
        ):
            serve_dashboard.DashboardHandler.do_GET(handler)

        handler.send_response.assert_called_with(200)
        response_bytes = handler.wfile.getvalue()
        response_data = json.loads(response_bytes.decode("utf-8"))
        self.assertTrue(response_data.get("ok"))
        self.assertIn("layers", response_data)
        self.assertEqual(response_data["layers"]["rtk_shell"]["observed_tokens"], 100)

        tmp_path.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
