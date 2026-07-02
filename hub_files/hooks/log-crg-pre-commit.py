#!/usr/bin/env python3
import json
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

# Add code-review-graph pipx site-packages to sys.path so we can use its utility functions
sys.path.append("/Users/blegouge/.local/pipx/venvs/code-review-graph/lib/python3.14/site-packages")

try:
    from code_review_graph.context_savings import estimate_file_tokens, format_context_savings_panel
    from code_review_graph.incremental import get_changed_files, get_staged_and_unstaged
except ImportError:
    # Fallback placeholders in case python paths change
    estimate_file_tokens = None
    format_context_savings_panel = None
    get_changed_files = None
    get_staged_and_unstaged = None


def utc_ts() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def run_cmd(args, cwd=None):
    try:
        res = subprocess.run(args, capture_output=True, text=True, check=True, cwd=cwd)
        return res.stdout.strip()
    except Exception:
        return ""


def main():
    repo_root = Path(os.getcwd()).resolve()

    # 1. Run detect-changes without --brief to get JSON
    try:
        res = subprocess.run(
            ["code-review-graph", "detect-changes"],
            capture_output=True,
            text=True,
            check=True,
            cwd=str(repo_root),
        )
        stdout = res.stdout.strip()
        if not stdout:
            sys.exit(0)

        if stdout == "No changes detected.":
            print(stdout)
            sys.exit(0)

        data = json.loads(stdout)
    except Exception as e:
        # Fallback: run the original brief command directly and exit to prevent blocking git
        sys.stderr.write(f"Warning: code-review-graph logging hook failed: {e}\n")
        subprocess.run(["code-review-graph", "detect-changes", "--brief"], cwd=str(repo_root))
        sys.exit(0)

    # 2. Print summary & panel to console (stdout)
    summary = data.get("summary", "No summary available.")
    print(summary)

    original_tokens = 0
    returned_tokens = 0
    saved_tokens = 0
    saved_percent = 0

    try:
        if estimate_file_tokens and get_changed_files:
            changed = get_changed_files(repo_root, "HEAD~1")
            if not changed:
                changed = get_staged_and_unstaged(repo_root)
            original_tokens = estimate_file_tokens(repo_root, changed)

            savings = data.get("context_savings") or {}
            saved_tokens = int(savings.get("saved_tokens", 0))
            saved_percent = int(savings.get("saved_percent", 0))
            returned_tokens = max(0, original_tokens - saved_tokens)

            panel = format_context_savings_panel(
                savings, original_tokens=original_tokens, response=data
            )
            if panel:
                print(panel)
        else:
            # Fallback format if imports are missing
            savings = data.get("context_savings") or {}
            saved_tokens = int(savings.get("saved_tokens", 0))
            saved_percent = int(savings.get("saved_percent", 0))
            print(f"Estimated context saved: ~{saved_tokens:,} tokens (~{saved_percent}%)")
    except Exception as e:
        sys.stderr.write(f"Warning: could not format token savings panel: {e}\n")

    # 3. Log to telemetry
    try:
        repo_name = repo_root.name
        branch_name = run_cmd(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=str(repo_root))

        files_changed = 0
        import re

        m_files = re.search(r"Analyzed (\d+) changed file", summary)
        if m_files:
            files_changed = int(m_files.group(1))

        functions_changed = len(data.get("changed_functions", []))
        affected_flows = len(data.get("affected_flows", []))
        test_gaps = len(data.get("test_gaps", []))
        risk_score = float(data.get("risk_score", 0.0))

        row = {
            "ts": utc_ts(),
            "event": "codeReviewGraph",
            "approx_tokens": returned_tokens,
            "text_chars": len(summary),
            "raw_chars": len(stdout),
            "repo": repo_name,
            "branch": branch_name,
            "files_changed": files_changed,
            "functions_changed": functions_changed,
            "affected_flows": affected_flows,
            "test_gaps": test_gaps,
            "risk_score": risk_score,
            "saved_tokens": saved_tokens,
            "original_tokens": original_tokens,
            "returned_tokens": returned_tokens,
            "saved_percent": saved_percent,
        }

        # Write to events.jsonl for both Cursor and Antigravity
        log_files = [
            Path.home() / ".cursor" / "token-telemetry" / "events.jsonl",
            Path.home() / ".gemini" / "antigravity" / "token-telemetry" / "events.jsonl",
        ]
        for log_file in log_files:
            try:
                log_file.parent.mkdir(parents=True, exist_ok=True)
                with log_file.open("a", encoding="utf-8") as fh:
                    fh.write(json.dumps(row, ensure_ascii=False) + "\n")
            except Exception as le:
                sys.stderr.write(f"Warning: could not write to {log_file}: {le}\n")
    except Exception as e:
        sys.stderr.write(f"Warning: could not log pre-commit telemetry: {e}\n")


if __name__ == "__main__":
    main()
