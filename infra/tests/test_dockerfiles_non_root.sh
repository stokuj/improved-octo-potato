#!/usr/bin/env bash
set -euo pipefail
fail=0
for f in backend/Dockerfile frontend/Dockerfile discord_bot/Dockerfile; do
  if ! grep -qE '^USER\s+\S' "$f"; then
    echo "FAIL: $f has no USER directive"
    fail=1
  fi
done
exit $fail
