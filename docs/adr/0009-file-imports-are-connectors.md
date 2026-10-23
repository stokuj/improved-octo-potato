# File imports are connectors; the core does not know file formats

Status: accepted, not built yet (2026-10-23)

Today the CSV parsing lives inside `market/` and `inventory/`, so those modules know headers and column positions. More file kinds are coming (recipes), and the addons change their headers over time.

We decided that each file kind is a connector in `imports/`: market, listings, inventory, chests, and later recipes. Every connector shares the same steps: detection by exact header (old and new headers side by side), per-row errors, the sum rule `inserted + updated + skipped + error_count == rows`, item resolution through `items` ([ADR-0008](0008-item-base-grows-from-uploads-with-verification.md)), and the import log ([ADR-0010](0010-two-logging-layers.md)). `market` and `inventory` never see a CSV header or column. They take parsed rows that already carry `item_id`.

Only file imports are connectors. Codex is not one: it stays a plain on-demand icon client in `inventory/` ([ADR-0005](0005-icons-from-codex-never-committed.md)).

## Consequences

- `listings.csv` with the old header has no item type or grade. Its rows match an item only when the name is unique in the item base; otherwise the row is an error. They never create items.
- A per-user advisory lock serialises one user's inventory imports. Without it, two parallel uploads by one user can both pass the "known snapshot" check and one fails on the unique key.
- Adding a file kind means adding a connector. `market`, `inventory` and `items` do not change.
