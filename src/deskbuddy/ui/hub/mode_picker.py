"""The Mode control under the Look chips: a segmented "Light | Dark | System". The look paints the
trough and the chosen segment (Style.paint_segment_track / paint_segment); the words are ours."""
from PySide6.QtCore import QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QAbstractButton, QButtonGroup, QHBoxLayout, QWidget

from deskbuddy.ui.hub import styles, theme
from deskbuddy.ui.hub.styles import modes

HEIGHT = 34
SEGMENT_W = 84


class _Segment(QAbstractButton):
    def __init__(self, mode: str):
        super().__init__()
        self.mode = mode
        self.setText(modes.LABELS[mode])
        self.setCheckable(True)
        self.setFixedHeight(HEIGHT)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAccessibleName(f"{modes.LABELS[mode]} mode")

    def sizeHint(self) -> QSize:
        return QSize(SEGMENT_W, HEIGHT)

    def keyPressEvent(self, event) -> None:
        step = {Qt.Key.Key_Left: -1, Qt.Key.Key_Right: 1}.get(event.key())
        if step and self.parent():
            self.parent().step(self, step)
        elif event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.click()
        else:
            super().keyPressEvent(event)

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        look = styles.active()
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect())
        look.paint_segment(p, rect, self.isChecked(), self.underMouse(), self.hasFocus())
        p.setFont(theme.ui_font(12, bold=True))
        p.setPen(QColor(look.segment_ink(self.isChecked())))
        p.drawText(rect, int(Qt.AlignmentFlag.AlignCenter), self.text())
        p.end()

    def enterEvent(self, event) -> None:
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self.update()
        super().leaveEvent(event)


class ModePicker(QWidget):
    """Light | Dark | System. `chosen(mode)` fires when the user picks one (not on set_current)."""

    chosen = Signal(str)

    def __init__(self):
        super().__init__()
        self.setFixedSize(SEGMENT_W * len(modes.MODES), HEIGHT)
        self.setAccessibleName("Mode")
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(0)
        self.group = QButtonGroup(self)
        self.segments: dict[str, _Segment] = {}
        for mode in modes.MODES:
            segment = _Segment(mode)
            segment.clicked.connect(lambda _=False, m=mode: self.chosen.emit(m))
            self.group.addButton(segment)
            self.segments[mode] = segment
            row.addWidget(segment)

    def set_current(self, mode: str) -> None:
        segment = self.segments.get(mode)
        if segment and not segment.isChecked():
            segment.setChecked(True)

    def step(self, segment: _Segment, delta: int) -> None:
        """Left / Right move to the neighbouring mode and choose it."""
        order = list(modes.MODES)
        target = self.segments[order[(order.index(segment.mode) + delta) % len(order)]]
        target.setFocus()
        target.click()

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        styles.active().paint_segment_track(p, QRectF(self.rect()))
        p.end()
