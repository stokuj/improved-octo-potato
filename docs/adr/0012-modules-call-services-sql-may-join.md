# Modules call each other's services; SQL may join other modules' tables

Status: accepted, not built yet (2026-10-23)

With a separate `items` module ([ADR-0007](0007-item-identity-is-type-and-grade.md)), `market` and `inventory` need item names and grades in almost every read. We need a rule for how modules depend on each other that keeps reads cheap.

We decided that modules call each other's services and never import each other's models. Reads in `market` and `inventory` may join the `item` table in raw SQL, as today's `_SUMMARY_SQL` does, so a read stays one query. Each module keeps the same core files: `models.py`, `schemas.py`, `services.py`, `router.py`, and `admin.py` when needed. Any other file starts with a one-line comment that says why it exists.

## Considered options

- **No SQL joins across modules; each read fetches ids, then calls `items.get_many` in a second query.** Rejected: stricter, but it costs a round-trip and more code on every read.
- **SQLModel selects that import `Item` in other modules.** Rejected: that breaks the "never each other's models" rule.
