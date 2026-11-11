"""The small pieces the pages are made of: labels, pills, bubbles, notes, cards, the toggle."""
from PySide6.QtCore import QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QFontMetrics, QPainter
from PySide6.QtWidgets import (QAbstractButton, QHBoxLayout, QLabel, QPushButton,
                               QVBoxLayout, QWidget)

from deskbuddy.ui.hub import styles, theme
from deskbuddy.ui.hub.icons import Blob, draw_glyph
from deskbuddy.ui.hub.surface import Surface

BUBBLE_MAX = 540


def clear(layout) -> None:
    while layout.count():
        item = layout.takeAt(0)
        widget = item.widget()
        if widget:
            widget.setParent(None)  # gone from the screen at once, freed when Qt is idle
            widget.deleteLater()
        elif item.layout():
            clear(item.layout())


def text(value: str, name: str, wrap: bool = True, select: bool = True) -> QLabel:
    label = QLabel(value)
    label.setObjectName(name)
    label.setWordWrap(wrap)
    label.setTextFormat(Qt.TextFormat.PlainText)
    if select:
        label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
    return label


def button(caption: str, name: str, on_click) -> QPushButton:
    widget = QPushButton(caption)
    widget.setObjectName(name)
    widget.setCursor(Qt.CursorShape.PointingHandCursor)
    widget.clicked.connect(lambda _=False: on_click())
    return widget


def matches(query: str, *parts: str) -> bool:
    """Simple case-insensitive substring filter used by the search box."""
    query = query.strip().lower()
    return not query or any(query in (part or "").lower() for part in parts)


class Pill(QLabel):
    """A verdict or state as a word, so it never rests on colour alone. The look paints its shape."""

    def __init__(self, kind: str):
        word, self.group = theme.PILLS[kind]
        super().__init__(word)
        self.setObjectName("pill")
        self.setContentsMargins(9, 2, 9, 2)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        style = styles.active()
        rect = QRectF(self.rect())
        ink = style.paint_pill(p, rect, self.group)
        shadow = style.text_shadow("pill")
        flags = int(Qt.AlignmentFlag.AlignCenter)
        p.setFont(self.font())
        if shadow:
            p.setPen(QColor(shadow[2]))
            p.drawText(rect.translated(shadow[0], shadow[1]), flags, self.text())
        p.setPen(QColor(ink))
        p.drawText(rect, flags, self.text())
        p.end()


def pill(kind: str) -> QLabel:
    return Pill(kind)


def day_label(value: str) -> QLabel:
    label = text(value, "dayLabel", wrap=False, select=False)
    label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
    return label


def _natural_width(line: str, px: int = 13) -> int:
    """Width of the longest line when not wrapped, so a short message gets a snug bubble."""
    metrics = QFontMetrics(theme.ui_font(px))
    return max(metrics.horizontalAdvance(part) for part in line.splitlines() or [""]) + 8


def bubble(line: str, ts: float, mine: bool = False, kind: str = "") -> QWidget:
    """A chat bubble: the user's orders are black on the right, Desk Buddy's items grey on the left."""
    row = QWidget()
    outer = QHBoxLayout(row)
    outer.setContentsMargins(0, 0, 0, 0)
    column = QWidget()
    column.setMaximumWidth(BUBBLE_MAX)
    box = QVBoxLayout(column)
    box.setContentsMargins(0, 0, 0, 0)
    box.setSpacing(3)
    frame = Surface("bubbleMe" if mine else "bubbleBot")
    inner = QVBoxLayout(frame)
    inner.setContentsMargins(14, 10, 14, 10)
    inner.setSpacing(6)
    if kind:
        inner.addWidget(pill(kind), 0, Qt.AlignmentFlag.AlignLeft)
    label = text(line, "bubbleMeText" if mine else "bubbleBotText")
    label.setMinimumWidth(min(_natural_width(line), BUBBLE_MAX - 28))  # wrap only past the maximum
    inner.addWidget(label)
    box.addWidget(frame)
    stamp = text(theme.clock(ts), "stamp", wrap=False, select=False)
    stamp.setAlignment(Qt.AlignmentFlag.AlignRight if mine else Qt.AlignmentFlag.AlignLeft)
    stamp.setContentsMargins(6, 0, 6, 0)
    box.addWidget(stamp)
    if mine:
        outer.addStretch(1)
        outer.addWidget(column)
    else:
        outer.addWidget(column)
        outer.addStretch(1)
    return row


def note(line: str, ts: float, glyph: str = "clock") -> QWidget:
    """A small centred system note, e.g. a reminder that just fired."""
    row = QWidget()
    outer = QHBoxLayout(row)
    outer.setContentsMargins(0, 2, 0, 2)
    frame = Surface("note")
    inner = QHBoxLayout(frame)
    inner.setContentsMargins(10, 6, 12, 6)
    inner.setSpacing(7)
    icon = _GlyphDot(glyph)
    inner.addWidget(icon, 0, Qt.AlignmentFlag.AlignTop)
    words = f"{line}  ·  {theme.clock(ts)}"
    label = text(words, "noteText")
    label.setMinimumWidth(min(_natural_width(words, 12), BUBBLE_MAX - 60))
    inner.addWidget(label, 1)
    frame.setMaximumWidth(BUBBLE_MAX)
    outer.addStretch(1)
    outer.addWidget(frame)
    outer.addStretch(1)
    return row


class _GlyphDot(QWidget):
    def __init__(self, glyph: str):
        super().__init__()
        self.glyph = glyph
        self.setFixedSize(14, 16)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        draw_glyph(p, self.glyph, QRectF(0, 1, 13, 13), styles.active().meta, 0.12)
        p.end()


def card(title: str, body: str = "", meta: str = "", kind: str = "", actions: tuple = (),
         faded: bool = False, blob: tuple | None = None) -> Surface:
    """A rounded grey card: title (and a verdict word), optional detail, a footer with actions."""
    frame = Surface("card")
    outer = QHBoxLayout(frame)
    outer.setContentsMargins(14, 12, 12, 12)
    outer.setSpacing(12)
    if blob:
        outer.addWidget(Blob(blob[0], letter=blob[1], size=30), 0, Qt.AlignmentFlag.AlignTop)
    box = QVBoxLayout()
    box.setSpacing(4)
    top = QHBoxLayout()
    top.setSpacing(10)
    top.addWidget(text(title, "cardTitleFaded" if faded else "cardTitle"), 1)
    if kind:
        top.addWidget(pill(kind), 0, Qt.AlignmentFlag.AlignTop)
    inline = bool(actions) and not (body or meta)  # nothing else to say: the button sits beside the title
    if inline:
        for caption, on_click in actions:
            top.addWidget(button(caption, "quiet", on_click))
    box.addLayout(top)
    if body:
        box.addWidget(text(body, "cardBody"))
    if (meta or actions) and not inline:
        foot = QHBoxLayout()
        foot.setSpacing(8)
        foot.addWidget(text(meta, "cardMeta", wrap=False), 1)
        for caption, on_click in actions:
            foot.addWidget(button(caption, "quiet", on_click))
        box.addLayout(foot)
    outer.addLayout(box, 1)
    frame.setProperty("searchText", " ".join((title, body, meta)))
    return frame


class Toggle(QAbstractButton):
    """An on/off switch. Space or a click flips it; the knob's side says which way it is set."""

    changed = Signal(bool)

    def __init__(self, name: str, on: bool = False):
        super().__init__()
        self.setCheckable(True)
        self.setChecked(on)
        self.setAccessibleName(name)
        self.setFixedSize(40, 24)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.toggled.connect(self.changed)

    def sizeHint(self) -> QSize:
        return QSize(40, 24)

    def set_quietly(self, on: bool) -> None:
        if on != self.isChecked():
            self.blockSignals(True)
            self.setChecked(on)
            self.blockSignals(False)
            self.update()

    def keyPressEvent(self, event) -> None:
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.click()
        else:
            super().keyPressEvent(event)

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        styles.active().paint_toggle(p, QRectF(self.rect()), self.isChecked(), self.hasFocus())
        p.end()
