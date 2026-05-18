from pathlib import Path

from watcher.state import WatcherState


def test_load_returns_zero_when_state_file_missing(tmp_path: Path):
    state = WatcherState(path=tmp_path / "missing.state")
    assert state.offset == 0


def test_save_then_load_roundtrip(tmp_path: Path):
    p = tmp_path / "state"
    state = WatcherState(path=p)
    state.offset = 500
    state.save()

    reloaded = WatcherState(path=p)
    assert reloaded.offset == 500


def test_load_handles_malformed_state_file(tmp_path: Path):
    p = tmp_path / "state"
    p.write_text("not a number")
    state = WatcherState(path=p)
    assert state.offset == 0


def test_save_creates_parent_dir(tmp_path: Path):
    nested = tmp_path / "a" / "b" / "state"
    state = WatcherState(path=nested)
    state.offset = 7
    state.save()
    assert nested.read_text() == "7"
