"""Icon widgets and the buttons built from glyphs. Painted in code, no image files; every colour
and shape comes from the active style (hub/styles/) when the widget paints."""
from PySide6.QtCore import QRectF, QSize, Qt
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QAbstractButton, QApplication, QWidget

from deskbuddy.ui.hub import styles
from deskbuddy.ui.hub.glyphs import SHAPES, draw_glyph  # noqa: F401  (re-exported for callers)


def glyph_icon(kind: str, color: str, px: int = 16) -> QIcon:
    screen = QApplication.primaryScreen()
    ratio = screen.devicePixelRatio() if screen else 1.0
    pixmap = QPixmap(int(px * ratio), int(px * ratio))
    pixmap.setDevicePixelRatio(ratio)
    pixmap.fill(Qt.GlobalColor.transparent)
    p = QPainter(pixmap)
    draw_glyph(p, kind, QRectF(0, 0, px, px), color, 0.1)
    p.end()
    return QIcon(pixmap)


def paint_blob(p: QPainter, rect: QRectF, color: str, glyph: str = "", letter: str = "",
               circle: bool = False) -> None:
    """A section or app icon in the active look."""
    styles.active().paint_tile(p, rect, color, glyph, letter, circle)


class Blob(QWidget):
    def __init__(self, color: str, glyph: str = "", letter: str = "", size: int = 22):
        super().__init__()
        self.color, self.glyph, self.letter = color, glyph, letter
        self.setFixedSize(size, size)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        paint_blob(p, QRectF(self.rect()), self.color, self.glyph, self.letter)
        p.end()


class Glyph(QWidget):
    """A plain, non-interactive glyph (`tone` is a Style.tone name), such as the check beside a
    routine ('check_circle' is the look's check button)."""

    def __init__(self, kind: str, tone: str, size: int = 18):
        super().__init__()
        self.kind, self.tone = kind, tone
        self.setFixedSize(size, size)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        style = styles.active()
        if self.kind == "check_circle":
            style.paint_check(p, QRectF(self.rect()))
        else:
            draw_glyph(p, self.kind, QRectF(self.rect()), style.tone(self.tone))
        p.end()


class GlyphButton(QAbstractButton):
    """An icon button. `fill` "" is bare, "soft" a quiet disc, "strong" the main disc (the
    composer's + and mic/send). `tone` is a Style.tone name for the glyph colour."""

    def __init__(self, kind: str, tip: str, size: int = 28, tone: str = "ink",
                 fill: str = "", glyph_scale: float = 0.56):
        super().__init__()
        self.kind, self.tone, self.fill, self.glyph_scale = kind, tone, fill, glyph_scale
        self.setFixedSize(size, size)
        self.setToolTip(tip)
        self.setAccessibleName(tip)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.TabFocus)  # a ring for the keyboard, not after a click

    def set_kind(self, kind: str) -> None:
        if kind != self.kind:
            self.kind = kind
            self.update()

    def sizeHint(self) -> QSize:
        return self.size()

    def keyPressEvent(self, event) -> None:
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.click()
        else:
            super().keyPressEvent(event)

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        style = styles.active()
        rect = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        down = self.isDown()
        style.paint_round_button(p, rect, self.fill, self.underMouse(), down, self.hasFocus())
        side = rect.width() * self.glyph_scale
        glyph_rect = QRectF(0, 0, side, side)
        glyph_rect.moveCenter(rect.center())
        if down and self.fill:
            glyph_rect.translate(0, style.press_shift)
        draw_glyph(p, self.kind, glyph_rect,
                   style.strong_glyph if self.fill == "strong" else style.tone(self.tone), 0.12)
        p.end()

    def enterEvent(self, event) -> None:
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self.update()
        super().leaveEvent(event)
