"""The Look picker: one preview chip per style. Each chip paints a miniature of its own look."""
from PySide6.QtCore import QPointF, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QFontMetrics, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QAbstractButton, QButtonGroup, QHBoxLayout, QWidget

from deskbuddy.ui.hub import styles, theme


class LookChip(QAbstractButton):
    def __init__(self, key: str):
        super().__init__()
        self.key = key
        look = styles.STYLES[key]
        self.setCheckable(True)
        self.setFixedHeight(128)
        self.setMinimumWidth(130)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAccessibleName(f"{look.label}. {look.blurb}")
        self.setToolTip(look.blurb)

    def sizeHint(self) -> QSize:
        return QSize(180, 128)

    def keyPressEvent(self, event) -> None:
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.click()
        else:
            super().keyPressEvent(event)

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        now = styles.active()
        look = styles.variant(self.key, now.dark)   # the miniature shows the mode in force
        on = self.isChecked()
        box = QRectF(self.rect()).adjusted(2, 2, -2, -2)
        shot = QRectF(box.left() + 6, box.top() + 6, box.width() - 12, box.height() - 44)
        clip = QPainterPath()
        clip.addRoundedRect(shot, 9, 9)
        p.save()
        p.setClipPath(clip)
        p.translate(shot.topLeft())
        look.paint_preview(p, QRectF(0, 0, shot.width(), shot.height()))
        p.restore()
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(QColor(255, 255, 255, 46) if now.dark else QColor(0, 0, 0, 50), 1))
        p.drawRoundedRect(shot, 9, 9)
        p.setPen(QPen(QColor(now.accent) if self.hasFocus() else QColor(now.ink) if on else _faint(now.meta),
                      2.5 if on or self.hasFocus() else 1))
        p.drawRoundedRect(box, 13, 13)
        title_font = theme.ui_font(13, bold=True)
        p.setFont(title_font)
        p.setPen(QColor(now.ink))
        p.drawText(QRectF(box.left() + 10, shot.bottom() + 5, box.width() - 40, 18),
                   int(Qt.AlignmentFlag.AlignVCenter), look.label)
        p.setFont(theme.ui_font(11))
        p.setPen(QColor(now.meta))
        small = QFontMetrics(theme.ui_font(11))
        p.drawText(QRectF(box.left() + 10, shot.bottom() + 22, box.width() - 20, 16),
                   int(Qt.AlignmentFlag.AlignVCenter),
                   small.elidedText(look.blurb, Qt.TextElideMode.ElideRight, int(box.width() - 20)))
        if on:  # a tick disc, so the choice is not colour alone
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(now.ink))
            disc = QRectF(box.right() - 28, shot.bottom() + 6, 17, 17)
            p.drawEllipse(disc)
            tick = "#111111" if QColor(now.ink).lightness() > 128 else "#ffffff"   # contrasts with the disc
            p.setPen(QPen(QColor(tick), 2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap,
                          Qt.PenJoinStyle.RoundJoin))
            p.drawPolyline([_pt(disc, 0.27, 0.52), _pt(disc, 0.43, 0.68), _pt(disc, 0.74, 0.32)])
        p.end()

    def enterEvent(self, event) -> None:
        self.update()
        super().enterEvent(event)


def _faint(colour: str) -> QColor:
    tint = QColor(colour)
    tint.setAlpha(110)
    return tint


def _pt(rect: QRectF, fx: float, fy: float):
    return QPointF(rect.left() + rect.width() * fx, rect.top() + rect.height() * fy)


class LookPicker(QWidget):
    chosen = Signal(str)

    def __init__(self):
        super().__init__()
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(12)
        self.group = QButtonGroup(self)
        self.chips: dict[str, LookChip] = {}
        for key in styles.ORDER:
            chip = LookChip(key)
            chip.clicked.connect(lambda _=False, k=key: self.chosen.emit(k))
            self.group.addButton(chip)
            self.chips[key] = chip
            row.addWidget(chip, 1)

    def set_current(self, key: str) -> None:
        chip = self.chips.get(key)
        if chip and not chip.isChecked():
            chip.setChecked(True)
