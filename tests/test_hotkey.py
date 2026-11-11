"""The hold-to-talk key: matching by name and side, the press-a-key box, and applying it live."""
from unittest.mock import MagicMock

import keyboard
import pytest
from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QKeyEvent

from deskbuddy.ui.hub import feed_pages
from deskbuddy.ui.hub.key_capture import HINT, PROMPT, KeyCapture
from deskbuddy.ui.hub.settings_page import SettingsPage
from deskbuddy.voice import hotkey
from deskbuddy.voice.listen import Listener


def ev(name, kind="down", scan=0, keypad=False):
    return keyboard.KeyboardEvent(kind, scan, name=name, is_keypad=keypad)


# ---- matching ---------------------------------------------------------------------
def test_right_ctrl_matches_only_the_right_one():
    # what the library names the keys: left Ctrl is plain "ctrl", right Ctrl is "right ctrl"
    assert hotkey.matches(ev("Right Ctrl", scan=29), "right ctrl")
    assert not hotkey.matches(ev("Ctrl", scan=29), "right ctrl")
    assert not hotkey.matches(ev("left ctrl", scan=29), "right ctrl")


def test_right_alt_matches_but_not_left_alt():
    assert hotkey.matches(ev("right alt"), "right alt")
    assert hotkey.matches(ev("alt gr"), "right alt")      # AltGr keyboards
    assert not hotkey.matches(ev("alt"), "right alt")
    assert hotkey.matches(ev("alt"), "left alt")
    assert not hotkey.matches(ev("right alt"), "left alt")


def test_single_keys_and_spelling():
    assert hotkey.matches(ev("f8"), "F8")
    assert not hotkey.matches(ev("f9"), "f8")
    assert hotkey.matches(ev("caps lock"), "caps lock")
    assert hotkey.matches(ev("scroll lock"), "scroll lock")
    assert hotkey.matches(ev("insert"), " Insert ")
    assert hotkey.matches(ev("pause"), "pause")
    assert hotkey.matches(ev("5", keypad=True), "5")       # the keypad does not change the name


def test_a_side_less_name_means_either_side_and_unnamed_events_never_match():
    for name in ("ctrl", "left ctrl", "right ctrl"):
        assert hotkey.matches(ev(name), "ctrl")
    assert not hotkey.matches(keyboard.KeyboardEvent("down", 5), "right ctrl")


def test_names_are_friendly_and_empty_means_default():
    assert hotkey.friendly("right ctrl") == "Right Ctrl"
    assert hotkey.friendly("caps lock") == "Caps Lock"
    assert hotkey.friendly("") == "Right Ctrl"


# ---- the listener --------------------------------------------------------------------
@pytest.fixture
def ears(monkeypatch):
    fake = MagicMock()
    monkeypatch.setattr(keyboard, "hook", fake.hook)
    listener = Listener("right ctrl", "tiny")
    listener._pressed = MagicMock()
    listener._released = MagicMock()
    listener._load_model = lambda: None
    listener.fake = fake
    return listener


def test_listener_uses_one_hook_and_ignores_the_left_key(ears):
    ears.start()
    ears.fake.hook.assert_called_once_with(ears._on_key)
    ears._on_key(ev("ctrl", scan=29))
    ears._on_key(ev("ctrl", "up", scan=29))
    ears._pressed.assert_not_called()
    ears._released.assert_not_called()
    ears._on_key(ev("right ctrl", scan=29))
    ears._pressed.assert_called_once()
    ears._on_key(ev("right ctrl", "up", scan=29))
    ears._released.assert_called_once()


def test_listener_escape_still_works(ears, qtbot):
    with qtbot.waitSignal(ears.escape, timeout=1000):
        ears._on_key(ev("esc"))
    with qtbot.assertNotEmitted(ears.escape):
        ears._on_key(ev("esc", "up"))


def test_held_key_repeat_is_ignored(monkeypatch):
    """The real _pressed: a repeat while the key is held must not restart the recording."""
    listener = Listener("f8", "tiny")
    started = []
    fake_sd = MagicMock()
    fake_sd.InputStream.side_effect = lambda **kw: started.append(1) or MagicMock()
    monkeypatch.setitem(__import__("sys").modules, "sounddevice", fake_sd)
    for _ in range(5):  # the OS repeats key-down while held
        listener._on_key(ev("f8"))
    assert len(started) == 1


def test_set_hotkey_switches_the_key_without_another_hook(ears):
    ears.start()
    ears.set_hotkey("Right Alt")
    ears._on_key(ev("right ctrl"))
    ears._pressed.assert_not_called()
    ears._on_key(ev("right alt"))
    ears._pressed.assert_called_once()
    ears.fake.hook.assert_called_once()   # still the one global hook


# ---- the press-a-key box -----------------------------------------------------------------
CTRL, ALT, SHIFT = Qt.Key.Key_Control, Qt.Key.Key_Alt, Qt.Key.Key_Shift


def press(box, key, vk=0, scan=0, mods=0, text="", repeat=False):
    """Deliver a key press the way Qt on Windows would (generic vk, extended scan code)."""
    event = QKeyEvent(QEvent.Type.KeyPress, key, Qt.KeyboardModifier.NoModifier, scan, vk, mods,
                      text, repeat)
    box.event(event)


@pytest.fixture
def box(qtbot):
    widget = KeyCapture()
    qtbot.addWidget(widget)
    widget.show()
    return widget


def test_box_shows_the_key_in_friendly_form_and_is_a_keyCapture(box):
    assert box.objectName() == "keyCapture"
    assert box.text() == "Right Ctrl"
    assert KeyCapture("caps lock").text() == "Caps Lock"


def test_click_then_right_ctrl_is_picked(qtbot, box):
    box.set_key("f8")
    qtbot.mouseClick(box, Qt.MouseButton.LeftButton)
    assert box.recording and box.text() == PROMPT
    with qtbot.waitSignal(box.picked) as got:
        press(box, CTRL, vk=0x11, scan=0xE01D, mods=0x1000200)
    assert got.args == ["right ctrl"]
    assert box.text() == "Right Ctrl" and not box.recording


def test_left_ctrl_is_refused_with_a_hint_and_recording_goes_on(qtbot, box):
    box.start()
    with qtbot.waitSignal(box.rejected) as got:
        press(box, CTRL, vk=0x11, scan=0x1D, mods=0x200)
    assert got.args == [HINT] and box.recording


def test_other_sides_and_keys(qtbot, box):
    cases = [
        (ALT, 0x12, 0xE038, "right alt"), (ALT, 0x12, 0x38, None),
        (SHIFT, 0x10, 0x36, "right shift"), (SHIFT, 0x10, 0x2A, None),
        (CTRL, 0xA3, 0x1D, "right ctrl"), (CTRL, 0xA2, 0x1D, None),   # if Qt gives sided vks
        (Qt.Key.Key_F8, 0x77, 0x42, "f8"), (Qt.Key.Key_CapsLock, 0x14, 0x3A, "caps lock"),
        (Qt.Key.Key_ScrollLock, 0x91, 0x46, "scroll lock"), (Qt.Key.Key_Pause, 0x13, 0x45, "pause"),
        (Qt.Key.Key_Insert, 0x2D, 0xE052, "insert"),
        (Qt.Key.Key_Meta, 0x5B, 0xE05B, None),    # the Windows key
        (Qt.Key.Key_Backspace, 0x08, 0x0E, None), (Qt.Key.Key_Delete, 0x2E, 0xE053, None),
        (Qt.Key.Key_Return, 0x0D, 0x1C, None), (Qt.Key.Key_Tab, 0x09, 0x0F, None),
        (Qt.Key.Key_Space, 0x20, 0x39, None), (Qt.Key.Key_A, 0x41, 0x1E, None),
        (Qt.Key.Key_5, 0x35, 0x06, None),
    ]
    for key, vk, scan, expected in cases:
        box.start()
        signal = box.picked if expected else box.rejected
        with qtbot.waitSignal(signal, timeout=500) as got:
            press(box, key, vk=vk, scan=scan, text="a" if key == Qt.Key.Key_A else "")
        assert got.args == [expected or HINT], (key, vk, scan)


def test_escape_cancels_and_keeps_the_old_key(qtbot, box):
    box.start()
    with qtbot.assertNotEmitted(box.picked):
        press(box, Qt.Key.Key_Escape)
    assert not box.recording and box.text() == "Right Ctrl"


def test_key_repeat_and_clicking_away_do_not_pick(qtbot, box):
    box.start()
    with qtbot.assertNotEmitted(box.picked):
        press(box, Qt.Key.Key_F8, vk=0x77, scan=0x42, repeat=True)
        box.clearFocus()
    assert not box.recording


# ---- saving and applying live --------------------------------------------------------------
@pytest.fixture
def page(qtbot, tmp_path, monkeypatch):
    monkeypatch.setenv("DESKBUDDY_HOTKEY", "right ctrl")
    memory = MagicMock()
    memory.get.return_value = "1"
    widget = SettingsPage(memory, tmp_path / ".env")
    qtbot.addWidget(widget)
    widget.show()
    return widget


def test_picking_a_key_saves_to_env_and_emits_and_says_how_to_talk(qtbot, page, tmp_path):
    page.hotkey.start()
    with qtbot.waitSignal(page.hotkey_changed) as got:
        press(page.hotkey, ALT, vk=0x12, scan=0xE038, mods=0x1000200)
    assert got.args == ["right alt"]
    assert "DESKBUDDY_HOTKEY=right alt" in (tmp_path / ".env").read_text()
    assert page.saved.text() == "Saved. Hold Right Alt to talk."
    assert feed_pages.hotkey_name() == "Right Alt"


def test_a_refused_key_writes_nothing_and_shows_the_hint(qtbot, page, tmp_path):
    page.hotkey.start()
    with qtbot.assertNotEmitted(page.hotkey_changed):
        press(page.hotkey, Qt.Key.Key_A, vk=0x41, scan=0x1E, text="a")
    assert not (tmp_path / ".env").exists()
    assert page.saved.text() == HINT


def test_reset_restores_right_ctrl(qtbot, page, tmp_path):
    page.hotkey.set_key("f8")
    reset = next(b for b in page.findChildren(type(page.save_button)) if b.text() == "Reset")
    with qtbot.waitSignal(page.hotkey_changed) as got:
        qtbot.mouseClick(reset, Qt.MouseButton.LeftButton)
    assert got.args == ["right ctrl"] and page.hotkey.text() == "Right Ctrl"
    assert "DESKBUDDY_HOTKEY=right ctrl" in (tmp_path / ".env").read_text()


def test_the_hotkey_row_is_not_part_of_the_plain_save(page):
    assert "DESKBUDDY_HOTKEY" not in page.boxes


def test_dashboard_forwards_the_change_to_the_app(qtbot, tmp_path, monkeypatch):
    from deskbuddy.memory.db import Memory
    from deskbuddy.ui.hub import styles
    from deskbuddy.ui.hub.window import Dashboard

    monkeypatch.setenv("DESKBUDDY_HOTKEY", "right ctrl")
    memory = Memory(tmp_path / "m.db")
    try:
        dash = Dashboard(memory, lambda _t: None, env_file=tmp_path / ".env")
        qtbot.addWidget(dash)
        with qtbot.waitSignal(dash.hotkey_changed) as got:
            dash.settings.hotkey.start()
            press(dash.settings.hotkey, Qt.Key.Key_F8, vk=0x77, scan=0x42)
        assert got.args == ["f8"]
        assert "F8" in dash.updates.composer.hint
    finally:
        styles.set_active("classic")
        memory._db.close()
