import json
from pathlib import Path

from watcher.client import SendOutcome
from watcher.config import WatcherSettings
from watcher.main import run_once


class FakeClient:
    def __init__(self, outcome: SendOutcome):
        self.outcome = outcome
        self.calls: list[list[dict]] = []

    async def send_batch(self, rows):
        self.calls.append(rows)
        return self.outcome


def _line(name: str = "Egg") -> str:
    return (
        json.dumps(
            {"name": name, "grade": 1, "price": 1, "ts": "2026-05-16T18:30:00", "source": "ah"}
        )
        + "\n"
    )


async def test_run_once_advances_offset_on_success(tmp_path: Path):
    jsonl = tmp_path / "prices.jsonl"
    jsonl.write_text(_line() + _line())
    state_path = tmp_path / "state"
    settings = WatcherSettings(jsonl_path=jsonl, state_path=state_path)
    client = FakeClient(SendOutcome.SUCCESS)

    advanced = await run_once(settings, client)

    assert advanced is True
    assert int(state_path.read_text()) == jsonl.stat().st_size


async def test_run_once_keeps_offset_on_retry(tmp_path: Path):
    jsonl = tmp_path / "prices.jsonl"
    jsonl.write_text(_line())
    state_path = tmp_path / "state"
    settings = WatcherSettings(jsonl_path=jsonl, state_path=state_path)
    client = FakeClient(SendOutcome.RETRY)

    advanced = await run_once(settings, client)

    assert advanced is False
    assert not state_path.exists() or int(state_path.read_text()) == 0


async def test_run_once_advances_offset_on_skip(tmp_path: Path):
    jsonl = tmp_path / "prices.jsonl"
    jsonl.write_text(_line())
    state_path = tmp_path / "state"
    settings = WatcherSettings(jsonl_path=jsonl, state_path=state_path)
    client = FakeClient(SendOutcome.SKIP)

    advanced = await run_once(settings, client)

    assert advanced is True
    assert int(state_path.read_text()) == jsonl.stat().st_size


async def test_run_once_returns_false_when_no_new_lines(tmp_path: Path):
    jsonl = tmp_path / "prices.jsonl"
    jsonl.write_text("")
    state_path = tmp_path / "state"
    settings = WatcherSettings(jsonl_path=jsonl, state_path=state_path)
    client = FakeClient(SendOutcome.SUCCESS)

    advanced = await run_once(settings, client)
    assert advanced is False


async def test_run_once_resets_offset_on_truncation(tmp_path: Path):
    jsonl = tmp_path / "prices.jsonl"
    jsonl.write_text(_line() * 5)
    state_path = tmp_path / "state"
    state_path.write_text("99999")  # offset way past file size
    settings = WatcherSettings(jsonl_path=jsonl, state_path=state_path)
    client = FakeClient(SendOutcome.SUCCESS)

    advanced = await run_once(settings, client)

    assert advanced is True
    assert int(state_path.read_text()) == jsonl.stat().st_size


async def test_run_once_batches_max_size(tmp_path: Path):
    jsonl = tmp_path / "prices.jsonl"
    jsonl.write_text(_line() * 5)
    state_path = tmp_path / "state"
    settings = WatcherSettings(jsonl_path=jsonl, state_path=state_path, batch_size=2)
    client = FakeClient(SendOutcome.SUCCESS)

    await run_once(settings, client)
    # 5 lines → 3 batches (2+2+1)
    assert len(client.calls) == 3
    assert len(client.calls[0]) == 2
    assert len(client.calls[1]) == 2
    assert len(client.calls[2]) == 1


async def test_run_once_skips_malformed_json(tmp_path: Path):
    jsonl = tmp_path / "prices.jsonl"
    jsonl.write_text("not json\n" + _line())
    state_path = tmp_path / "state"
    settings = WatcherSettings(jsonl_path=jsonl, state_path=state_path)
    client = FakeClient(SendOutcome.SUCCESS)

    advanced = await run_once(settings, client)

    # Malformed line is skipped, valid line is sent
    assert advanced is True
    assert len(client.calls) == 1
    assert len(client.calls[0]) == 1
