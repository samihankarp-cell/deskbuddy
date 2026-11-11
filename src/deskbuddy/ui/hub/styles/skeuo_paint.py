"""Procedural materials for the Skeuomorphic look: leather, linen, felt, brushed metal, and the
small painters (drop shadow, inner shadow, gloss) the controls are made from. No image files.
Everything expensive returns a QPixmap that the style caches."""
import random

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (QBrush, QColor, QImage, QLinearGradient, QPainter, QPainterPath, QPen,
                           QPixmap, QRadialGradient)

from deskbuddy.ui.hub.styles.base import make_pixmap


def rgba(value: str, alpha: float = 1.0) -> QColor:
    colour = QColor(value)
    colour.setAlphaF(alpha)
    return colour


def vgrad(rect: QRectF, top: str, bottom: str, mid: tuple | None = None) -> QLinearGradient:
    """A top-to-bottom gradient over rect; mid is an optional (stop, colour) pair."""
    grad = QLinearGradient(rect.topLeft(), rect.bottomLeft())
    grad.setColorAt(0, QColor(top))
    if mid:
        grad.setColorAt(mid[0], QColor(mid[1]))
    grad.setColorAt(1, QColor(bottom))
    return grad


# ---- textures (built once per pixel ratio, then tiled) -------------------------------------
def noise(size: int, seed: int, colour: str, max_alpha: int, dpr: float) -> QPixmap:
    """Fine random speckle: `size` logical px square, per-pixel alpha 0..max_alpha."""
    side = max(1, int(size * dpr))
    count = side * side
    alpha = random.Random(seed).randbytes(count).translate(
        bytes(int(i * max_alpha / 255) for i in range(256)))
    base = QColor(colour)
    data = bytearray(count * 4)
    data[0::4] = bytes([base.blue()]) * count
    data[1::4] = bytes([base.green()]) * count
    data[2::4] = bytes([base.red()]) * count
    data[3::4] = alpha
    pixmap = QPixmap.fromImage(QImage(bytes(data), side, side, side * 4, QImage.Format.Format_ARGB32))
    pixmap.setDevicePixelRatio(dpr)
    return pixmap


def leather_tile(base: str, dpr: float) -> QPixmap:
    """Pebbled leather: base colour, soft dimples, light and dark grain."""
    size = 128
    pixmap = make_pixmap(size, size, dpr)
    p = QPainter(pixmap)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.fillRect(QRectF(0, 0, size, size), QColor(base))
    rnd = random.Random(7)
    for _ in range(420):
        x, y, r = rnd.uniform(0, size), rnd.uniform(0, size), rnd.uniform(1.4, 3.2)
        for dx in (0, -size):
            for dy in (0, -size):
                spot = QRadialGradient(QPointF(x + dx - r * 0.3, y + dy - r * 0.3), r * 1.4)
                spot.setColorAt(0, QColor(255, 225, 180, 20))
                spot.setColorAt(0.55, QColor(0, 0, 0, 0))
                spot.setColorAt(1, QColor(0, 0, 0, 34))
                p.setBrush(QBrush(spot))
                p.setPen(Qt.PenStyle.NoPen)
                p.drawEllipse(QPointF(x + dx, y + dy), r, r)
    p.drawPixmap(0, 0, noise(size, 3, "#000000", 34, dpr))
    p.drawPixmap(0, 0, noise(size, 4, "#ffe2b8", 16, dpr))
    p.end()
    return pixmap


def linen_tile(base: str, dpr: float, weave: float = 1.0) -> QPixmap:
    """Woven linen: base colour, a fine over-under weave and speckle. `weave` scales how visible
    the threads are (1.0 = the light look; a dark fabric takes less)."""
    size = 96
    pixmap = make_pixmap(size, size, dpr)
    p = QPainter(pixmap)
    p.fillRect(QRectF(0, 0, size, size), QColor(base))
    step = 4

    def a(value: int) -> int:
        return int(value * weave)

    for i in range(0, size, step):
        shade = 14 if (i // step) % 2 else 6
        p.fillRect(QRectF(i, 0, 1, size), QColor(80, 60, 30, a(shade + 1)))     # warp threads
        p.fillRect(QRectF(i + 1, 0, 1, size), QColor(255, 255, 255, a(26)))
        p.fillRect(QRectF(0, i + 2, size, 1), QColor(80, 60, 30, a(shade - 1)))  # weft threads
        p.fillRect(QRectF(0, i + 3, size, 1), QColor(255, 255, 255, a(18)))
    p.drawPixmap(0, 0, noise(size, 11, "#5a4020", a(22), dpr))
    p.drawPixmap(0, 0, noise(size, 12, "#ffffff", a(26), dpr))
    p.end()
    return pixmap


def felt_tile(base: str, dpr: float) -> QPixmap:
    size = 64
    pixmap = make_pixmap(size, size, dpr)
    p = QPainter(pixmap)
    p.fillRect(QRectF(0, 0, size, size), QColor(base))
    p.drawPixmap(0, 0, noise(size, 21, "#000000", 70, dpr))
    p.drawPixmap(0, 0, noise(size, 22, "#d8ffe8", 46, dpr))
    p.end()
    return pixmap


def brushed_tile(dpr: float, gain: float = 1.0) -> QPixmap:
    """Horizontal brushed-metal streaks, drawn over a gradient strip. `gain` scales their strength."""
    width, height = 256, 56
    pixmap = make_pixmap(width, height, dpr)
    p = QPainter(pixmap)
    rnd = random.Random(5)
    for y in range(height):
        for _ in range(3):
            x = rnd.uniform(0, width)
            length = rnd.uniform(30, 150)
            light = rnd.random() < 0.5
            colour = (QColor(255, 255, 255, int(rnd.randint(14, 46) * gain)) if light
                      else QColor(70, 55, 30, int(rnd.randint(6, 18) * gain)))
            p.setPen(QPen(colour, 1))
            for dx in (0, -width):
                p.drawLine(QPointF(x + dx, y + 0.5), QPointF(x + dx + length, y + 0.5))
    p.end()
    return pixmap


def tiled(w: float, h: float, tile: QPixmap, dpr: float) -> QPixmap:
    """A w x h pixmap filled with a tile."""
    pixmap = make_pixmap(w, h, dpr)
    p = QPainter(pixmap)
    p.drawTiledPixmap(QRectF(0, 0, w, h), tile)
    p.end()
    return pixmap


# ---- small painters ------------------------------------------------------------------------
def rrect(rect: QRectF, radius: float) -> QPainterPath:
    path = QPainterPath()
    path.addRoundedRect(rect, radius, radius)
    return path


def drop_shadow(p: QPainter, rect: QRectF, radius: float, depth: int = 3, alpha: int = 34,
                rgb: tuple = (60, 36, 12)) -> None:
    """A soft shadow under a raised card, drawn as stacked translucent rounded rects."""
    p.setPen(Qt.PenStyle.NoPen)
    for i in range(depth, 0, -1):
        p.setBrush(QColor(*rgb, int(alpha * (1.0 - (i - 1) / depth) * 0.55)))
        p.drawRoundedRect(rect.adjusted(-i * 0.4, 0, i * 0.4, 0).translated(0, i * 0.9),
                          radius + i * 0.4, radius + i * 0.4)


def inner_shadow(p: QPainter, rect: QRectF, radius: float, depth: float = 7, alpha: int = 70,
                 side: float = 0.45) -> None:
    """The shadow a recessed well casts on its own floor: darkest at the top, softer at the sides."""
    p.save()
    p.setClipPath(rrect(rect, radius))
    p.setPen(Qt.PenStyle.NoPen)
    top = QLinearGradient(rect.topLeft(), QPointF(rect.left(), rect.top() + depth))
    top.setColorAt(0, QColor(30, 14, 0, alpha))
    top.setColorAt(1, QColor(30, 14, 0, 0))
    p.fillRect(QRectF(rect.left(), rect.top(), rect.width(), depth), QBrush(top))
    for x0, x1 in ((rect.left(), rect.left() + depth * 0.7), (rect.right(), rect.right() - depth * 0.7)):
        grad = QLinearGradient(QPointF(x0, 0), QPointF(x1, 0))
        grad.setColorAt(0, QColor(30, 14, 0, int(alpha * side)))
        grad.setColorAt(1, QColor(30, 14, 0, 0))
        p.fillRect(QRectF(min(x0, x1), rect.top(), abs(x1 - x0), rect.height()), QBrush(grad))
    p.restore()


def gloss(p: QPainter, rect: QRectF, radius: float, strength: int = 90, fraction: float = 0.52) -> None:
    """A sheen over the top part of a glossy object (clipped to its rounded outline)."""
    p.save()
    p.setClipPath(rrect(rect, radius))
    sheen = QRectF(rect.left(), rect.top(), rect.width(), rect.height() * fraction)
    grad = QLinearGradient(sheen.topLeft(), sheen.bottomLeft())
    grad.setColorAt(0, QColor(255, 255, 255, strength))
    grad.setColorAt(1, QColor(255, 255, 255, int(strength * 0.1)))
    p.fillRect(sheen, QBrush(grad))
    p.fillRect(QRectF(rect.left(), rect.top(), rect.width(), 1), QColor(255, 255, 255, min(255, strength + 60)))
    p.restore()


def stitches(p: QPainter, x: float, top: float, bottom: float, thread: str = "#e8cf98") -> None:
    """A vertical seam of stitches with a thin shadow under the thread."""
    dash = QPen(QColor(15, 6, 0, 170), 2.0)
    dash.setDashPattern([2.2, 2.2])
    dash.setCapStyle(Qt.PenCapStyle.FlatCap)
    p.setPen(dash)
    p.drawLine(QPointF(x + 0.9, top + 0.9), QPointF(x + 0.9, bottom))
    seam = QPen(QColor(thread), 1.6)
    seam.setDashPattern([2.2, 2.2])
    seam.setCapStyle(Qt.PenCapStyle.FlatCap)
    p.setPen(seam)
    p.drawLine(QPointF(x, top), QPointF(x, bottom))


def sphere(p: QPainter, rect: QRectF, colour: str, rim: str) -> None:
    """A glossy button/lamp: lit from above-left, with a rim and a highlight."""
    base = QColor(colour)
    grad = QRadialGradient(QPointF(rect.center().x() - rect.width() * 0.12, rect.top() + rect.height() * 0.3),
                           rect.width() * 0.75)
    grad.setColorAt(0, base.lighter(165))
    grad.setColorAt(0.55, base)
    grad.setColorAt(1, base.darker(135))
    p.setPen(QPen(QColor(rim), 1))
    p.setBrush(QBrush(grad))
    p.drawEllipse(rect)
    p.setPen(Qt.PenStyle.NoPen)
    shine = QRectF(rect.left() + rect.width() * 0.2, rect.top() + rect.height() * 0.08,
                   rect.width() * 0.6, rect.height() * 0.38)
    grad2 = QLinearGradient(shine.topLeft(), shine.bottomLeft())
    grad2.setColorAt(0, QColor(255, 255, 255, 150))
    grad2.setColorAt(1, QColor(255, 255, 255, 10))
    p.setBrush(QBrush(grad2))
    p.drawEllipse(shine)
