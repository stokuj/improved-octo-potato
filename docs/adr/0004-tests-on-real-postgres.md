# Tests run on a real Postgres, never DB mocks

Status: accepted (2026-10-23)

Backend tests talk to a real PostgreSQL database, `app_test`, the same major version as production. There are no DB mocks and no SQLite. DB mocks once hid a migration bug that only showed up in production. The import also relies on Postgres-only behaviour, such as telling inserts from updates with `xmax`.

The database is not cleaned between tests. Each test session starts by dropping and recreating the `public` schema, then every test shares it. So every test creates its own unique data: unique item names and item types, unique user emails.

## Consequences

- Running the tests needs a Postgres; `TEST_PG_HOSTPORT` points them at another server. CI runs Postgres 16 and also checks `alembic upgrade head` and `alembic check`.
- A test must never assume an empty table. Count only the rows it created.
- The rule is about the database. Outside services are still faked: Google sign-in and Codex icon fetches never leave the test process.
