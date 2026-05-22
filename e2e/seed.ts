import { randomBytes } from 'node:crypto';

const API = process.env.E2E_API_URL ?? 'http://localhost:8001';

async function call(path: string, init: RequestInit = {}) {
  const r = await fetch(`${API}${path}`, {
    ...init,
    headers: { 'content-type': 'application/json', ...(init.headers ?? {}) },
  });
  if (!r.ok && r.status !== 409) {
    throw new Error(`${init.method ?? 'GET'} ${path} → ${r.status}: ${await r.text()}`);
  }
  return r;
}

async function seed() {
  const email = 'e2e-user@example.com';
  const password = 'E2EPassword123!';

  await call('/api/auth/register', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  });

  const login = await fetch(`${API}/api/auth/login`, {
    method: 'POST',
    headers: { 'content-type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({ username: email, password }),
  });
  if (!login.ok) throw new Error(`login failed: ${login.status}`);

  console.log('Seed complete: e2e-user created.');
}

seed().catch((e) => {
  console.error(e);
  process.exit(1);
});
