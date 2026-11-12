"""The log file: it is written once, hides secrets (also inside tracebacks) and records crashes."""
import logging
import sys
import threading

import pytest

from deskbuddy import log


@pytest.fixture
def logfile(tmp_path, monkeypatch):
    """Set logging up in tmp_path and put the global state back afterwards."""
    monkeypatch.delenv("DESKBUDDY_DEBUG", raising=False)
    saved = (sys.excepthook, threading.excepthook, dict(log._previous_hooks), log._folder)
    logger = logging.getLogger(log.NAME)
    before = list(logger.handlers)
    target = log.setup(tmp_path)
    yield target
    for handler in list(logger.handlers):
        if handler not in before:
            logger.removeHandler(handler)
            handler.close()
    sys.excepthook, threading.excepthook = saved[0], saved[1]
    log._previous_hooks.clear()
    log._previous_hooks.update(saved[2])
    log._folder = saved[3]


def _text(target) -> str:
    for handler in logging.getLogger(log.NAME).handlers:
        handler.flush()
    return target.read_text(encoding="utf-8")


def test_setup_writes_to_the_file(logfile, tmp_path):
    assert logfile == tmp_path / "deskbuddy.log" == log.path()
    logging.getLogger("deskbuddy.test").info("hello there")
    assert "INFO deskbuddy.test: hello there" in _text(logfile)


def test_setup_twice_does_not_duplicate_lines(logfile, tmp_path):
    log.setup(tmp_path)
    logging.getLogger("deskbuddy.test").info("only once")
    assert _text(logfile).count("only once") == 1


def test_secrets_are_redacted_in_messages(logfile, monkeypatch):
    monkeypatch.setenv("DESKBUDDY_API_KEY", "my-secret-value-123")
    logger = logging.getLogger("deskbuddy.test")
    logger.info("key sk-abcdefghijklmnopqrstuvwx used")
    logger.info("header %s", "Authorization: Bearer xyz")
    logger.info("env value my-secret-value-123 leaked")
    text = _text(logfile)
    assert "sk-abcdefgh" not in text and "Bearer xyz" not in text and "my-secret-value-123" not in text
    assert text.count("[redacted]") == 3


def test_secrets_are_redacted_in_tracebacks(logfile, monkeypatch):
    monkeypatch.setenv("DESKBUDDY_API_KEY", "my-secret-value-123")
    try:
        raise RuntimeError("bad key my-secret-value-123 and sk-abcdefghijklmnopqrstuvwx")
    except RuntimeError:
        logging.getLogger("deskbuddy.test").exception("call failed")
    text = _text(logfile)
    assert "RuntimeError" in text and "call failed" in text
    assert "my-secret-value-123" not in text and "sk-abcdefgh" not in text


def test_excepthook_logs_an_uncaught_error_and_calls_the_old_hook(logfile, monkeypatch):
    seen = []
    log._previous_hooks["sys"] = lambda *args: seen.append(args[0])
    try:
        raise ValueError("boom")
    except ValueError as error:
        sys.excepthook(type(error), error, error.__traceback__)
    text = _text(logfile)
    assert "ERROR deskbuddy: Uncaught error" in text and "ValueError: boom" in text
    assert seen == [ValueError]


def test_settings_page_has_an_open_logs_button(qtbot, tmp_path):
    from deskbuddy.memory.db import Memory
    from deskbuddy.ui.hub.settings_page import SettingsPage

    page = SettingsPage(Memory(tmp_path / "m.db"), env_file=tmp_path / "x.env")
    qtbot.addWidget(page)
    assert page.logs_button.text() == "Open logs folder"
