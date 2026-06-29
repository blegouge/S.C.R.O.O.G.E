#!/usr/bin/env bash
# code-review-graph: show graph status on session start (Cursor hook)
# Fails gracefully — never blocks the editor.
set -euo pipefail

# Consume stdin
cat > /dev/null

# Capture status output
output=$(code-review-graph status 2>&1) || output="graph not built yet"

# Emit valid JSON on stdout
python3 -c "
import json, sys
msg = sys.stdin.read()
print(json.dumps({'message': msg, 'passed': True}))
" <<< "$output" 2>/dev/null || echo '{"passed":true}'

exit 0
