import asyncio
import json
import logging
from typing import Protocol

from watcher.client import IngestClient, SendOutcome
from watcher.config import WatcherSettings, load_settings
from watcher.reader import detect_truncation, read_new_lines
from watcher.state import WatcherState

log = logging.getLogger("watcher")


class _ClientProtocol(Protocol):
    async def send_batch(self, rows: list[dict]) -> SendOutcome: ...


def _parse_lines(lines: list[str]) -> list[dict]:
    rows: list[dict] = []
    for line in lines:
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            log.warning("skipping malformed JSON line: %r", line[:80])
            continue
    return rows


async def run_once(settings: WatcherSettings, client: _ClientProtocol) -> bool:
    """One iteration of the loop. Returns True if any progress was made."""
    state = WatcherState(path=settings.state_path)

    if detect_truncation(settings.jsonl_path, state.offset):
        log.warning("file truncation detected, resetting offset")
        state.offset = 0
        state.save()

    lines, new_offset = read_new_lines(settings.jsonl_path, state.offset)
    if not lines:
        return False

    rows = _parse_lines(lines)
    if not rows:
        # All lines were malformed — still advance offset so we don't re-read them.
        state.offset = new_offset
        state.save()
        return True

    for chunk_start in range(0, len(rows), settings.batch_size):
        chunk = rows[chunk_start : chunk_start + settings.batch_size]
        outcome = await client.send_batch(chunk)
        if outcome is SendOutcome.RETRY:
            return False  # leave offset where it was

    state.offset = new_offset
    state.save()
    return True


async def _loop(settings: WatcherSettings) -> None:
    client = IngestClient(api_url=settings.api_url, timeout=settings.request_timeout_seconds)
    backoff = settings.backoff_initial_seconds
    while True:
        try:
            progressed = await run_once(settings, client)
        except Exception:
            log.exception("unexpected error in run_once")
            progressed = False

        if progressed:
            backoff = settings.backoff_initial_seconds
            await asyncio.sleep(settings.poll_interval_seconds)
        else:
            await asyncio.sleep(min(backoff, settings.backoff_max_seconds))
            backoff = min(backoff * 2, settings.backoff_max_seconds)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    settings = load_settings()
    log.info("starting watcher: %s -> %s", settings.jsonl_path, settings.api_url)
    asyncio.run(_loop(settings))


if __name__ == "__main__":
    main()
