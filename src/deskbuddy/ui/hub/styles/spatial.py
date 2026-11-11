"""Spatial: a visionOS-style look. Three frosted-glass panes float over a soft out-of-focus
backdrop (a dusk in the dark variant, a bright day in the light one); rows are glass capsules, icons
are glowing glass orbs, bubbles and pills are glass. All painted in code and cached. Surfaces live in
spatial_surfaces.py, materials in spatial_paint.py, colours in spatial_tokens.py."""
from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QLinearGradient, QPainter, QPen, QRadialGradient

from deskbuddy.ui.hub.styles import spatial_paint as sp
from deskbuddy.ui.hub.styles.base import ratio
from deskbuddy.ui.hub.styles.classic import ClassicStyle
from deskbuddy.ui.hub.styles.spatial_preview import miniature
from deskbuddy.ui.hub.styles.spatial_qss import BLUE_BOTTOM, BLUE_TOP, controls
from deskbuddy.ui.hub.styles.spatial_surfaces import SurfacePainter
from deskbuddy.ui.hub.styles.spatial_tokens import DARK, LIGHT


class SpatialStyle(SurfacePainter, ClassicStyle):
    key = "spatial"
    label = "Spatial"
    blurb = "Floating frosted glass."

    window_margins = (14, 14, 14, 14)
    pane_gap = 12
    press_shift = 1

    def __init__(self, dark: bool = False):
        super().__init__(dark)
        self._orbs: dict[tuple, object] = {}

    def tokens(self) -> dict:
        return DARK if self.dark else LIGHT

    # ---- QSS ---------------------------------------------------------------------------------
    def stylesheet(self) -> str:
        return self.label_qss() + controls(self)

    def surface_margins(self, role: str):
        return (10, 10, 6, 10) if role == "notepad" else None

    def text_shadow(self, name: str):
        return self.t.text_shadows.get(name)

    # ---- icons -------------------------------------------------------------------------------
    def _orb(self, p, rect, color, glyph="", letter="") -> None:
        dpr = ratio(p)
        w, h = round(rect.width(), 1), round(rect.height(), 1)
        key = (color, glyph, letter, w, h, dpr)
        pixmap = self._orbs.get(key)
        if pixmap is None:
            if len(self._orbs) > 64:
                self._orbs.clear()
            pixmap = self._orbs[key] = sp.orb(color, glyph, letter, w, h, dpr, self.t.orb_dark)
        p.drawPixmap(rect.topLeft(), pixmap)

    def paint_tile(self, p, rect, color, glyph="", letter="", circle=False) -> None:
        self._orb(p, rect, color, glyph, letter)

    def paint_check(self, p, rect) -> None:
        self._orb(p, rect.adjusted(1, 1, -1, -1), self.green, "check")

    def paint_unread(self, p, rect) -> None:
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        halo = QRadialGradient(rect.center(), rect.width() * 0.95)
        halo.setColorAt(0.0, sp.rgba(self.accent, 150))
        halo.setColorAt(1.0, sp.rgba(self.accent, 0))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(halo))
        p.drawEllipse(rect.center(), rect.width() * 0.95, rect.width() * 0.95)
        dot = rect.adjusted(1, 1, -1, -1)
        p.setBrush(QBrush(sp.vgrad(dot, (0.0, "#c4d6ff"), (1.0, self.accent))))
        p.drawEllipse(dot)

    # ---- controls ----------------------------------------------------------------------------
    def paint_round_button(self, p, rect, fill, hot, down, focused) -> None:
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        if fill == "strong":
            top, bottom = (("#6f8af4", "#4259d2") if hot else (BLUE_TOP, BLUE_BOTTOM))
            if down:
                top, bottom = bottom, top
            sp.disc(p, rect, top, bottom, 200)
        elif fill or hot or down:
            boost = 14 if hot or down else 0
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(sp.vgrad(rect, (0.0, self.w(52 + boost)), (1.0, self.w(26 + boost)))))
            p.drawEllipse(rect)
            if self.t.hair[3]:
                p.setPen(QPen(QColor(*self.t.hair), 1))
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.drawEllipse(rect)
            sp.rim(p, rect, rect.width() / 2, 150 if fill else 90)
        if focused:
            p.setPen(QPen(QColor(self.accent), 2))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(rect)

    def paint_row(self, p, box, checked, hot, focused) -> None:
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        radius = box.height() / 2
        if checked:                                          # a brighter capsule, lit around its orb
            tint = QColor(*self.t.row_tint) if self.t.row_tint else None
            body = self.glass(p, box, radius, top=52, bottom=34, edge=150, tint=tint)
            lit = QRadialGradient(body.left() + 22, body.center().y(), 52)
            lit.setColorAt(0.0, self.w(46))
            lit.setColorAt(1.0, self.w(0))
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(lit))
            p.drawRoundedRect(body.adjusted(1, 1, -1, -1), radius - 1, radius - 1)
        elif hot:
            self.glass(p, box, radius, top=30, bottom=14, edge=60)
        if focused:
            p.setPen(QPen(QColor(self.accent), 2))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(box.adjusted(1, 1, -1, -1), radius - 1, radius - 1)

    def paint_toggle(self, p, rect, on, focused) -> None:
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        t = self.t
        track = rect.adjusted(1, 1, -1, -1)
        r = track.height() / 2
        p.setPen(Qt.PenStyle.NoPen)
        if on:
            p.setBrush(sp.rgba(self.green, t.tog_on))
            p.drawRoundedRect(track, r, r)
        elif t.tog_base:
            p.setBrush(QColor(*t.tog_base))
            p.drawRoundedRect(track, r, r)
        top, bottom = t.tog_wash[on]
        p.setBrush(QBrush(sp.vgrad(track, (0.0, sp.white(top)), (1.0, sp.white(bottom)))))
        p.drawRoundedRect(track, r, r)
        if t.hair[3]:
            p.setPen(QPen(QColor(*t.hair), 1))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(track, r, r)
        sp.rim(p, track, r, 150)
        d = track.height() - 4
        knob = QRectF(track.right() - d - 2 if on else track.left() + 2, track.top() + 2, d, d)
        halo = QRadialGradient(knob.center(), d * 0.95)
        halo.setColorAt(0.0, sp.white(120))
        halo.setColorAt(1.0, sp.white(0))
        p.setBrush(QBrush(halo))
        p.drawEllipse(knob.center(), d * 0.95, d * 0.95)
        p.setBrush(QBrush(sp.vgrad(knob, (0.0, "#ffffff"), (1.0, "#dcd8f4"))))
        p.drawEllipse(knob)
        if focused:
            p.setPen(QPen(QColor(self.accent), 2))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(track.adjusted(-1.5, -1.5, 1.5, 1.5), r + 1.5, r + 1.5)

    def paint_pill(self, p, rect, group) -> str:
        ink, tint = self.pill_colors(group)
        t = self.t
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        body = rect.adjusted(0.5, 0.5, -0.5, -0.5)
        r = body.height() / 2
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(*t.pill_base))                      # smoky (dark) or milky (light) glass keeps the word legible
        p.drawRoundedRect(body, r, r)
        p.setBrush(sp.rgba(tint, t.pill_wash))
        p.drawRoundedRect(body, r, r)
        p.setBrush(QBrush(_sheen(body)))
        p.drawRoundedRect(body, r, r)
        p.setPen(QPen(sp.rgba(tint, 170), 1))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(body, r, r)
        return ink

    # ---- the Mode control: a glass trough with a brighter glass capsule ---------------------------
    def paint_segment_track(self, p, rect) -> None:
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        body = rect.adjusted(0.5, 0.5, -0.5, -0.5)
        r = body.height() / 2
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(*self.t.pill_base) if self.dark else QColor(255, 255, 255, 110))
        p.drawRoundedRect(body, r, r)
        if self.t.hair[3]:
            p.setPen(QPen(QColor(*self.t.hair), 1))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(body, r, r)
        sp.rim(p, body, r, 90)

    def paint_segment(self, p, rect, on, hot, focused) -> None:
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        body = rect.adjusted(3, 3, -3, -3)
        r = body.height() / 2
        if on:
            tint = QColor(*self.t.row_tint) if self.t.row_tint else None
            sp.soft_shadow(p, body, r, spread=4, dy=1.5, strength=0.22 * self.t.shadow_gain, rgb=self.t.shade)
            self.glass(p, body, r, top=70, bottom=46, edge=160, tint=tint if self.dark else QColor(255, 255, 255, 190))
        elif hot:
            self.glass(p, body, r, top=26, bottom=12, edge=60)
        if focused:
            p.setPen(QPen(QColor(self.accent), 2))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(rect.adjusted(1, 1, -1, -1), rect.height() / 2 - 1, rect.height() / 2 - 1)

    # ---- the Look chip ---------------------------------------------------------------------------
    def paint_preview(self, p: QPainter, rect: QRectF) -> None:
        dpr = ratio(p)
        key = (round(rect.width()), round(rect.height()), dpr)
        pixmap = self.cached("sp_preview_chip", key, lambda: miniature(key[0], key[1], dpr, self.t))
        p.drawPixmap(rect.topLeft(), pixmap)


def _sheen(body: QRectF) -> QLinearGradient:
    grad = QLinearGradient(body.topLeft(), body.bottomLeft())
    grad.setColorAt(0.0, sp.white(30))
    grad.setColorAt(0.55, sp.white(4))
    grad.setColorAt(1.0, sp.white(0))
    return grad
