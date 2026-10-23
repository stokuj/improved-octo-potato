# Market rows record their uploader; per-user rows come later

Status: accepted, not built yet (2026-10-23)

Market import is Admin-only for now. Later, with player registration, players may upload market data too. The threat then is a user who deliberately forges a CSV. To deal with it later we need to know, for every stored row, who uploaded it.

We decided that `market_day` and `listing` get the uploader's `user_id`, hidden from users. `listing`'s key includes `user_id`, because `scan_id` is the addon's epoch seconds and two uploaders can share one. All listing history is kept. `market_day` stays one row per item and day, and the newest scan wins.

## Consequences

Later, with registration, `market_day` becomes one row per uploader (`PK (item_id, day, user_id)`). Reads take the newest row from users who are not blocked. Blocking a forger then hides their rows with no data loss, and closed days whose values disagree between uploaders can be flagged. Every market read goes through one SQL fragment, so that change touches one place.

## Considered options

- **A `market_scan` table** (one row per uploader and scan). Rejected: an extra join on every read for nothing that two columns do not already give.
- **Per-user rows now.** Rejected: every read would need `DISTINCT ON` for a feature nobody uses yet. Waiting costs one PK migration and one fragment.
