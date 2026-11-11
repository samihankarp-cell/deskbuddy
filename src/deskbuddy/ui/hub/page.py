"""The shared page frame (fixed top, scrolling list, fixed bottom) and the composer."""
from dataclasses import dataclass, field

from PySide6.QtCore import QEvent, QPoint, Qt, QTimer, Signal
from PySide6.QtWidgets import (QFrame, QHBoxLayout, QLineEdit, QMenu, QScrollArea, QToolTip,
                               QVBoxLayout, QWidget)

from deskbuddy.ui.hub.icons import GlyphButton
from deskbuddy.ui.hub.surface import Surface
from deskbuddy.ui.hub.widgets import clear, text

PAD = 28


@dataclass
class Snapshot:
    """Everything the screens show, read from memory once per refresh."""
    feed: list = field(default_factory=list)       # newest first: (ts, role, text)
    jobs: list = field(default_factory=list)       # newest first: (ts, title, passed, reason, answer)
    reminders: list = field(default_factory=list)  # (id, due, text, fired)
    prefs: list = field(default_factory=list)      # (id, text)
    notes: list = field(default_factory=list)      # (id, place, lesson)
    habits: list = field(default_factory=list)

    @property
    def waiting(self) -> list:
        return [r for r in self.reminders if not r[3]]


class Page(QWidget):
    """One section's screen. `fill(snap, query)` redraws only when the data differs."""

    def __init__(self):
        super().__init__()
        self.setObjectName("page")
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        self.top = QVBoxLayout()
        self.top.setContentsMargins(PAD, 16, PAD, 0)
        outer.addLayout(self.top)
        holder = QWidget()
        holder.setObjectName("holder")
        self.body = QVBoxLayout(holder)
        self.body.setContentsMargins(PAD, 10, PAD, 14)
        self.body.setSpacing(8)
        self.body.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setWidget(holder)
        holder.setAutoFillBackground(False)  # the column's texture shows through the list
        self.scroll.viewport().setAutoFillBackground(False)
        outer.addWidget(self.scroll, 1)
        self.foot = QVBoxLayout()
        self.foot.setContentsMargins(PAD, 4, PAD, 18)
        outer.addLayout(self.foot)
        self._shown = object()
        self._stick = False
        self.scroll.verticalScrollBar().rangeChanged.connect(self._ranged)

    def changed(self, key) -> bool:
        """True (and the list cleared) when `key` differs from what is on screen."""
        if key == self._shown:
            return False
        self._shown = key
        clear(self.body)
        return True

    def group(self, name: str) -> None:
        self.body.addWidget(text(name, "group", select=False))

    def empty(self, message: str) -> None:
        self.body.addWidget(text(message, "empty"))

    def _ranged(self, _low: int, high: int) -> None:
        if self._stick:  # the list just grew: stay at the newest item
            self.scroll.verticalScrollBar().setValue(high)

    def scroll_to_end(self) -> None:
        """Follow the bottom while the new list lays itself out."""
        self._stick = True
        QTimer.singleShot(300, lambda: setattr(self, "_stick", False))

    def fill(self, snap: Snapshot, query: str) -> None:
        raise NotImplementedError

    def focus_input(self) -> None:
        pass


def form_row(*widgets) -> QFrame:
    """A rounded grey strip holding an inline form: (widget, stretch) pairs."""
    frame = Surface("form")
    row = QHBoxLayout(frame)
    row.setContentsMargins(10, 10, 10, 10)
    row.setSpacing(8)
    for widget, stretch in widgets:
        row.addWidget(widget, stretch)
    return frame


def line_edit(placeholder: str = "", secret: bool = False, value: str = "") -> QLineEdit:
    box = QLineEdit(value)
    box.setObjectName("field")
    box.setPlaceholderText(placeholder)
    if secret:
        box.setEchoMode(QLineEdit.EchoMode.Password)
    return box


class Composer(Surface):
    """The pill at the bottom: a + for shortcuts, the text, and a black mic/send circle."""

    submitted = Signal(str)

    def __init__(self, placeholder: str, hint: str):
        super().__init__("composer")
        self.hint = hint
        self.menu_items: list[tuple[str, object]] = []
        row = QHBoxLayout(self)
        row.setContentsMargins(8, 6, 8, 6)
        row.setSpacing(8)
        self.plus = GlyphButton("plus", "More", 32, "ink", fill="soft", glyph_scale=0.5)
        self.plus.clicked.connect(self._show_menu)
        self.edit = QLineEdit()
        self.edit.setObjectName("composerEdit")
        self.edit.setPlaceholderText(placeholder)
        self.edit.setAccessibleName(placeholder.rstrip("…."))
        self.edit.returnPressed.connect(self.send)
        self.edit.textChanged.connect(self._sync)
        self.edit.installEventFilter(self)
        self.action = GlyphButton("mic", "Talk", 34, fill="strong", glyph_scale=0.5)
        self.action.clicked.connect(self._act)
        row.addWidget(self.plus)
        row.addWidget(self.edit, 1)
        row.addWidget(self.action)
        self.setProperty("focused", False)

    def eventFilter(self, obj, event) -> bool:
        if obj is self.edit and event.type() in (QEvent.Type.FocusIn, QEvent.Type.FocusOut):
            self.setProperty("focused", event.type() == QEvent.Type.FocusIn)
            self.update()
        return False

    def _sync(self, value: str) -> None:
        sending = bool(value.strip())
        self.action.set_kind("send" if sending else "mic")
        self.action.setToolTip("Send" if sending else "Talk")
        self.action.setAccessibleName("Send" if sending else "Talk")

    def _act(self) -> None:
        if self.edit.text().strip():
            self.send()
        else:
            QToolTip.showText(self.action.mapToGlobal(QPoint(-120, -44)), self.hint, self.action)

    def send(self) -> None:
        value = self.edit.text().strip()
        self.edit.clear()
        if value:
            self.submitted.emit(value)

    def _show_menu(self) -> None:
        menu = QMenu(self)
        for label, callback in self.menu_items:
            menu.addAction(label).triggered.connect(lambda _=False, c=callback: c())
        menu.exec(self.plus.mapToGlobal(QPoint(0, -menu.sizeHint().height() - 6)))
