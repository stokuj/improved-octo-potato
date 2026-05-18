from pathlib import Path

from watcher.reader import detect_truncation, read_new_lines


def test_read_new_lines_from_offset_zero(tmp_path: Path):
    p = tmp_path / "prices.jsonl"
    p.write_text("one\ntwo\nthree\n")
    lines, new_offset = read_new_lines(p, offset=0)
    assert lines == ["one", "two", "three"]
    assert new_offset == len("one\ntwo\nthree\n")


def test_read_new_lines_from_mid_offset(tmp_path: Path):
    p = tmp_path / "prices.jsonl"
    p.write_text("one\ntwo\nthree\n")
    skip = len("one\n")
    lines, new_offset = read_new_lines(p, offset=skip)
    assert lines == ["two", "three"]
    assert new_offset == len("one\ntwo\nthree\n")


def test_read_new_lines_returns_empty_when_no_new_data(tmp_path: Path):
    p = tmp_path / "prices.jsonl"
    p.write_text("one\n")
    lines, new_offset = read_new_lines(p, offset=len("one\n"))
    assert lines == []
    assert new_offset == len("one\n")


def test_read_new_lines_excludes_incomplete_trailing_line(tmp_path: Path):
    """Half-written line (no trailing newline) is not consumed — wait for next poll."""
    p = tmp_path / "prices.jsonl"
    p.write_text("one\ntwo\nthr")
    lines, new_offset = read_new_lines(p, offset=0)
    assert lines == ["one", "two"]
    assert new_offset == len("one\ntwo\n")


def test_read_new_lines_handles_missing_file(tmp_path: Path):
    lines, new_offset = read_new_lines(tmp_path / "nope.jsonl", offset=0)
    assert lines == []
    assert new_offset == 0


def test_detect_truncation_true_when_size_less_than_offset(tmp_path: Path):
    p = tmp_path / "f"
    p.write_text("abc")
    assert detect_truncation(p, offset=100) is True


def test_detect_truncation_false_when_size_ge_offset(tmp_path: Path):
    p = tmp_path / "f"
    p.write_text("abcdef")
    assert detect_truncation(p, offset=3) is False


def test_detect_truncation_false_when_file_missing(tmp_path: Path):
    assert detect_truncation(tmp_path / "nope", offset=10) is False
