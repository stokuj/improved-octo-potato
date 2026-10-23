import io
import json
import logging
import re
import uuid
from datetime import datetime

from app.core.logging import JsonFormatter, configure_logging, get_logger, request_id


def _line(call) -> dict:
    """Run call(get_logger("app.test")) with a StringIO JSON handler; return the last line."""
    target = logging.getLogger("app.test")
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JsonFormatter())
    saved = target.handlers, target.propagate, target.level
    target.handlers, target.propagate = [handler], False
    target.setLevel(logging.DEBUG)
    try:
        call(get_logger("app.test"))
    finally:
        target.handlers, target.propagate = saved[0], saved[1]
        target.setLevel(saved[2])
    return json.loads(stream.getvalue().splitlines()[-1])


def test_line_has_event_fields_and_request_id():
    token = request_id.set("abc-123")
    try:
        line = _line(lambda log: log.info("import.done", rows=3, connector="market"))
    finally:
        request_id.reset(token)
    assert list(line)[:5] == ["ts", "level", "module", "event", "request_id"]
    assert line["level"] == "INFO"
    assert line["module"] == "app.test"
    assert line["event"] == "import.done"
    assert line["request_id"] == "abc-123"
    assert line["rows"] == 3 and line["connector"] == "market"
    assert re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{3}Z", line["ts"])


def test_request_id_outside_a_request_is_dash():
    assert _line(lambda log: log.info("x.y"))["request_id"] == "-"


def test_exception_goes_under_exc():
    def call(log):
        try:
            raise ValueError("boom")
        except ValueError:
            log.exception("x.failed", item_type=7)

    line = _line(call)
    assert line["level"] == "ERROR"
    assert "ValueError: boom" in line["exc"]
    assert line["item_type"] == 7


def test_unserialisable_fields_become_strings():
    when = datetime(2026, 10, 23, 18, 0)
    who = uuid.UUID(int=1)
    line = _line(lambda log: log.info("x.y", at=when, who=who, err=OSError("down")))
    assert line["at"] == str(when)
    assert line["who"] == str(who)
    assert line["err"] == "down"


def test_configure_logging_is_idempotent_and_keeps_other_handlers(caplog):
    configure_logging("INFO")
    configure_logging("INFO")
    root = logging.getLogger()
    ours = [h for h in root.handlers if isinstance(h.formatter, JsonFormatter)]
    assert len(ours) == 1
    assert caplog.handler in root.handlers
    # Uvicorn's access line carries the query string; http.request replaces it.
    access = logging.getLogger("uvicorn.access")
    assert access.handlers == [] and not access.propagate
    error = logging.getLogger("uvicorn.error")
    assert error.handlers == [] and error.propagate
