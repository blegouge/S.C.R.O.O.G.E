#!/usr/bin/env bash
# code-review-graph: auto-update graph after file edits (Cursor hook)
# Fails gracefully — never blocks the editor.
set -euo pipefail

# Consume stdin (Cursor sends JSON context)
cat > /dev/null

# Run update; swallow errors so the hook always succeeds.
output=$(code-review-graph update --skip-flows 2>&1) || true

# Emit valid JSON on stdout per Cursor hooks protocol.
python3 -c "
import json, sys
print(json.dumps({'message': 'graph updated', 'passed': True}))
" 2>/dev/null || echo '{"passed":true}'

exit 0
