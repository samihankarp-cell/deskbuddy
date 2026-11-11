"""Materials and small painters for the Spatial look: the out-of-focus dusk backdrop, its frosted
copy, soft shadows, glass fills and glowing orbs. All procedural, no image files. Everything
expensive returns a pixmap that the style caches."""
import random

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (QBrush, QColor, QImage, QLinearGradient, QPainter, QPainterPath, QPen,
                           QPixmap, QRadialGradient)

from deskbuddy.ui.hub import glyphs, theme
from deskbuddy.ui.hub.styles.base import make_pixmap
from deskbuddy.ui.hub.styles.skeuo_paint import noise


def rgba(value, alpha: int) -> QColor:
    colour = QColor(value)
    colour.setAlpha(alpha)
    return colour


def white(alpha: int) -> QColor:
    return QColor(255, 255, 255, alpha)


def rrect(rect: QRectF, radius: float) -> QPainterPath:
    path = QPainterPath()
    path.addRoundedRect(rect, radius, radius)
    return path


def vgrad(rect: QRectF, *stops) -> QLinearGradient:
    """A top-to-bottom gradient over rect from (position, colour) stops."""
    grad = QLinearGradient(rect.topLeft(), rect.bottomLeft())
    for at, colour in stops:
        grad.setColorAt(at, QColor(colour))
    return grad


def glow(p: QPainter, cx: float, cy: float, radius: float, rgb: tuple, alpha: int) -> None:
    grad = QRadialGradient(QPointF(cx, cy), radius)
    grad.setColorAt(0.0, QColor(*rgb, alpha))
    grad.setColorAt(0.45, QColor(*rgb, int(alpha * 0.4)))
    grad.setColorAt(1.0, QColor(*rgb, 0))
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QBrush(grad))
    p.drawEllipse(QPointF(cx, cy), radius, radius)


# ---- the environment ------------------------------------------------------------------------
def backdrop(w: int, h: int, dpr: float, t) -> QPixmap:
    """The soft environment behind everything: sky, big glows, out-of-focus lights, a grain.
    `t` is the variant's tokens (spatial_tokens.py): dusk for dark, a bright day for light."""
    pixmap = make_pixmap(w, h, dpr)
    q = QPainter(pixmap)
    q.setRenderHint(QPainter.RenderHint.Antialiasing)
    area = QRectF(0, 0, w, h)
    q.fillRect(area, QBrush(vgrad(area, *t.sky)))
    reach = max(w, h)
    for fx, fy, fr, rgb, alpha in t.glows:
        glow(q, w * fx, h * fy, reach * fr, rgb, alpha)
    rnd = random.Random(11)
    for _ in range(16):                                            # bokeh: lights far out of focus
        x, y = rnd.uniform(0, w), rnd.uniform(0, h)
        r, alpha = rnd.uniform(34, 96) * reach / 1180, int(rnd.randint(16, 34) * t.bokeh_gain)
        colour = QColor(rnd.choice(t.bokeh))
        disc = QRadialGradient(QPointF(x, y), r)
        disc.setColorAt(0.0, rgba(colour, int(alpha * 0.55)))
        disc.setColorAt(0.78, rgba(colour, alpha))
        disc.setColorAt(1.0, rgba(colour, 0))
        q.setPen(Qt.PenStyle.NoPen)
        q.setBrush(QBrush(disc))
        q.drawEllipse(QPointF(x, y), r, r)
    vignette = QRadialGradient(QPointF(w / 2, h * 0.46), reach * 0.78)
    vignette.setColorAt(0.55, QColor(*t.vignette[:3], 0))
    vignette.setColorAt(1.0, QColor(*t.vignette))
    q.fillRect(area, QBrush(vignette))
    q.drawTiledPixmap(area, noise(64, 5, t.grain[0], t.grain[1], dpr))        # grain stops dark banding
    q.end()
    return pixmap


def blurred(pixmap: QPixmap, shrink: int = 16) -> QPixmap:
    """A very soft copy: halve it repeatedly (area averaging), then smooth it back up."""
    dpr = pixmap.devicePixelRatio()
    image = pixmap.toImage()
    image.setDevicePixelRatio(1.0)
    w, h = image.width(), image.height()
    smooth = Qt.TransformationMode.SmoothTransformation
    small = image
    while small.width() > max(4, w // shrink) and small.height() > max(4, h // shrink):
        small = small.scaled(max(2, small.width() // 2), max(2, small.height() // 2),
                             Qt.AspectRatioMode.IgnoreAspectRatio, smooth)
    big = small
    while big.width() < w or big.height() < h:
        big = big.scaled(min(w, big.width() * 2), min(h, big.height() * 2),
                         Qt.AspectRatioMode.IgnoreAspectRatio, smooth)
    result = QPixmap.fromImage(big.convertToFormat(QImage.Format.Format_ARGB32_Premultiplied))
    result.setDevicePixelRatio(dpr)
    return result


def soft_shadow(p: QPainter, rect: QRectF, radius: float, spread: float = 26, dy: float = 12,
                strength: float = 0.5, rgb: tuple = (6, 2, 22)) -> None:
    """A wide, soft, deep shadow: stacked translucent rounded rects that compound to `strength`."""
    layers = 16
    each = 255 * (1 - (1 - strength) ** (1 / layers))
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(*rgb, int(each)))
    for i in range(layers):
        grow = spread * (1 - i / layers) ** 1.5 - spread * 0.35
        box = rect.adjusted(-grow, -grow, grow, grow).translated(0, dy)
        p.drawRoundedRect(box, max(2.0, radius + grow), max(2.0, radius + grow))


# ---- glass --------------------------------------------------------------------------------
def rim(p: QPainter, body: QRectF, radius: float, strength: int = 100) -> None:
    """A 1px edge of light: bright at the top-left, faint through the middle, a glint at the bottom."""
    grad = QLinearGradient(body.topLeft(), body.bottomRight())
    grad.setColorAt(0.0, white(strength))
    grad.setColorAt(0.35, white(int(strength * 0.32)))
    grad.setColorAt(0.7, white(int(strength * 0.2)))
    grad.setColorAt(1.0, white(int(strength * 0.55)))
    p.setPen(QPen(QBrush(grad), 1))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawRoundedRect(body, radius, radius)


def glass(p: QPainter, rect: QRectF, radius: float, top: int = 36, bottom: int = 18,
          edge: int = 95, tint=None, gain: float = 1.0, hair: tuple = (0, 0, 0, 0)) -> QRectF:
    """A translucent capsule or card: white (or `tint`) wash, a lit rim and a short top highlight.
    `gain` strengthens the white wash (a light variant needs more of it) and `hair` is a faint
    1px outline under the rim, so white glass still has an edge on white."""
    body = rect.adjusted(0.5, 0.5, -0.5, -0.5)
    p.setPen(Qt.PenStyle.NoPen)
    if tint is not None:
        p.setBrush(QColor(tint))
        p.drawRoundedRect(body, radius, radius)
    p.setBrush(QBrush(vgrad(body, (0.0, white(min(255, int(top * gain)))),
                            (1.0, white(min(255, int(bottom * gain)))))))
    p.drawRoundedRect(body, radius, radius)
    if hair[3]:
        p.setPen(QPen(QColor(*hair), 1))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(body, radius, radius)
    rim(p, body, radius, min(255, edge))
    reach = min(radius * 0.9, body.width() / 3)
    p.setPen(QPen(white(int(edge * 0.55)), 1))
    p.drawLine(QPointF(body.left() + reach, body.top() + 1), QPointF(body.right() - reach, body.top() + 1))
    return body


def disc(p: QPainter, rect: QRectF, top: str, bottom: str, rim_alpha: int = 150) -> None:
    """A glossy glass disc between two colours with a lit rim and a specular cap."""
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QBrush(vgrad(rect, (0.0, top), (1.0, bottom))))
    p.drawEllipse(rect)
    cap = QRectF(rect.left() + rect.width() * 0.16, rect.top() + rect.height() * 0.06,
                 rect.width() * 0.68, rect.height() * 0.42)
    p.setBrush(QBrush(vgrad(cap, (0.0, white(120)), (1.0, white(6)))))
    p.drawEllipse(cap)
    rim(p, rect, rect.width() / 2, rim_alpha)


# ---- icons ----------------------------------------------------------------------------------
def orb(color: str, glyph: str, letter: str, w: float, h: float, dpr: float,
        deep: int = 205) -> QPixmap:
    """A round glass orb: the identity colour glows from inside, a specular cap sits on top."""
    pixmap = make_pixmap(w, h, dpr)
    q = QPainter(pixmap)
    q.setRenderHint(QPainter.RenderHint.Antialiasing)
    side = min(w, h)
    body = QRectF((w - side) / 2 + 0.5, (h - side) / 2 + 0.5, side - 1, side - 1)
    base = QColor(color)
    if base.lightness() < 60:                                    # a dark identity colour: smoky glass
        base = QColor("#8d8ab4")
    core = QRadialGradient(QPointF(body.center().x(), body.center().y() + side * 0.12), side * 0.62)
    core.setColorAt(0.0, base.lighter(128))
    core.setColorAt(0.55, base)
    core.setColorAt(1.0, base.darker(deep))
    q.setPen(Qt.PenStyle.NoPen)
    q.setBrush(QBrush(core))
    q.drawEllipse(body)
    belly = QRadialGradient(QPointF(body.center().x(), body.bottom() - side * 0.05), side * 0.42)
    belly.setColorAt(0.0, rgba(base.lighter(150), 120))
    belly.setColorAt(1.0, rgba(base.lighter(150), 0))
    q.setBrush(QBrush(belly))
    q.drawEllipse(body)
    cap = QRectF(body.left() + side * 0.17, body.top() + side * 0.05, side * 0.66, side * 0.40)
    q.setBrush(QBrush(vgrad(cap, (0.0, white(175)), (1.0, white(8)))))
    q.drawEllipse(cap)
    rim(q, body, side / 2, 190)
    face = body.adjusted(side * 0.24, side * 0.24, -side * 0.24, -side * 0.22)
    if glyph:
        glyphs.draw_glyph(q, glyph, face.translated(0, 0.6), rgba(base.darker(260), 110).name(QColor.NameFormat.HexArgb), 0.12)
        glyphs.draw_glyph(q, glyph, face, "#ffffff", 0.12)
    elif letter:
        q.setFont(theme.ui_font(max(9, int(side * 0.42)), bold=True))
        q.setPen(QColor(0, 0, 0, 70))
        q.drawText(body.translated(0, 0.8), Qt.AlignmentFlag.AlignCenter, letter)
        q.setPen(QColor("#ffffff"))
        q.drawText(body, Qt.AlignmentFlag.AlignCenter, letter)
    q.end()
    return pixmap


def floor_shadow(p: QPainter, cx: float, cy: float, rx: float, ry: float, alpha: int = 120,
                 rgb: tuple = (6, 2, 22)) -> None:
    """A soft elliptical shadow on the 'floor' under something that floats."""
    p.save()
    p.translate(cx, cy)
    p.scale(1.0, ry / rx)
    grad = QRadialGradient(QPointF(0, 0), rx)
    grad.setColorAt(0.0, QColor(*rgb, alpha))
    grad.setColorAt(0.6, QColor(*rgb, int(alpha * 0.35)))
    grad.setColorAt(1.0, QColor(*rgb, 0))
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QBrush(grad))
    p.drawEllipse(QPointF(0, 0), rx, rx)
    p.restore()
