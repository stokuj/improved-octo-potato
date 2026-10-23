# JSON-lines logging for the whole app, configured once, with the request id from a contextvar.
import json
import logging
import re
import sys
import time
import uuid
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
    root.setLevel(level.upper())
    for name in ("uvicorn", "uvicorn.error"):
        logger = logging.getLogger(name)
        logger.handlers = []
        logger.propagate = True
    # Off for good: its line carries the query string, and http.request replaces it.
    access = logging.getLogger("uvicorn.access")
    access.handlers = []
    access.propagate = False


_VALID_ID = re.compile(r"[A-Za-z0-9-]{1,64}")
_http_log = get_logger("app.http")


class RequestIdMiddleware:
    """Sets the request id, echoes it as X-Request-ID and logs one `http.request` line."""

    def __init__(self, app) -> None:
        self.app = app

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        incoming = dict(scope["headers"]).get(b"x-request-id", b"").decode("latin-1")
        rid = incoming if _VALID_ID.fullmatch(incoming) else uuid.uuid4().hex
        token = request_id.set(rid)
        status = 500  # stays 500 when the app fails before it starts a response
        started = time.perf_counter()

        async def send_with_id(message) -> None:
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
                headers = [*message.get("headers", []), (b"x-request-id", rid.encode())]
                message = {**message, "headers": headers}
            await send(message)

        try:
            await self.app(scope, receive, send_with_id)
        except Exception:
            # Uvicorn logs the traceback only after the id is reset; log it here with the id.
            _http_log.exception(
                "http.failed", method=scope["method"], path=scope["path"]
            )
            raise
        finally:
            ms = round((time.perf_counter() - started) * 1000, 1)
            # Path only: a query string can carry an OAuth code.
            _http_log.info(
                "http.request",
                method=scope["method"],
                path=scope["path"],
                status=status,
                ms=ms,
            )
            request_id.reset(token)
