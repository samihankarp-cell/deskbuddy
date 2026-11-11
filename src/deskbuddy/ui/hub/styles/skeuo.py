"""Skeuomorphic: warm, tactile, real materials. A walnut-leather sidebar with a stitched seam,
a linen page under a brushed-metal header, paper cards, leather-capsule orders, glossy app tiles,
a felt display case for Kettle and a notepad for routines. All painted in code and cached.
The dark variant is the same room at night (see skeuo_tokens.py); only the numbers change."""
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QPainter, QPen

from deskbuddy.ui.hub import glyphs, theme
from deskbuddy.ui.hub.styles import skeuo_paint as sk
from deskbuddy.ui.hub.styles.base import make_pixmap, ratio
from deskbuddy.ui.hub.styles.classic import ClassicStyle
from deskbuddy.ui.hub.styles.skeuo_qss import controls
from deskbuddy.ui.hub.styles.skeuo_surfaces import SurfacePainter
from deskbuddy.ui.hub.styles.skeuo_tokens import DARK, LIGHT


class SkeuoStyle(SurfacePainter, ClassicStyle):
    key = "skeuo"
    label = "Skeuomorphic"
    blurb = "Leather, linen and brass."
    press_shift = 1

    def __init__(self, dark: bool = False):
        super().__init__(dark)
        self._tiles: dict[tuple, object] = {}

    def tokens(self) -> dict:
        return DARK if self.dark else LIGHT

    # ---- QSS ---------------------------------------------------------------------------------
    def stylesheet(self) -> str:
        return self.label_qss() + controls(self)

    def surface_margins(self, role: str):
        return (12, 24, 10, 12) if role == "notepad" else None

    def text_shadow(self, name: str):
        return self.t.text_shadows.get(name)

    # ---- icons -------------------------------------------------------------------------------
    def paint_tile(self, p, rect, color, glyph="", letter="", circle=False) -> None:
        dpr = ratio(p)
        w, h = round(rect.width(), 1), round(rect.height(), 1)
        key = (color, glyph, letter, circle, w, h, dpr)
        pixmap = self._tiles.get(key)
        if pixmap is None:
            if len(self._tiles) > 64:
                self._tiles.clear()
            pixmap = self._tiles[key] = self._make_tile(color, glyph, letter, circle, w, h, dpr)
        p.drawPixmap(rect.topLeft(), pixmap)

    def _make_tile(self, color, glyph, letter, circle, w, h, dpr):
        pixmap = make_pixmap(w, h, dpr)
        p = QPainter(pixmap)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        base = QColor(color)
        side = min(w - 1, h - 3) if circle else None
        body = (QRectF((w - side) / 2, 0.5, side, side) if circle
                else QRectF(0.5, 0.5, w - 1, h - 3))
        radius = body.width() / 2 if circle else body.width() * 0.28
        for dy, alpha in ((2.0, 55), (1.0, 70)):                       # drop shadow
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(20, 8, 0, alpha))
            p.drawRoundedRect(body.translated(0, dy), radius, radius)
        p.setPen(QPen(base.darker(185), 1))
        p.setBrush(QBrush(sk.vgrad(body, base.lighter(132).name(), base.darker(122).name(),
                                   (0.5, base.name()))))
        p.drawRoundedRect(body, radius, radius)
        inside = body.adjusted(1, 1, -1, -1)
        sk.gloss(p, inside, radius - 1, 105, 0.5)
        p.setPen(QPen(QColor(255, 255, 255, 70), 1))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(inside, radius - 1, radius - 1)
        face = body.adjusted(body.width() * 0.22, body.height() * 0.2, -body.width() * 0.22, -body.height() * 0.24)
        if glyph:
            glyphs.draw_glyph(p, glyph, face.translated(0, 1), "#66000000", 0.12)   # engraved shadow
            glyphs.draw_glyph(p, glyph, face, "#ffffff", 0.12)
        elif letter:
            p.setFont(theme.ui_font(max(9, int(body.height() * 0.44)), bold=True))
            p.setPen(QColor(0, 0, 0, 100))
            p.drawText(body.translated(0, 1), Qt.AlignmentFlag.AlignCenter, letter)
            p.setPen(QColor("#ffffff"))
            p.drawText(body, Qt.AlignmentFlag.AlignCenter, letter)
        p.end()
        return pixmap

    def paint_check(self, p, rect) -> None:
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        disc = rect.adjusted(1, 0.5, -1, -2)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(20, 8, 0, 70))
        p.drawEllipse(disc.translated(0, 1.3))
        sk.sphere(p, disc, self.green, "#1b5c26")
        tick = disc.adjusted(disc.width() * 0.2, disc.height() * 0.2, -disc.width() * 0.2, -disc.height() * 0.2)
        glyphs.draw_glyph(p, "check", tick.translated(0, 0.8), "#59000000", 0.17)
        glyphs.draw_glyph(p, "check", tick, "#ffffff", 0.17)
        p.restore()

    def paint_round_button(self, p, rect, fill, hot, down, focused) -> None:
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        t = self.t
        if fill or hot or down:
            disc = rect.adjusted(0.5, 0.5, -0.5, -1.5).translated(0, 1 if down else 0)
            if not down:
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(QColor(20, 8, 0, 70))
                p.drawEllipse(disc.translated(0, 1.4))
            if fill == "strong":
                top, bottom, rim = t.strong_hot if hot else t.strong
            else:
                top, bottom, rim = t.soft_hot if hot else t.soft
            if down:
                top, bottom = bottom, top
            p.setPen(QPen(QColor(rim), 1))
            p.setBrush(QBrush(sk.vgrad(disc, top, bottom)))
            p.drawEllipse(disc)
            if not down:
                sk.gloss(p, disc.adjusted(1, 1, -1, -1), disc.width() / 2,
                         t.strong_gloss if fill == "strong" else t.soft_gloss, 0.5)
        if focused:
            p.setPen(QPen(QColor(self.accent), 2))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(rect)

    def paint_row(self, p, box, checked, hot, focused) -> None:
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        if checked:                                                     # a recessed groove
            groove = box.adjusted(0, 1, 0, -1)
            p.setPen(QPen(QColor(10, 3, 0, 150), 1))
            p.setBrush(QColor(15, 6, 0, 88))
            p.drawRoundedRect(groove, 11, 11)
            sk.inner_shadow(p, groove, 11, depth=11, alpha=170, side=0.5)
            p.setPen(QPen(QColor(255, 226, 180, 52), 1))
            p.drawLine(QPointF(groove.left() + 8, groove.bottom() + 0.5),
                       QPointF(groove.right() - 8, groove.bottom() + 0.5))
        elif hot:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(255, 226, 180, 26))
            p.drawRoundedRect(box.adjusted(0, 1, 0, -1), 11, 11)
        if focused:
            p.setPen(QPen(QColor("#e8cf98"), 2))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(box.adjusted(1, 1, -1, -1), 10, 10)

    def paint_unread(self, p, rect) -> None:
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        sk.sphere(p, rect, self.accent, "#0f3366")

    def paint_toggle(self, p, rect, on, focused) -> None:
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        t = self.t
        track = rect.adjusted(1, 1, -1, -3)
        r = track.height() / 2
        p.setPen(QPen(QColor(*t.tog_hi), 1))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(track.translated(0, 1.2), r, r)
        p.setPen(QPen(QColor("#1d5a26" if on else t.tog_off[2]), 1))
        p.setBrush(QBrush(sk.vgrad(track, "#2f903d", "#5ccb68") if on else sk.vgrad(track, *t.tog_off[:2])))
        p.drawRoundedRect(track, r, r)
        sk.inner_shadow(p, track.adjusted(1, 1, -1, -1), r, depth=9, alpha=120, side=0.6)
        d = track.height() - 4
        x = track.right() - d - 2 if on else track.left() + 2
        knob = QRectF(x, track.top() + 2, d, d)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(20, 8, 0, 90))
        p.drawEllipse(knob.translated(0, 1.4))
        p.setPen(QPen(QColor("#6c675c"), 1))
        p.setBrush(QBrush(sk.vgrad(knob, "#ffffff", "#a8a398", (0.5, "#e4e1d9"))))
        p.drawEllipse(knob)
        sk.gloss(p, knob.adjusted(1, 1, -1, -1), d / 2, 120, 0.45)
        if focused:
            p.setPen(QPen(QColor(self.accent), 2))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(track.adjusted(-1.5, -1.5, 1.5, 1.5), r + 1.5, r + 1.5)

    def paint_pill(self, p, rect, group) -> str:
        """A rubber stamp: a double inked border, a faint tint, the word pressed in."""
        ink, _tint = self.pill_colors(group)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        box = rect.adjusted(0.8, 0.8, -0.8, -1.8)
        p.setPen(QPen(QColor(*self.t.stamp_hi), 1))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(box.translated(0, 1), 6, 6)
        p.setPen(QPen(sk.rgba(ink, 0.85), 1.3))
        p.setBrush(sk.rgba(ink, 0.10))
        p.drawRoundedRect(box, 6, 6)
        p.setPen(QPen(sk.rgba(ink, 0.35), 0.8))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(box.adjusted(2.2, 2.2, -2.2, -2.2), 3.5, 3.5)
        return ink

    # ---- the Mode control: a recessed trough, a raised capsule ---------------------------------
    def paint_segment_track(self, p, rect) -> None:
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        top, bottom, edge = self.t.seg_track
        body = rect.adjusted(0.5, 0.5, -0.5, -1.5)
        r = body.height() / 2
        p.setPen(QPen(QColor(255, 255, 255, 60 if not self.dark else 24), 1))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(body.translated(0, 1), r, r)
        p.setPen(QPen(QColor(edge), 1))
        p.setBrush(QBrush(sk.vgrad(body, top, bottom)))
        p.drawRoundedRect(body, r, r)
        sk.inner_shadow(p, body.adjusted(1, 1, -1, -1), r, depth=8, alpha=80)

    def paint_segment(self, p, rect, on, hot, focused) -> None:
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        body = rect.adjusted(3, 3, -3, -4)
        r = body.height() / 2
        if on:
            top, bottom, rim = self.t.seg_on
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(20, 8, 0, 70))
            p.drawRoundedRect(body.translated(0, 1.3), r, r)
            p.setPen(QPen(QColor(rim), 1))
            p.setBrush(QBrush(sk.vgrad(body, top, bottom)))
            p.drawRoundedRect(body, r, r)
            sk.gloss(p, body.adjusted(1, 1, -1, -1), r - 1, 90, 0.5)
        elif hot:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(255, 226, 180, 22))
            p.drawRoundedRect(body, r, r)
        if focused:
            p.setPen(QPen(QColor(self.accent), 2))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(rect.adjusted(1, 1, -1, -2), rect.height() / 2 - 1, rect.height() / 2 - 1)

    # ---- the Look chip ---------------------------------------------------------------------------
    def paint_preview(self, p, rect) -> None:
        t = self.t
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(rect, QColor(t.pv_linen))
        side = QRectF(rect.left(), rect.top(), rect.width() * 0.28, rect.height())
        p.fillRect(side, QBrush(sk.vgrad(side, *t.pv_side)))
        sk.stitches(p, side.right() - 4, rect.top() + 4, rect.bottom() - 4)
        for i, colour in enumerate(("#ff6b2c", "#2d8cff", "#ffb020", "#8b6cff")):
            y = rect.top() + 11 + i * 12
            p.setPen(QPen(QColor(colour).darker(170), 0.8))
            p.setBrush(QBrush(sk.vgrad(QRectF(side.left() + 7, y, 8, 8), QColor(colour).lighter(130).name(),
                                       QColor(colour).darker(110).name())))
            p.drawRoundedRect(QRectF(side.left() + 7, y, 8, 8), 2.5, 2.5)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(*t.pv_rows))
            p.drawRoundedRect(QRectF(side.left() + 19, y + 2, side.width() - 32, 4), 2, 2)
        left = side.right() + 10
        top, bottom, edge = t.pv_paper
        for box in (QRectF(left, rect.top() + 12, rect.width() * 0.38, 15),
                    QRectF(left, rect.top() + 56, rect.width() * 0.46, 15)):
            p.setPen(QPen(QColor(edge), 1))
            p.setBrush(QBrush(sk.vgrad(box, top, bottom)))
            p.drawRoundedRect(box, 7, 7)
        mine = QRectF(rect.right() - 14 - rect.width() * 0.3, rect.top() + 34, rect.width() * 0.3, 15)
        top, bottom, edge = t.pv_me
        p.setPen(QPen(QColor(edge), 1))
        p.setBrush(QBrush(sk.vgrad(mine, top, bottom)))
        p.drawRoundedRect(mine, 7, 7)
        sk.gloss(p, mine.adjusted(1, 1, -1, -1), 6, 80, 0.5)
        well = QRectF(left, rect.bottom() - 22, rect.right() - left - 10, 14)
        top, bottom, edge = t.pv_well
        p.setPen(QPen(QColor(edge), 1))
        p.setBrush(QBrush(sk.vgrad(well, top, bottom)))
        p.drawRoundedRect(well, 7, 7)
        sk.inner_shadow(p, well, 7, depth=5, alpha=80)
