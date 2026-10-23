#!/usr/bin/env bash
set -euo pipefail
required=(
  "Strict-Transport-Security"
  "X-Frame-Options"
  "X-Content-Type-Options"
  "Referrer-Policy"
)
fail=0
for h in "${required[@]}"; do
  if ! grep -qiE "^\s*${h}" infra/caddy/Caddyfile; then
    echo "FAIL: missing header ${h}"
    fail=1
  fi
done
# CSP is verified separately — must come from SvelteKit, not Caddy.
if ! grep -q "csp" frontend/svelte.config.js; then
  echo "FAIL: frontend/svelte.config.js missing kit.csp config"
  fail=1
fi
# The auth cookie is host-only on the apex domain, so www must redirect there.
if ! grep -qF 'redir https://{$APP_DOMAIN}{uri}' infra/caddy/Caddyfile; then
  echo "FAIL: Caddyfile must redirect APP_WWW_DOMAIN to APP_DOMAIN"
  fail=1
fi
exit $fail
