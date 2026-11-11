"""A box that records the key you press, for choosing the hold-to-talk key.

Click it, press the key you want. Left and right Ctrl / Shift / Alt are told apart. Keys you type
with every day (letters, Enter, left Ctrl...) are refused with a short hint.
"""
from PySide6.QtCore import QEvent, Qt, Signal
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import QLineEdit

from deskbuddy.voice import hotkey

HINT = "Pick a key you don't type with, like Right Ctrl, Right Alt, F8 or Caps Lock."
PROMPT = "Press a key…"

# Windows virtual keys that already say which side they are.
_VK_SIDED = {0xA3: "right ctrl", 0xA1: "right shift", 0xA5: "right alt",
             0xA2: None, 0xA0: None, 0xA4: None}   # None: the left-hand ones, refused
_EXTENDED = 0xE000            # nativeScanCode of an "extended" key (the right Ctrl / Alt) is 0xE0xx
_RIGHT_SHIFT_SCAN = 0x36      # right Shift is not extended: only its scan code differs

K = Qt.Key
_PLAIN = {K.Key_CapsLock: "caps lock", K.Key_ScrollLock: "scroll lock", K.Key_Pause: "pause",
          K.Key_Insert: "insert", K.Key_Print: "print screen", K.Key_Menu: "menu"}
_FKEYS = {getattr(K, f"Key_F{n}"): f"f{n}" for n in range(1, 25)}


def key_name(key: int, vk: int = 0, scan: int = 0, native_mods: int = 0) -> str | None:
    """The `keyboard` library's name for a pressed key, or None if it is not a good talk key.

    Qt on Windows reports plain Ctrl/Shift/Alt with the generic virtual key (0x11/0x10/0x12) for
    both sides, so the side comes from the scan code: extended (0xE0xx) means right for Ctrl and
    Alt, 0x36 means right Shift.
    """
    if vk in _VK_SIDED:
        return _VK_SIDED[vk]
    extended = bool(scan & _EXTENDED) or bool(native_mods & 0x1000000)
    if key == K.Key_Control:
        return "right ctrl" if extended else None
    if key == K.Key_Alt:
        return "right alt" if extended else None
    if key == K.Key_AltGr:
        return "right alt"
    if key == K.Key_Shift:
        return "right shift" if (scan & 0xFF) == _RIGHT_SHIFT_SCAN else None
    return _PLAIN.get(key) or _FKEYS.get(key)


def event_key_name(event: QKeyEvent) -> str | None:
    return key_name(event.key(), event.nativeVirtualKey(), event.nativeScanCode(),
                    event.nativeModifiers())


class KeyCapture(QLineEdit):
    picked = Signal(str)     # a good key was pressed: its `keyboard` name
    rejected = Signal(str)   # a key that is not suitable: the hint to show
    recording = False        # class defaults: Qt sends events while the base class is still starting
    key = hotkey.DEFAULT

    def __init__(self, key: str = hotkey.DEFAULT):
        super().__init__()
        self.setObjectName("keyCapture")
        self.setReadOnly(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAccessibleName("Hold-to-talk key")
        self.set_key(key)

    def set_key(self, key: str) -> None:
        self.key = hotkey.normalize(key)
        self.stop()

    def start(self) -> None:
        self.recording = True
        self.setText(PROMPT)
        self.setFocus()
        self._restyle()

    def stop(self) -> None:
        """Leave recording and show the chosen key again."""
        self.recording = False
        self.setText(hotkey.friendly(self.key))
        self._restyle()

    def _restyle(self) -> None:
        self.setProperty("recording", self.recording)   # the look's stylesheet can colour it
        self.style().unpolish(self)
        self.style().polish(self)

    def mousePressEvent(self, event) -> None:
        self.start()
        event.accept()

    def focusOutEvent(self, event) -> None:
        if self.recording:
            self.stop()
        super().focusOutEvent(event)

    def event(self, event) -> bool:
        if self.recording and event.type() in (QEvent.Type.ShortcutOverride, QEvent.Type.KeyPress):
            if event.type() == QEvent.Type.KeyPress:  # skip Tab focus-moving and shortcuts
                self.keyPressEvent(event)
            event.accept()
            return True
        return super().event(event)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if not self.recording:
            if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space):
                self.start()
            else:
                event.ignore()
            return
        if event.isAutoRepeat():
            return
        if event.key() == Qt.Key.Key_Escape:
            self.stop()
            return
        name = event_key_name(event)
        if name is None:
            self.rejected.emit(HINT)
            return
        self.set_key(name)
        self.picked.emit(name)
