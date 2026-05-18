# pricetracker — manual test plan

The addon runs in-game so there are no unit tests. Follow these steps in order. Stop at the first failure and report it before changing anything else.

## Setup

1. Copy the entire `addon/pricetracker/` directory into `C:\ArcheRage\Documents\Addon\pricetracker\`.
2. Verify the destination has these files at the top level: `toc.g`, `apitypes.lua`, `pricetracker.lua`.
3. Launch ArcheRage and log in to a character.

## Test 1 — Smoke: addon loads

- Open `ArcheRage.log` (usually in `Documents/ArcheRage/`) after entering the world.
- Search for "pricetracker" or for any line starting with "Error" near the end of the file.
- **Pass:** no error lines mentioning pricetracker; a "Save now" button is visible in the top-right of the screen.
- **Fail:** Lua parse error → fix and reload, or any other error → capture the log line.

## Test 2 — Opportunistic capture

- Open the Auction House.
- Search for the keyword "Egg" (or any popular item).
- Wait for the results to appear.
- Open the file `C:\ArcheRage\Documents\Addon\pricetracker\prices.jsonl`.
- **Pass:** a new line exists with `"name":"<egg name>"`, plausible `"price"`, current `"ts"`, and `"source":"ah"`.
- **Fail:** no file, no new line, or fields are wrong.

## Test 3 — Manual sweep

- Click the "Save now" button.
- Wait ~3 seconds.
- In `prices.jsonl`, **Pass:** new lines appear for each watchlist item that has at least one auction listing.
- In system chat, **Pass:** a message like `[pricetracker] Saved N prices` appears.

## Test 4 — End-to-end with watcher

- Start the watcher on your PC (see `watcher/README.md`).
- Trigger Test 2 again.
- In the watcher log, **Pass:** a line like `INFO ... POSTed 1 row(s)` appears within a few seconds.
- In a browser open `https://<your-domain>/api/items/?name=Egg`. **Pass:** the matching `Item` exists and `current_price` reflects the latest AH price.

## Reporting failures

When something fails, include:
- which test
- the exact line from `ArcheRage.log` if relevant
- the offending JSONL line if relevant
- screenshot of the in-game state
