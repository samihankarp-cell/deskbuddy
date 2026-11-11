"""Vector glyph shapes drawn in code (no image files). Pure drawing: knows nothing about styles."""
import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen


def _poly(points) -> QPainterPath:
    path = QPainterPath(QPointF(*points[0]))
    for x, y in points[1:]:
        path.lineTo(x, y)
    return path


def _lines(*segments) -> QPainterPath:
    path = QPainterPath()
    for (x1, y1), (x2, y2) in segments:
        path.moveTo(x1, y1)
        path.lineTo(x2, y2)
    return path


def _round_rect(x, y, w, h, r) -> QPainterPath:
    path = QPainterPath()
    path.addRoundedRect(QRectF(x, y, w, h), r, r)
    return path


def _ring(cx, cy, r) -> QPainterPath:
    path = QPainterPath()
    path.addEllipse(QPointF(cx, cy), r, r)
    return path


def _bubble() -> QPainterPath:
    return _round_rect(0.1, 0.14, 0.8, 0.6, 0.2).united(_poly([(0.27, 0.7), (0.27, 0.92), (0.5, 0.72)]))


def _sparkle() -> QPainterPath:
    path = QPainterPath(QPointF(0.5, 0.06))
    path.quadTo(0.56, 0.44, 0.94, 0.5)
    path.quadTo(0.56, 0.56, 0.5, 0.94)
    path.quadTo(0.44, 0.56, 0.06, 0.5)
    path.quadTo(0.44, 0.44, 0.5, 0.06)
    return path


def _mic_arc() -> QPainterPath:
    box = QRectF(0.25, 0.26, 0.5, 0.44)
    path = QPainterPath()
    path.arcMoveTo(box, 180)
    path.arcTo(box, 180, 180)  # the lower half: a U
    return path


def _gear_ticks() -> QPainterPath:
    path = QPainterPath()
    for i in range(8):
        a = i * math.pi / 4
        path.moveTo(0.5 + 0.33 * math.cos(a), 0.5 + 0.33 * math.sin(a))
        path.lineTo(0.5 + 0.44 * math.cos(a), 0.5 + 0.44 * math.sin(a))
    return path


# name -> list of (path, "fill" | "stroke"), all drawn in a 0..1 square
SHAPES = {
    "updates": [(_bubble(), "fill")],
    "activity": [(_poly([(0.1, 0.55), (0.3, 0.55), (0.42, 0.22), (0.58, 0.8), (0.7, 0.5), (0.9, 0.5)]),
                  "stroke")],
    "clock": [(_ring(0.5, 0.5, 0.4), "stroke"), (_poly([(0.5, 0.26), (0.5, 0.5), (0.68, 0.6)]), "stroke")],
    "memory": [(_sparkle(), "fill")],
    "plug": [(_round_rect(0.2, 0.34, 0.6, 0.3, 0.1), "fill"),
             (_lines(((0.36, 0.12), (0.36, 0.34)), ((0.64, 0.12), (0.64, 0.34)), ((0.5, 0.64), (0.5, 0.9))),
              "stroke")],
    "gear": [(_ring(0.5, 0.5, 0.2), "stroke"), (_gear_ticks(), "stroke")],
    "plus": [(_lines(((0.5, 0.2), (0.5, 0.8)), ((0.2, 0.5), (0.8, 0.5))), "stroke")],
    "check": [(_poly([(0.22, 0.52), (0.43, 0.72), (0.78, 0.3)]), "stroke")],
    "mic": [(_round_rect(0.38, 0.08, 0.24, 0.46, 0.12), "fill"), (_mic_arc(), "stroke"),
            (_lines(((0.5, 0.7), (0.5, 0.88)), ((0.38, 0.88), (0.62, 0.88))), "stroke")],
    "send": [(_lines(((0.5, 0.84), (0.5, 0.22))), "stroke"),
             (_poly([(0.26, 0.46), (0.5, 0.22), (0.74, 0.46)]), "stroke")],
    "search": [(_ring(0.43, 0.43, 0.27), "stroke"), (_lines(((0.63, 0.63), (0.86, 0.86))), "stroke")],
    "chev_d": [(_poly([(0.22, 0.36), (0.5, 0.64), (0.78, 0.36)]), "stroke")],
    "chev_l": [(_poly([(0.62, 0.22), (0.36, 0.5), (0.62, 0.78)]), "stroke")],
    "chev_r": [(_poly([(0.38, 0.22), (0.64, 0.5), (0.38, 0.78)]), "stroke")],
    "dchev_r": [(_poly([(0.2, 0.26), (0.43, 0.5), (0.2, 0.74)]), "stroke"),
                (_poly([(0.5, 0.26), (0.73, 0.5), (0.5, 0.74)]), "stroke")],
    "dchev_l": [(_poly([(0.8, 0.26), (0.57, 0.5), (0.8, 0.74)]), "stroke"),
                (_poly([(0.5, 0.26), (0.27, 0.5), (0.5, 0.74)]), "stroke")],
}


def _draw_shapes(p: QPainter, kind: str, color: str, pen_width: float) -> None:
    pen = QPen(QColor(color), pen_width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap,
               Qt.PenJoinStyle.RoundJoin)
    for path, mode in SHAPES[kind]:
        if mode == "fill":
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(color))
        else:
            p.setPen(pen)
            p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(path)


def draw_glyph(p: QPainter, kind: str, rect: QRectF, color: str, pen_width: float = 0.11) -> None:
    """Draw a glyph (a key of SHAPES) inside a square rect."""
    p.save()
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.translate(rect.topLeft())
    p.scale(rect.width(), rect.height())
    _draw_shapes(p, kind, color, pen_width)
    p.restore()
