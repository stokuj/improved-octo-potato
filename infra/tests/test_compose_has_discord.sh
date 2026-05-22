#!/usr/bin/env bash
# infra/tests/test_compose_has_discord.sh
set -euo pipefail
for f in infra/compose/docker-compose.dev.yml infra/compose/docker-compose.prod.yml; do
  if ! grep -qE '^\s*discord_bot:' "$f"; then
    echo "FAIL: $f missing discord_bot service"
    exit 1
  fi
done
echo OK
