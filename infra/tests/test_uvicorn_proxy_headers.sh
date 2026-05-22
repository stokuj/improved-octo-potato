#!/usr/bin/env bash
set -euo pipefail
for f in infra/compose/docker-compose.prod.yml infra/compose/docker-compose.dev.yml; do
  if ! grep -q -- "--proxy-headers" "$f"; then
    echo "FAIL: $f missing --proxy-headers"
    exit 1
  fi
done
echo OK
