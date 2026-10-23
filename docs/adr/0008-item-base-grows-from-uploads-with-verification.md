# The item base grows from uploads, with verification

Status: accepted, not built yet (2026-10-23)

Recipes and "all my items" need a base of items with a name, category and NPC price. Nobody wants to type it in. It starts with about 200-400 key items from the Admin's auction-house refreshes and grows from what players upload. Recipes come later and FK `item.id`.

We decided that any upload creates the items it names. An Admin file creates verified items. A player file creates unverified items, records `created_by`, and logs it. An Admin file that contains an unverified item verifies it. In `/admin` the Admin can verify or edit an item. There is no reject flow for now. The fields are `item_type`, `grade`, `name`, `category`, `npc_price`, `verified`, `created_by`, `first_seen_at` and `changed_at`.

Manual correction is not the normal path. Values fix themselves by newest-wins, and the log shows every change:
- The newest value wins, by the file's own `captured_at` compared with the item's `changed_at`. An old file uploaded late never reverts a newer value.
- A row dated more than a day in the future is a row error, so a forged timestamp cannot freeze a field.
- An Admin file may overwrite any item. A player file may overwrite only unverified items.
- A player value that differs on a verified item is kept out and logged as a mismatch. This includes filling a field that is empty.
- An empty field in a file never erases a value.
- `npc_price` may change after a game patch, so it follows the same rules.
- Every change is logged (see [ADR-0010](0010-two-logging-layers.md)).

Concurrent uploads: missing items are inserted in key order with `ON CONFLICT DO NOTHING`. Then every key in the file is locked with `SELECT … FOR UPDATE` in key order, and the rules are decided in Python. The log is exact and there are no deadlocks. Uploads that share items wait for each other, which costs milliseconds at this traffic.

## Considered options

- **One `INSERT … ON CONFLICT DO UPDATE WHERE …` that encodes the rules in SQL.** Rejected: the rule holds, but the log is computed from a read taken before the write, so it can drift when two uploads run at once.
- **Upload order as "newest".** Rejected: uploading an old file late would revert newer values.
- **A `tradeable` flag.** Rejected: having market data already says that.
- **A `source` column.** Rejected: the import log says where each value came from.
