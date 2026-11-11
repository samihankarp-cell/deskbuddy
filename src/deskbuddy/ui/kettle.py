"""Kettle: the robot itself, drawn with vector shapes. Original artwork."""
import math

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QWidget

from deskbuddy.state import STATE_COLORS, BuddyState

ART_W, ART_H = 200.0, 210.0  # the drawing is designed on this canvas, then scaled
SHELL_LINE = QColor("#d9e0e8")
FACE = QColor("#18202b")


class KettleWidget(QWidget):
    def __init__(self, parent=None, width: int = 150):
        super().__init__(parent)
        self.setFixedSize(width, int(width * ART_H / ART_W))
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._state = BuddyState.IDLE
        self._phase = 0.0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(33)

    @property
    def state(self) -> BuddyState:
        return self._state

    def set_state(self, state: BuddyState) -> None:
        self._state = state
        self.update()

    def _tick(self) -> None:
        self._phase += 0.07
        self.update()

    # ---- drawing -------------------------------------------------------
    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.scale(self.width() / ART_W, self.height() / ART_H)
        accent = QColor(STATE_COLORS[self._state])
        bob = math.sin(self._phase)  # -1..1
        lift = 5 + 5 * bob            # 0..10 units above rest

        # hover glow on the "floor": shrinks as the robot rises
        glow = QColor(accent)
        glow.setAlphaF(0.55 - 0.02 * lift)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(glow)
        p.drawEllipse(QPointF(100, 194), 30 - lift * 0.6, 6 - lift * 0.15)

        p.translate(0, -lift)
        self._draw_antenna(p, accent)
        self._draw_body(p)
        self._draw_eyes(p, accent.lighter(120))
        self._draw_hands(p)
        p.end()

    def _draw_antenna(self, p: QPainter, accent: QColor) -> None:
        p.setPen(QPen(QColor("#d3dae3"), 5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawLine(QPointF(100, 52), QPointF(100, 30))
        ball = QColor(accent)
        if self._state in (BuddyState.WORKING, BuddyState.LISTENING):
            ball.setAlphaF(0.55 + 0.45 * abs(math.sin(self._phase * 2.5)))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(ball)
        p.drawEllipse(QPointF(100, 24), 8, 8)

    def _draw_body(self, p: QPainter) -> None:
        body = QPainterPath()
        body.moveTo(62, 58)
        body.quadTo(100, 40, 138, 58)
        body.lineTo(152, 140)
        body.quadTo(100, 172, 48, 140)
        body.closeSubpath()
        shade = QLinearGradient(0, 45, 0, 170)
        shade.setColorAt(0, QColor("#ffffff"))
        shade.setColorAt(1, QColor("#e8ecf2"))
        p.setPen(QPen(SHELL_LINE, 2))
        p.setBrush(shade)
        p.drawPath(body)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(FACE)
        p.drawEllipse(QPointF(100, 100), 31, 31)

    def _draw_eyes(self, p: QPainter, color: QColor) -> None:
        pen = QPen(color, 5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        s = self._state
        for cx in (89.0, 111.0):
            if s in (BuddyState.IDLE, BuddyState.WORKING, BuddyState.DONE):
                rise = 14 if s is BuddyState.DONE else 10
                arc = QPainterPath()
                arc.moveTo(cx - 7, 102)
                arc.quadTo(cx, 102 - rise, cx + 7, 102)
                p.setPen(pen)
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.drawPath(arc)
            elif s is BuddyState.COULDNT:
                p.setPen(pen)
                p.drawLine(QPointF(cx - 6, 100), QPointF(cx + 6, 100))
            else:
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(color)
                if s is BuddyState.THINKING:
                    p.drawEllipse(QPointF(cx + 4 * math.sin(self._phase * 2), 99), 3.5, 3.5)
                elif s is BuddyState.ASKING:
                    r = 4 if cx < 100 else 6
                    p.drawEllipse(QPointF(cx, 99), r, r)
                else:  # LISTENING
                    p.drawEllipse(QPointF(cx, 99), 5.5, 5.5)

    def _draw_hands(self, p: QPainter) -> None:
        sway = 3 * math.sin(self._phase + 1.2)
        busy = 4 * math.sin(self._phase * 4) if self._state is BuddyState.WORKING else 0
        p.setPen(QPen(SHELL_LINE, 2))
        p.setBrush(QColor("#ffffff"))
        p.drawEllipse(QRectF(13, 113 + sway + busy, 22, 22))
        p.drawEllipse(QRectF(165, 113 - sway - busy, 22, 22))
