"""Safety checks for the desktop-app tools: no real windows or keyboard are touched."""
import types

import pytest

from deskbuddy.apps import tools as apps


def _control(name, kind="Button"):
    return types.SimpleNamespace(element_info=types.SimpleNamespace(name=name, control_type=kind))


def _ctx(**controls):
    return types.SimpleNamespace(controls={i: c for i, c in enumerate(controls.values())})


def _click_risk(name):
    return apps._app_click_risk(_ctx(a=_control(name)), {"id": 0})


@pytest.mark.parametrize("name", ["Send", "Send (Ctrl+Enter)", "Delete", "Reply all", "Place order",
                                  "Sign in", "Log in", "Buy now", "Empty Recycle Bin", "Uninstall"])
def test_click_risky_names_ask(name):
    assert _click_risk(name)


@pytest.mark.parametrize("name", ["Bold", "File", "Save", ""])
def test_click_harmless_names_do_not_ask(name):
    assert not _click_risk(name)


def test_click_unknown_control_or_error_is_no_risk():
    assert not apps._app_click_risk(_ctx(), {"id": 5})
    assert not apps._app_click_risk(types.SimpleNamespace(), {"id": 0})


@pytest.mark.parametrize("keys", ["Ctrl + Enter", "enter+ctrl", "shift+delete", "Shift+Del", "alt+s",
                                  "win+r", "windows+x"])
def test_keys_risky_ask(keys):
    assert apps._app_keys_risk(None, {"keys": keys})


@pytest.mark.parametrize("keys", ["ctrl+s", "page down", "enter", "alt+f4"])
def test_keys_harmless_do_not_ask(keys):
    assert not apps._app_keys_risk(None, {"keys": keys})


def test_normalise_keys_keeps_internal_spaces():
    assert apps._normalise_keys("Page Down") == "page down"
    assert apps._normalise_keys(" Ctrl + Right Ctrl ") == "ctrl+right ctrl"
    assert apps._normalise_keys("print screen") == "print screen"


def test_app_type_refuses_password_box(monkeypatch):
    import keyboard

    def boom(*a, **k):
        raise AssertionError("typed into a password box")

    monkeypatch.setattr(keyboard, "write", boom)
    monkeypatch.setattr(apps, "_focus", lambda ctx: None)
    monkeypatch.setattr(apps, "_focused_is_password", lambda: True)
    result = apps.app_type.fn(types.SimpleNamespace(), "hunter2") if hasattr(apps.app_type, "fn") \
        else apps.app_type(types.SimpleNamespace(), "hunter2")
    assert result.ok is False
    assert "password" in result.text.lower()


def test_screen_click_adds_window_origin(monkeypatch):
    import pyautogui

    clicks = []
    monkeypatch.setattr(pyautogui, "click", lambda x, y: clicks.append((x, y)))
    monkeypatch.setattr(apps.time, "sleep", lambda s: None)
    monkeypatch.setattr(apps.win, "foreground_title", lambda: "t")
    ctx = types.SimpleNamespace(screen_scale=2.0, screen_origin=(100, 50))
    apps.screen_click(ctx, 10, 20)
    assert clicks == [(120, 90)]
