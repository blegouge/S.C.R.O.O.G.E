#!/usr/bin/env bash
# code-review-graph: detect changes before git commit (Cursor hook)
# Fails gracefully — never blocks the editor.
set -euo pipefail

# Consume stdin
cat > /dev/null

# Run detect-changes and log telemetry; swallow errors
output=$(python3 /Users/blegouge/.gemini/antigravity/hooks/log-crg-pre-commit.py 2>&1) || output=""

# Emit valid JSON on stdout
python3 -c "
import json, sys
msg = sys.stdin.read()
print(json.dumps({'message': msg, 'passed': True}))
" <<< "$output" 2>/dev/null || echo '{"passed":true}'

exit 0
