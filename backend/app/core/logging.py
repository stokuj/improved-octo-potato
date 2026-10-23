# JSON-lines logging for the whole app, configured once, with the request id from a contextvar.
import json
import logging
import sys
from contextvars import ContextVar
from datetime import UTC, datetime

request_id: ContextVar[str] = ContextVar("request_id", default="-")


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        ts = datetime.fromtimestamp(record.created, UTC)
        line = {
            "ts": f"{ts:%Y-%m-%dT%H:%M:%S}.{int(record.msecs):03d}Z",
            "level": record.levelname,
            "module": record.name,
            "event": record.getMessage(),
            # Third-party records carry no id of their own; read it while still in the request.
            "request_id": getattr(record, "request_id", request_id.get()),
            **getattr(record, "fields", {}),
        }
        if record.exc_info:
            line["exc"] = self.formatException(record.exc_info)
        return json.dumps(line, default=str)


class EventLogger:
    """`log.info("module.verb", **fields)`: the event name is the message, fields go to the line."""

    def __init__(self, name: str) -> None:
        self._log = logging.getLogger(name)

    def _emit(
        self, level: int, event: str, fields: dict, exc_info: bool = False
    ) -> None:
        extra = {"fields": fields, "request_id": request_id.get()}
        self._log.log(level, event, exc_info=exc_info, extra=extra, stacklevel=3)

    def debug(self, event: str, **fields) -> None:
        self._emit(logging.DEBUG, event, fields)

    def info(self, event: str, **fields) -> None:
        self._emit(logging.INFO, event, fields)

    def warning(self, event: str, **fields) -> None:
        self._emit(logging.WARNING, event, fields)

    def error(self, event: str, **fields) -> None:
        self._emit(logging.ERROR, event, fields)

    def exception(self, event: str, **fields) -> None:
        self._emit(logging.ERROR, event, fields, exc_info=True)


def get_logger(name: str) -> EventLogger:
    return EventLogger(name)


def configure_logging(level: str = "INFO") -> None:
    root = logging.getLogger()
    # Replace only our own handler, so a second call (or pytest's caplog) is left alone.
    for handler in [h for h in root.handlers if getattr(h, "_app_json", False)]:
        root.removeHandler(handler)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    handler._app_json = True
    root.addHandler(handler)
    root.setLevel(level)
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        logger = logging.getLogger(name)
        logger.handlers = []
        logger.propagate = True
