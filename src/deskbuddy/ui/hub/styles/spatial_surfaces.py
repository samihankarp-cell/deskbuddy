"""How the Spatial look paints its surfaces: the backdrop (dusk, or a bright day) with a soft shadow
under each pane, three floating frosted-glass panes, and glass capsules for everything inside them.
Backdrop, frost and panes are cached pixmaps (per variant: light and dark are separate Style
instances), so the 1.5 s refresh and Kettle's animation never rebuild them. Colours are tokens
(spatial_tokens.py)."""
from PySide6.QtCore import QPoint, QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QLinearGradient, QPainter, QPen, QRadialGradient

from deskbuddy.ui.hub.styles import spatial_paint as sp
from deskbuddy.ui.hub.styles.base import make_pixmap, ratio

PANE_RADIUS = 28.0


class SurfacePainter:
    """Mixin for SpatialStyle: `paint_surface` plus one `_role_*` method per surface role."""

    def pane_radius(self, role: str) -> float:
        return PANE_RADIUS if role in ("sidebar", "centre", "right") else 0.0

    # ---- token-aware helpers -------------------------------------------------------------------
    def w(self, alpha: int) -> QColor:
        """White at `alpha`, strengthened for the light variant (white on white needs more)."""
        return sp.white(min(255, int(alpha * self.t.gain)))

    def glass(self, p, rect, radius, top=36, bottom=18, edge=95, tint=None) -> QRectF:
        return sp.glass(p, rect, radius, top, bottom, edge, tint, self.t.gain, self.t.hair)

    def shadow(self, p, rect, radius, spread=26, dy=12, strength=0.5) -> None:
        sp.soft_shadow(p, rect, radius, spread, dy, strength * self.t.shadow_gain, self.t.shade)

    # ---- the window: backdrop, its frosted copy, shadows ------------------------------------
    def _backdrop(self, w: int, h: int, dpr: float):
        return self.cached("sp_back", (w, h, dpr), lambda: sp.backdrop(w, h, dpr, self.t))

    def _frost(self, w: int, h: int, dpr: float):
        return self.cached("sp_frost", (w, h, dpr), lambda: sp.blurred(self._backdrop(w, h, dpr)))

    @staticmethod
    def _panes(window) -> tuple:
        """The pane rectangles (x, y, w, h) in window coordinates, for the shadows."""
        stack = getattr(window, "stack", None)
        found = (getattr(window, "sidebar", None), stack.parentWidget() if stack else None,
                 getattr(window, "right", None))
        return tuple((w.x(), w.y(), w.width(), w.height()) for w in found if w and not w.isHidden())

    def paint_window(self, p: QPainter, window) -> None:
        w, h, dpr = window.width(), window.height(), ratio(p)
        panes = self._panes(window)

        def make():
            scene = self._backdrop(w, h, dpr).copy()
            scene.setDevicePixelRatio(dpr)
            q = QPainter(scene)
            q.setRenderHint(QPainter.RenderHint.Antialiasing)
            for x, y, pw, ph in panes:
                self.shadow(q, QRectF(x, y, pw, ph), PANE_RADIUS)
            q.end()
            return scene

        p.drawPixmap(0, 0, self.cached("sp_scene", (w, h, dpr, panes), make))

    def paint_surface(self, p: QPainter, widget, role: str) -> None:
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        paint = getattr(self, f"_role_{role}", None)
        if paint:
            paint(p, QRectF(widget.rect()), widget)

    # ---- the three panes ----------------------------------------------------------------------
    def _pane(self, p, rect, widget, role) -> None:
        window = widget.window()
        spot = widget.mapTo(window, QPoint(0, 0))
        dpr, w, h = ratio(p), rect.width(), rect.height()
        key = (w, h, spot.x(), spot.y(), window.width(), window.height(), dpr)
        t = self.t

        def make():
            frost = self._frost(window.width(), window.height(), dpr)
            pixmap = make_pixmap(w, h, dpr)
            q = QPainter(pixmap)
            q.setRenderHint(QPainter.RenderHint.Antialiasing)
            q.drawPixmap(QRectF(0, 0, w, h), frost,
                         QRectF(spot.x() * dpr, spot.y() * dpr, w * dpr, h * dpr))
            q.setCompositionMode(QPainter.CompositionMode.CompositionMode_DestinationIn)
            q.setPen(Qt.PenStyle.NoPen)
            q.setBrush(QColor(0, 0, 0, 255))
            q.drawRoundedRect(QRectF(0, 0, w, h), PANE_RADIUS, PANE_RADIUS)
            q.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
            q.setBrush(QColor(*t.pane_tint))
            q.drawRoundedRect(QRectF(0, 0, w, h), PANE_RADIUS, PANE_RADIUS)
            body = QRectF(0, 0, w, h)
            sheen = QLinearGradient(body.topLeft(), QPointF(body.left(), body.top() + min(h, 260)))
            sheen.setColorAt(0.0, sp.white(t.pane_sheen))
            sheen.setColorAt(1.0, sp.white(0))
            q.setBrush(QBrush(sheen))
            q.drawRoundedRect(body, PANE_RADIUS, PANE_RADIUS)
            lamp = QRadialGradient(QPointF(w * 0.18, 0), max(w, 260) * 0.8)       # light from above-left
            lamp.setColorAt(0.0, sp.white(t.pane_lamp))
            lamp.setColorAt(1.0, sp.white(0))
            q.setBrush(QBrush(lamp))
            q.drawRoundedRect(body, PANE_RADIUS, PANE_RADIUS)
            if t.hair[3]:
                q.setPen(QPen(QColor(*t.hair), 1))
                q.setBrush(Qt.BrushStyle.NoBrush)
                q.drawRoundedRect(body.adjusted(0.5, 0.5, -0.5, -0.5), PANE_RADIUS - 0.5, PANE_RADIUS - 0.5)
            sp.rim(q, body.adjusted(0.5, 0.5, -0.5, -0.5), PANE_RADIUS - 0.5, t.pane_rim)
            sp.rim(q, body.adjusted(1.5, 1.5, -1.5, -1.5), PANE_RADIUS - 1.5, t.pane_rim2)
            q.end()
            return pixmap

        p.drawPixmap(rect.topLeft(), self.cached(f"sp_pane_{role}", key, make))

    def _role_sidebar(self, p, rect, widget) -> None:
        self._pane(p, rect, widget, "sidebar")

    def _role_centre(self, p, rect, widget) -> None:
        self._pane(p, rect, widget, "centre")

    def _role_right(self, p, rect, widget) -> None:
        self._pane(p, rect, widget, "right")

    # ---- header and composer --------------------------------------------------------------------
    def _role_header(self, p, rect, widget) -> None:
        """A faint band of glass across the top of the centre pane (clipped to its rounded corners)."""
        pane = widget.parentWidget()
        if pane is not None:
            p.setClipPath(sp.rrect(QRectF(pane.rect()).translated(-widget.x(), -widget.y()), PANE_RADIUS))
        top, bottom = self.t.head_wash
        p.fillRect(rect, QBrush(sp.vgrad(rect, (0.0, sp.white(top)), (1.0, sp.white(bottom)))))
        p.setClipping(False)
        p.setPen(QPen(QColor(*self.t.head_line), 1))
        p.drawLine(QPointF(rect.left() + 20, rect.bottom() - 0.5), QPointF(rect.right() - 20, rect.bottom() - 0.5))

    def _role_composer(self, p, rect, widget) -> None:
        body = rect.adjusted(1, 1, -1, -4)
        radius = body.height() / 2
        self.shadow(p, body, radius, spread=5, dy=2.5, strength=0.28)
        self.glass(p, body, radius, top=52, bottom=28, edge=125)
        if widget.property("focused"):                       # a glowing accent ring
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(QPen(sp.rgba(self.accent, 70), 3))
            p.drawRoundedRect(body.adjusted(1.5, 1.5, -1.5, -1.5), radius - 1.5, radius - 1.5)
            p.setPen(QPen(sp.rgba(self.accent, 235), 1.5))
            p.drawRoundedRect(body.adjusted(0.75, 0.75, -0.75, -0.75), radius - 0.75, radius - 0.75)

    # ---- cards, forms, notes, bubbles -------------------------------------------------------------
    def _role_card(self, p, rect, _widget) -> None:
        self.glass(p, rect, 18, top=34, bottom=19, edge=78)

    def _role_form(self, p, rect, _widget) -> None:
        self.glass(p, rect, 18, top=26, bottom=14, edge=62)

    def _role_note(self, p, rect, _widget) -> None:
        self.glass(p, rect, min(16.0, rect.height() / 2), top=30, bottom=16, edge=70)

    def _role_bubbleBot(self, p, rect, _widget) -> None:
        self.glass(p, rect, min(20.0, rect.height() / 2), top=50, bottom=29, edge=110)

    def _role_bubbleMe(self, p, rect, _widget) -> None:
        radius = min(20.0, rect.height() / 2)
        colour, alpha = self.t.me_tint
        body = sp.glass(p, rect, radius, 34, 10, 120, sp.rgba(colour, alpha), 1.0, self.t.hair)   # tint, not white, carries it
        p.setPen(QPen(sp.rgba(self.accent, 120), 1))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(body.adjusted(1, 1, -1, -1), radius - 1, radius - 1)

    # ---- Kettle's stage -------------------------------------------------------------------------
    def _stage(self, name, p, rect, well: bool, floor: float) -> None:
        """No tile border: a halo of light behind Kettle and a soft shadow on the floor below it.
        `well` adds a barely-there glass bed (the big display). Painted once per size."""
        dpr, t = ratio(p), self.t

        def make():
            pixmap = make_pixmap(rect.width(), rect.height(), dpr)
            q = QPainter(pixmap)
            q.setRenderHint(QPainter.RenderHint.Antialiasing)
            w, h = rect.width(), rect.height()
            if well:
                bed = QRectF(0, 0, w, h)
                q.setPen(Qt.PenStyle.NoPen)
                q.setBrush(QBrush(sp.vgrad(bed, (0.0, sp.white(t.bed[0])), (1.0, sp.white(t.bed[1])))))
                q.drawRoundedRect(bed, 22, 22)
            reach = min(w, h) * 0.5          # the halo must end inside the rectangle: no visible edge
            centre = QPointF(w / 2, h * (0.5 if not well else 0.42))
            halo = QRadialGradient(centre, reach)
            halo.setColorAt(0.0, QColor(*t.halo, int(66 * t.halo_gain)))
            halo.setColorAt(0.55, QColor(*t.halo, int(24 * t.halo_gain)))
            halo.setColorAt(1.0, QColor(*t.halo, 0))
            q.setPen(Qt.PenStyle.NoPen)
            q.setBrush(QBrush(halo))
            q.drawEllipse(centre, reach, reach)
            sp.floor_shadow(q, w / 2, h * floor, w * 0.30, h * 0.035, int(135 * t.shadow_gain), t.shade)
            q.end()
            return pixmap

        p.drawPixmap(rect.topLeft(), self.cached(name, (rect.width(), rect.height(), dpr), make))

    def _role_tile(self, p, rect, _widget) -> None:
        self._stage("sp_tile", p, rect, False, 0.88)

    def _role_preview(self, p, rect, _widget) -> None:
        self._stage("sp_preview", p, rect, True, 0.74)

    # ---- the routines pad --------------------------------------------------------------------------
    def _role_notepad(self, p, rect, _widget) -> None:
        self.glass(p, rect, 20, top=20, bottom=9, edge=52)

    def _role_rule(self, p, rect, _widget) -> None:
        """Glass has no ruled lines."""
