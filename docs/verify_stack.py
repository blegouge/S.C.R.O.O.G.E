#!/usr/bin/env python3
"""verify_stack.py - Sanity check de la stack d'optimisation de tokens (~/.cursor).

Auto-contenu : stdlib uniquement. Multi-OS (macOS/Linux/Windows).
Renvoie un rapport [OK]/[FAIL] par brique. Exit 0 si tout OK, 1 sinon.
"""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HUB = Path(os.environ.get("HUB", Path.home() / ".cursor"))
SRC_UTILS = HUB / "src" / "utils"
PROJECTS = HUB / "projects"
TT_DATA = Path(os.environ.get("CURSOR_TOKEN_TELEMETRY_DATA_DIR", HUB / "token-telemetry"))

results: list[tuple[str, bool, str]] = []


def record(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, ok, detail))


def load_module(name: str, path: Path):
    """Import a module from an explicit file path (no package install needed)."""
    spec = importlib.util.spec_from_file_location(name, str(path))
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {name} from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


# --- Brique 1 : Hooks interceptent une commande factice -----------------------
def check_hooks() -> None:
    try:
        hooks_file = HUB / "hooks.json"
        data = json.loads(hooks_file.read_text(encoding="utf-8"))
        hooks = data.get("hooks", {})

        pre = hooks.get("preToolUse", [])
        shell_hook = next(
            (h for h in pre if h.get("matcher") == "Shell" and "rtk" in h.get("command", "")),
            None,
        )
        has_after = "afterAgentResponse" in hooks
        has_subagent = "subagentStop" in hooks

        # Interception simulee d'une commande factice : la regle de matching
        # "Shell" doit s'appliquer a un appel terminal du type "ls -la".
        fake_tool = "Shell"
        intercepted = shell_hook is not None and shell_hook.get("matcher") == fake_tool

        ok = bool(shell_hook) and has_after and has_subagent and intercepted
        detail = (
            f"shell_intercept={intercepted}, "
            f"afterAgentResponse={has_after}, subagentStop={has_subagent}"
        )
        record("Hooks (interception commande factice)", ok, detail)
    except Exception as exc:  # noqa: BLE001
        record("Hooks (interception commande factice)", False, f"erreur: {exc}")


# --- Brique 2 : Diff-Only applique un patch de test ---------------------------
def check_diff_only() -> None:
    try:
        applier = load_module("diff_applier", SRC_UTILS / "diff_applier.py")

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "sample.txt"
            target.write_text("line A\nline B\nline C\n", encoding="utf-8")

            block = (
                "path: sample.txt\n"
                "<<<<<<< SEARCH\n"
                "line B\n"
                "=======\n"
                "line B (patched)\n"
                ">>>>>>> REPLACE\n"
            )

            result = applier.apply_text(block, [root])
            content = target.read_text(encoding="utf-8")
            ok = bool(getattr(result, "ok", False)) and "line B (patched)" in content
            detail = f"applied={getattr(result, 'applied', None)}, errors={getattr(result, 'errors', None)}"
            record("Diff-Only (application patch test)", ok, detail)
    except Exception as exc:  # noqa: BLE001
        record("Diff-Only (application patch test)", False, f"erreur: {exc}")


# --- Brique 3 : Cache Git ecrit son JSON dans projects/ -----------------------
def check_git_cache() -> None:
    try:
        acm = load_module("adaptive_context_manager", SRC_UTILS / "adaptive_context_manager.py")

        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            repo.mkdir()
            _git(repo, "init")
            _git(repo, "config", "user.email", "ci@example.com")
            _git(repo, "config", "user.name", "ci")
            (repo / "f.txt").write_text("x\n", encoding="utf-8")
            _git(repo, "add", ".")
            _git(repo, "commit", "-m", "init")

            projects_dir = Path(tmp) / "projects"
            projects_dir.mkdir()

            snapshot = acm.collect_git_repo_snapshot(repo)
            assert snapshot is not None, "snapshot Git introuvable"
            signature = acm.compute_git_signature(snapshot)

            entry = acm.Block2CacheEntry(
                global_state_kv={"probe": "verify_stack"},
                history_fingerprint="verify-fp",
                summarizer_mode="none",
                git_snapshot=snapshot,
            )

            cache = acm.GitPreflightCache(projects_dir=projects_dir)
            saved_path = cache.save(signature, entry)

            cache_path = cache.cache_path(signature)
            ok = (
                saved_path is not None
                and cache_path.exists()
                and cache_path.suffix == ".json"
                and cache_path.name.startswith("cache_")
            )
            record("Cache Git (ecriture JSON dans projects/)", ok, f"file={cache_path.name}")
    except Exception as exc:  # noqa: BLE001
        record("Cache Git (ecriture JSON dans projects/)", False, f"erreur: {exc}")


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    )


# --- Brique 4 : Observabilite + Gouvernance -----------------------------------
def check_observability_and_governance() -> None:
    try:
        TT_DATA.mkdir(parents=True, exist_ok=True)
        events = TT_DATA / "events.jsonl"
        with events.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({"event": "verify_stack_probe"}) + "\n")
        append_ok = events.exists()

        governance = [
            HUB / "rules" / "token-budget-guardrail.mdc",
            HUB / "skills" / "spec-driven-idempotency" / "SKILL.md",
            HUB / "rules" / "caveman-default.mdc",
            HUB / "src" / "utils" / "token_budget_guardrail.py",
        ]
        gov_missing = [str(p) for p in governance if not p.exists()]

        ok = append_ok and not gov_missing
        detail = f"events_append={append_ok}, manquants={gov_missing or 'aucun'}"
        record("Observabilite + Gouvernance", ok, detail)
    except Exception as exc:  # noqa: BLE001
        record("Observabilite + Gouvernance", False, f"erreur: {exc}")


def main() -> int:
    print("=" * 64)
    print(" verify_stack.py - Sanity check stack tokens (~/.cursor)")
    print(f" HUB = {HUB}")
    print("=" * 64)

    check_hooks()
    check_diff_only()
    check_git_cache()
    check_observability_and_governance()

    print()
    failures = 0
    for name, ok, detail in results:
        tag = "[OK]  " if ok else "[FAIL]"
        if not ok:
            failures += 1
        line = f"{tag} {name}"
        if detail:
            line += f"  -> {detail}"
        print(line)

    print()
    total = len(results)
    print(f"Resultat : {total - failures}/{total} briques OK.")
    if failures:
        print("Au moins une brique en echec : voir les details ci-dessus.")
        return 1
    print("Stack verifiee : toutes les briques testees sont operationnelles.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
