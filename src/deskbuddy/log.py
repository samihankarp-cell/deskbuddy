"""A log file for Desk Buddy, so a problem in the packaged app (no console) can still be reported.

`setup()` is called once at start-up. It writes `deskbuddy.log` in the data folder (about 1 MB, three
older copies kept), and also catches crashes that nobody would otherwise see, including errors Qt
swallows inside button handlers. Secrets (API keys, tokens, Authorization headers) are blanked out
before anything reaches the file, so the log is safe to attach to a bug report."""
import logging
import logging.handlers
import os
import re
import sys
import threading
from pathlib import Path

from deskbuddy import config

NAME = "deskbuddy"
FILE_NAME = "deskbuddy.log"
FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"
SECRET_SHAPES = re.compile(
    r"sk-[A-Za-z0-9_-]{16,}|nvapi-[A-Za-z0-9_-]{16,}|ck_[A-Za-z0-9]{16,}|gsk_[A-Za-z0-9]{16,}"
    r"|AIza[0-9A-Za-z_-]{20,}|Bearer\s+\S+")
_previous_hooks: dict[str, object] = {}
_folder: Path | None = None


def _secret_values() -> list[str]:
    """Values of key-like environment variables, longest first so a long one is not half-hidden."""
    found = {value for name, value in os.environ.items()
             if len(value) >= 8 and (name.endswith(("_KEY", "_TOKEN", "_SECRET")) or "API_KEY" in name)}
    return sorted(found, key=len, reverse=True)


def redact(text: str) -> str:
    for value in _secret_values():
        text = text.replace(value, "[redacted]")
    return SECRET_SHAPES.sub("[redacted]", text)


class RedactingFormatter(logging.Formatter):
    """Blanks secrets in the finished line. It works on the whole output (message, arguments and the
    traceback text together), so nothing can slip through the way it can when only `record.msg` is
    cleaned. Every handler uses it, which is why no separate logging filter is needed."""

    def format(self, record: logging.LogRecord) -> str:
        return redact(super().format(record))


def folder() -> Path:
    """The folder holding the log (and the rest of Desk Buddy's data)."""
    return _folder or config.data_dir()


def path() -> Path:
    return folder() / FILE_NAME


def _log_crash(kind: str, exc_type, exc_value, exc_tb) -> None:
    logging.getLogger(NAME).error("Uncaught error (%s)", kind, exc_info=(exc_type, exc_value, exc_tb))


def _excepthook(exc_type, exc_value, exc_tb) -> None:
    if not issubclass(exc_type, KeyboardInterrupt):
        _log_crash("main thread", exc_type, exc_value, exc_tb)
    previous = _previous_hooks.get("sys")
    if previous:
        previous(exc_type, exc_value, exc_tb)


def _thread_hook(args) -> None:
    _log_crash(f"thread {getattr(args.thread, 'name', '?')}", args.exc_type, args.exc_value, args.exc_traceback)
    previous = _previous_hooks.get("thread")
    if previous:
        previous(args)


def setup(folder: Path | None = None) -> Path:
    """Start logging to `<folder>/deskbuddy.log` and catch uncaught errors. Safe to call twice."""
    global _folder
    _folder = Path(folder) if folder else config.data_dir()
    _folder.mkdir(parents=True, exist_ok=True)
    target = _folder / FILE_NAME
    logger = logging.getLogger(NAME)
    logger.setLevel(logging.DEBUG if os.environ.get("DESKBUDDY_DEBUG") == "1" else logging.INFO)
    for old in [h for h in logger.handlers if getattr(h, "_deskbuddy", False)]:
        logger.removeHandler(old)   # a second call replaces our handlers instead of doubling them
        old.close()
    handlers: list[logging.Handler] = [logging.handlers.RotatingFileHandler(
        target, maxBytes=1_000_000, backupCount=3, encoding="utf-8")]
    if sys.stderr is not None:      # a windowed .exe has no stderr
        handlers.append(logging.StreamHandler())
    for handler in handlers:
        handler.setFormatter(RedactingFormatter(FORMAT))
        handler._deskbuddy = True
        logger.addHandler(handler)
    if sys.excepthook is not _excepthook:
        _previous_hooks["sys"] = sys.excepthook
        sys.excepthook = _excepthook
    if threading.excepthook is not _thread_hook:
        _previous_hooks["thread"] = threading.excepthook
        threading.excepthook = _thread_hook
    return target
