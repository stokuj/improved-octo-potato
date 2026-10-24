# Two logging layers: technical JSON lines and a business import log

Status: accepted; the technical layer is built (#24), the business import log is not yet (2026-10-24)

Today logging is ad hoc: a bare `logging.getLogger` in a few places and `print` in the CLI. Nothing records who uploaded what, or why an item changed. With items created by players ([ADR-0008](0008-item-base-grows-from-uploads-with-verification.md)) we need both an operations log and a history the Admin can browse.

**Technical layer.** stdlib `logging` is configured once in `core/logging.py`. It writes JSON lines to stdout with time, level, module, event, request_id and the event's fields. Code everywhere logs with `get_logger(__name__).info("event", **fields)`, never `print`. A request-id middleware sets the id for each request and echoes it in `X-Request-ID`.

**Business layer.** Every uploaded file gets one `import_run` row, including failed and refused files: user, request_id, connector, filename, status and counts. Its `import_issue` rows have the kinds `row_error`, `file_error`, `item_new`, `item_changed`, `item_verified` and `item_mismatch`. Admin edits in `/admin` are recorded as an `import_run` with connector `admin_edit`, so an item's whole history is in one place. The request_id links the two layers.

Both layers are kept forever, and the business log is read-only in `/admin`. At most 1 000 row errors are stored per run; the counts on the run stay exact. Log fields never carry character names or emails.

## Considered options

- **structlog or python-json-logger.** Rejected: about 25 lines of stdlib do the same without a dependency.
- **Admin edits as a technical log line only.** Rejected: they would be missing from the item's history in `/admin`.
- **A separate `item_change` table.** Rejected: a third table for what `import_run` plus `import_issue` already hold.
