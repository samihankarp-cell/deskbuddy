"""The Spatial chip in Settings -> Look: a miniature of the look (dusk, three glass panes, orbs,
glass bubbles and a composer capsule). Painted once per chip size into a pixmap."""
from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QPainter

from deskbuddy.ui.hub.styles import spatial_paint as sp
from deskbuddy.ui.hub.styles.base import make_pixmap

ORBS = ("#ff6b2c", "#2d8cff", "#ffb020", "#8b6cff")


def miniature(w: float, h: float, dpr: float, t):
    """`t` is the variant's tokens (spatial_tokens.py)."""
    gain, hair = t.gain, t.hair

    def glass(rect, radius, **kw):
        return sp.glass(q, rect, radius, gain=gain, hair=hair, **kw)

    def white(alpha):
        return sp.white(min(255, int(alpha * gain)))

    pixmap = make_pixmap(w, h, dpr)
    q = QPainter(pixmap)
    q.setRenderHint(QPainter.RenderHint.Antialiasing)
    q.drawPixmap(0, 0, sp.backdrop(int(w), int(h), dpr, t))
    margin, gap, radius = 6.0, 4.0, 8.0
    inner_w, inner_h = w - 2 * margin, h - 2 * margin
    left_w, right_w = inner_w * 0.27, inner_w * 0.21
    centre_w = inner_w - left_w - right_w - 2 * gap
    side = QRectF(margin, margin, left_w, inner_h)
    mid = QRectF(side.right() + gap, margin, centre_w, inner_h)
    right = QRectF(mid.right() + gap, margin, right_w, inner_h)
    for pane in (side, mid, right):
        sp.soft_shadow(q, pane, radius, spread=7, dy=3, strength=0.4 * t.shadow_gain, rgb=t.shade)
    for pane in (side, mid, right):
        q.setPen(Qt.PenStyle.NoPen)
        q.setBrush(QColor(*t.pv_pane))
        q.drawRoundedRect(pane, radius, radius)
        glass(pane, radius, top=34, bottom=12, edge=130)
    for i, colour in enumerate(ORBS):                                   # sidebar rows: orb + line
        y = side.top() + 9 + i * 13
        orb = QRectF(side.left() + 6, y, 9, 9)
        q.drawPixmap(orb.topLeft(), sp.orb(colour, "", "", 9, 9, dpr, t.orb_dark))
        q.setPen(Qt.PenStyle.NoPen)
        q.setBrush(white(75 if i == 0 else 42))
        q.drawRoundedRect(QRectF(orb.right() + 4, y + 2.5, left_w - 28, 4), 2, 2)
    bubble_h = 13.0
    bot = QRectF(mid.left() + 7, mid.top() + 9, centre_w * 0.52, bubble_h)
    glass(bot, bubble_h / 2, top=70, bottom=38, edge=150)
    mine = QRectF(mid.right() - 7 - centre_w * 0.4, mid.top() + 28, centre_w * 0.4, bubble_h)
    glass(mine, bubble_h / 2, top=60, bottom=16, edge=150, tint=sp.rgba(*t.pv_me))
    bot2 = QRectF(mid.left() + 7, mid.top() + 47, centre_w * 0.62, bubble_h)
    glass(bot2, bubble_h / 2, top=70, bottom=38, edge=150)
    bar = QRectF(mid.left() + 7, mid.bottom() - 21, centre_w - 14, 14)
    glass(bar, 7, top=70, bottom=32, edge=150)
    knob = QRectF(bar.right() - 12, bar.top() + 2, 10, 10)
    q.setPen(Qt.PenStyle.NoPen)
    sp.disc(q, knob, "#8aa2ff", "#4057d6", 120)
    cx, cy = right.center().x(), right.top() + inner_h * 0.34                # Kettle floating
    sp.floor_shadow(q, cx, cy + 16, right_w * 0.3, 2.6, 150, t.shade)
    q.setPen(Qt.PenStyle.NoPen)
    q.setBrush(QBrush(sp.vgrad(QRectF(cx - 9, cy - 12, 18, 24), (0.0, "#ffffff"), (1.0, "#cfc8ee"))))
    q.drawRoundedRect(QRectF(cx - 9, cy - 12, 18, 24), 8, 8)
    q.setBrush(QColor("#2a2150"))
    q.drawRoundedRect(QRectF(cx - 6, cy - 6, 12, 7), 3.5, 3.5)
    for i in range(3):
        y = right.top() + inner_h * 0.62 + i * 9
        glass(QRectF(right.left() + 5, y, right_w - 10, 7), 3.5, top=60, bottom=30, edge=110)
    q.end()
    return pixmap
