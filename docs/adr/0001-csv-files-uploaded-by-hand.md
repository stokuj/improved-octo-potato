# Data arrives as CSV files uploaded by hand

Status: accepted (2026-10-23)

All game data comes from two addons kept in a separate repo. ArcheMarket writes auction-house scans to `listings.csv` and market days to `market.csv`. ArcheBag writes bags and warehouses to `inventory.csv` and house chests to `chests.csv`. The user drops these files on `/import` in the browser, a few at a time, whenever they like. Nothing reaches the app any other way.

We decided this in the ArcheMarket rebuild. The old intake had stopped working: the `pricetracker_folio` addon wrote JSONL, the watcher that sent it was already gone, and only the Discord bot still called the ingest endpoint. The user chose to upload by hand, through the same sign-in as the rest of the app.

The addons only append to their files, so every upload repeats rows the app has already seen. The import is therefore idempotent: uploading the same file again changes nothing, the newest scan wins, and every data line is counted once as inserted, updated, skipped or an error. Old files can be archived or emptied at any time.

## Considered options

- **Automatic upload** (a file watcher, a collector on the player's PC, an API token for scripts). Rejected by the user: they upload by hand.
- **Discord bot** (`/addprice`) and **JSONL ingest** (`POST /api/ingest/prices`). Removed with the rebuild.
- **The old `pricetracker*` addons.** Replaced by ArcheMarket and removed.

## Consequences

- How a file is routed is decided by its exact header, see [ADR-0009](0009-file-imports-are-connectors.md).
- Market files are admin only; inventory and chest files are open to any signed-in user.
- Who uploaded a market row is covered in [ADR-0011](0011-market-rows-record-their-uploader.md).
