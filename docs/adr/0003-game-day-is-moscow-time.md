# The game day is a Moscow-time day

Status: accepted (2026-10-23)

ArcheMarket saves the game's own statistics for an item as 14 days, where day 14 is today and still open. A row carries only a day index and `captured_at` in epoch seconds, which has no timezone. To store a market day we must turn the index into a date, so we must pick the day boundary.

The ArcheRage server runs on Moscow time, so a game day is a day in Moscow time: `day_date = date(captured_at at UTC+3) − (14 − day)`. Moscow has no daylight saving time, so the offset is one fixed constant in the market module.

## Considered options

- **UTC.** Rejected: a scan taken between 21:00 and 24:00 UTC would land every row one day early. Because the newest scan wins, those wrong rows would overwrite correct ones.
- **The user's local time (Europe/Warsaw).** Rejected for the same reason: it is not the server's clock.

## Consequences

- A test covers a scan at 21:30 UTC that lands on the next Moscow date.
- Timestamps are still stored as naive UTC. Only the derived date uses Moscow time.
- Today's market day is partial, and the game's 7-day average includes it, so the app's 7-day average is the game's value for the day before today.
