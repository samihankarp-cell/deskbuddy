"""How the Skeuomorphic look paints its surfaces: leather sidebar, linen page, brushed-metal
header, paper cards, leather-capsule orders, felt display tile, notepad. Column textures are
cached per size (and per variant: light and dark are separate Style instances), so the 1.5 s
refresh and Kettle's animation never rebuild them. Every colour is a token (skeuo_tokens.py)."""
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QLinearGradient, QPainter, QPen, QRadialGradient

from deskbuddy.ui.hub.styles import skeuo_paint as sk
from deskbuddy.ui.hub.styles.base import make_pixmap, ratio


def _c(rgba: tuple) -> QColor:
    return QColor(*rgba)


class SurfacePainter:
    """Mixin for SkeuoStyle: `paint_surface` plus one `_role_*` method per surface role."""

    def paint_window(self, p: QPainter, window) -> None:
        p.fillRect(window.rect(), QColor(self.t.win))

    def paint_surface(self, p: QPainter, widget, role: str) -> None:
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        paint = getattr(self, f"_role_{role}", None)
        if paint:
            paint(p, QRectF(widget.rect()), widget)

    # ---- the three columns ------------------------------------------------------------------
    def _column(self, name: str, p: QPainter, rect: QRectF, tile, finish) -> None:
        dpr = ratio(p)
        w, h = rect.width(), rect.height()

        def make():
            pixmap = make_pixmap(w, h, dpr)
            q = QPainter(pixmap)
            q.drawTiledPixmap(QRectF(0, 0, w, h), self.cached(f"{name}_tile", dpr, lambda: tile(dpr)))
            finish(q, w, h)
            q.end()
            return pixmap

        p.drawPixmap(rect.topLeft(), self.cached(name, (w, h, dpr), make))

    def _role_sidebar(self, p, rect, _widget) -> None:
        t = self.t

        def finish(q, w, h):
            vignette = QRadialGradient(QPointF(w * 0.5, h * 0.36), max(w, h) * 0.8)
            vignette.setColorAt(0.0, QColor(0, 0, 0, 0))
            vignette.setColorAt(0.5, QColor(0, 0, 0, 0))
            vignette.setColorAt(1.0, QColor(18, 6, 0, 140))
            q.fillRect(QRectF(0, 0, w, h), QBrush(vignette))
            q.fillRect(QRectF(0, 0, w, 150), QBrush(_fade(QRectF(0, 0, w, 150), _c(t.side_glow))))
            edge = QLinearGradient(QPointF(w - 18, 0), QPointF(w, 0))
            edge.setColorAt(0, QColor(0, 0, 0, 0))
            edge.setColorAt(1, QColor(0, 0, 0, 105))
            q.fillRect(QRectF(w - 18, 0, 18, h), QBrush(edge))
            q.fillRect(QRectF(w - 1, 0, 1, h), QColor(20, 8, 0, 230))
            q.fillRect(QRectF(w - 4, 0, 1, h), QColor(255, 226, 180, 40))   # the welt
            sk.stitches(q, w - 9.5, 8, h - 8)

        self._column("sidebar", p, rect, lambda d: sk.leather_tile(t.leather, d), finish)

    def _role_centre(self, p, rect, _widget) -> None:
        t = self.t

        def finish(q, w, h):
            vignette = QRadialGradient(QPointF(w / 2, h * 0.45), max(w, h) * 0.75)
            vignette.setColorAt(0.55, QColor(*t.vig_c[:3], 0))
            vignette.setColorAt(1.0, _c(t.vig_c))
            q.fillRect(QRectF(0, 0, w, h), QBrush(vignette))

        self._column("centre", p, rect, lambda d: sk.linen_tile(t.linen, d, t.weave), finish)

    def _role_right(self, p, rect, _widget) -> None:
        t = self.t

        def finish(q, w, h):
            vignette = QRadialGradient(QPointF(w / 2, h * 0.4), max(w, h) * 0.8)
            vignette.setColorAt(0.5, QColor(*t.vig_r[:3], 0))
            vignette.setColorAt(1.0, _c(t.vig_r))
            q.fillRect(QRectF(0, 0, w, h), QBrush(vignette))
            edge = QLinearGradient(QPointF(0, 0), QPointF(14, 0))
            edge.setColorAt(0, _c(t.r_shade))
            edge.setColorAt(1, QColor(*t.r_shade[:3], 0))
            q.fillRect(QRectF(0, 0, 14, h), QBrush(edge))
            q.fillRect(QRectF(0, 0, 1, h), _c(t.r_line))
            q.fillRect(QRectF(1, 0, 1, h), _c(t.r_hi))

        self._column("right", p, rect, lambda d: sk.linen_tile(t.linen_r, d, t.weave), finish)

    # ---- header, composer, forms -----------------------------------------------------------
    def _role_header(self, p, rect, _widget) -> None:
        t, dpr = self.t, ratio(p)
        body = QRectF(rect.left(), rect.top(), rect.width(), rect.height() - 4)
        p.fillRect(body, QBrush(sk.vgrad(body, t.head_top, t.head_bot)))
        p.drawTiledPixmap(body, self.cached("brushed", dpr, lambda: sk.brushed_tile(dpr, t.brush)))
        p.fillRect(QRectF(body.left(), body.top(), body.width(), 1), _c(t.head_hi))
        p.fillRect(QRectF(body.left(), body.bottom() - 1, body.width(), 1), _c(t.head_lo))
        shade = QRectF(body.left(), body.bottom(), body.width(), 4)
        p.fillRect(shade, QBrush(_fade(shade, _c(t.head_shade))))

    def _role_composer(self, p, rect, widget) -> None:
        t = self.t
        body = rect.adjusted(1, 1, -1, -3)
        radius = body.height() / 2
        p.setPen(QPen(_c(t.lip), 1))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(body.translated(0, 1.4), radius, radius)   # light catching the lip
        p.setPen(QPen(QColor(t.well_edge), 1))
        p.setBrush(QBrush(sk.vgrad(body, t.well_top, t.well_bot)))
        p.drawRoundedRect(body, radius, radius)
        sk.inner_shadow(p, body.adjusted(1, 1, -1, -1), radius, depth=9, alpha=85)
        if widget.property("focused"):
            p.setPen(QPen(QColor(self.accent), 2))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(body.adjusted(1, 1, -1, -1), radius - 1, radius - 1)

    def _role_form(self, p, rect, _widget) -> None:
        t = self.t
        body = rect.adjusted(1, 0.5, -1, -3)
        p.setPen(QPen(QColor(t.form_edge), 1))
        p.setBrush(QBrush(sk.vgrad(body, t.form_top, t.form_bot)))
        p.drawRoundedRect(body, 12, 12)
        sk.inner_shadow(p, body.adjusted(1, 1, -1, -1), 12, depth=7, alpha=55)
        p.setPen(QPen(_c(t.form_hi), 1))
        p.drawLine(QPointF(body.left() + 10, body.bottom() + 1.5), QPointF(body.right() - 10, body.bottom() + 1.5))

    # ---- paper cards and bubbles -----------------------------------------------------------
    def _paper(self, p, rect, radius, top, bottom, edge) -> QRectF:
        body = rect.adjusted(1, 0.5, -1, -3.5)
        sk.drop_shadow(p, body, radius, rgb=self.t.shadow)
        p.setPen(QPen(QColor(edge), 1))
        p.setBrush(QBrush(sk.vgrad(body, top, bottom)))
        p.drawRoundedRect(body, radius, radius)
        p.setPen(QPen(_c(self.t.card_hi), 1))
        p.drawLine(QPointF(body.left() + radius * 0.7, body.top() + 1.5),
                   QPointF(body.right() - radius * 0.7, body.top() + 1.5))
        return body

    def _card_paper(self, p, rect, radius) -> None:
        t = self.t
        self._paper(p, rect, radius, t.card_top, t.card_bot, t.card_edge)

    def _role_card(self, p, rect, _widget) -> None:
        self._card_paper(p, rect, 10)

    def _role_note(self, p, rect, _widget) -> None:
        t = self.t
        self._paper(p, rect, 12, t.note_top, t.note_bot, t.note_edge)

    def _role_bubbleBot(self, p, rect, _widget) -> None:
        self._card_paper(p, rect, 14)

    def _role_bubbleMe(self, p, rect, _widget) -> None:
        t = self.t
        body = rect.adjusted(1, 0.5, -1, -3.5)
        sk.drop_shadow(p, body, 14, alpha=t.me_shadow, rgb=t.shadow)
        p.setPen(QPen(QColor(t.me_edge), 1))
        p.setBrush(QBrush(sk.vgrad(body, t.me_top, t.me_bot, (0.5, t.me_mid))))
        p.drawRoundedRect(body, 14, 14)
        sk.gloss(p, body.adjusted(1, 1, -1, -1), 13, t.me_gloss, 0.5)
        p.setPen(QPen(_c(t.me_rim), 1))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(body.adjusted(1.5, 1.5, -1.5, -1.5), 12.5, 12.5)

    # ---- Kettle's display case ----------------------------------------------------------------
    def _cached_surface(self, name: str, p: QPainter, rect: QRectF, paint) -> None:
        """Paint `paint(painter, rect)` once per size into a pixmap, then just blit it (Kettle
        repaints the surfaces under it 30 times a second)."""
        dpr = ratio(p)

        def make():
            pixmap = make_pixmap(rect.width(), rect.height(), dpr)
            q = QPainter(pixmap)
            q.setRenderHint(QPainter.RenderHint.Antialiasing)
            paint(q, QRectF(0, 0, rect.width(), rect.height()))
            q.end()
            return pixmap

        p.drawPixmap(rect.topLeft(), self.cached(name, (rect.width(), rect.height(), dpr), make))

    def _felt(self, p, rect, radius) -> None:
        self._cached_surface(f"felt{radius}", p, rect, lambda q, r: self._felt_paint(q, r, radius))

    def _felt_paint(self, p, rect, radius) -> None:
        dpr = ratio(p)
        body = rect.adjusted(1, 1, -1, -4)
        sk.drop_shadow(p, body, radius, alpha=90, rgb=self.t.shadow)
        p.setPen(QPen(QColor("#3f2c0e"), 1))
        p.setBrush(QBrush(sk.vgrad(body, "#ecd593", "#8c6c2e", (0.45, "#c9a65a"))))
        p.drawRoundedRect(body, radius, radius)                   # the brass frame
        inner = body.adjusted(3.5, 3.5, -3.5, -3.5)
        p.save()
        p.setClipPath(sk.rrect(inner, radius - 3.5))
        p.drawTiledPixmap(inner, self.cached("felt", dpr, lambda: sk.felt_tile(self.t.felt, dpr)))
        p.restore()
        sk.inner_shadow(p, inner, radius - 3.5, depth=16, alpha=190, side=0.8)
        p.save()
        p.setClipPath(sk.rrect(inner, radius - 3.5))
        sheen = QLinearGradient(inner.topLeft(), QPointF(inner.center().x(), inner.bottom()))
        sheen.setColorAt(0, QColor(255, 255, 255, 34))
        sheen.setColorAt(0.5, QColor(255, 255, 255, 0))
        p.fillRect(inner, QBrush(sheen))                          # the glass over the case
        p.restore()
        p.setPen(QPen(QColor(0, 0, 0, 140), 1))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(inner, radius - 3.5, radius - 3.5)

    def _role_tile(self, p, rect, _widget) -> None:
        self._felt(p, rect, 16)

    def _role_preview(self, p, rect, _widget) -> None:
        self._felt(p, rect, 18)

    # ---- the routines notepad ------------------------------------------------------------------
    def _role_notepad(self, p, rect, _widget) -> None:
        self._cached_surface("notepad", p, rect, self._notepad_paint)

    def _notepad_paint(self, p, rect) -> None:
        t = self.t
        body = rect.adjusted(1, 0.5, -1, -3.5)
        sk.drop_shadow(p, body, 8, alpha=60, rgb=t.shadow)
        p.setPen(QPen(QColor(t.pad_edge), 1))
        p.setBrush(QBrush(sk.vgrad(body, t.pad_top, t.pad_bot)))
        p.drawRoundedRect(body, 8, 8)
        strip = QRectF(body.left(), body.top(), body.width(), 17)
        p.save()
        p.setClipPath(sk.rrect(body, 8))
        p.fillRect(strip, QBrush(sk.vgrad(strip, t.strip_top, t.strip_bot)))
        p.fillRect(QRectF(strip.left(), strip.bottom() - 1, strip.width(), 1), _c(t.strip_lo))
        p.fillRect(QRectF(strip.left(), strip.top(), strip.width(), 1), _c(t.strip_hi))
        p.restore()
        holes = max(2, int(body.width() // 34))
        for i in range(holes):
            cx = body.left() + body.width() * (i + 0.5) / holes
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(_c(t.hole_hi))
            p.drawEllipse(QPointF(cx, 9.6), 3.4, 3.4)
            p.setBrush(QColor(t.hole))
            p.drawEllipse(QPointF(cx, 8.8), 3.2, 3.2)
            p.setBrush(QColor(0, 0, 0, 90))
            p.drawEllipse(QPointF(cx, 9.3), 2.2, 2.0)

    def _role_rule(self, p, rect, _widget) -> None:
        y = rect.bottom() - 1.5
        p.setPen(QPen(_c(self.t.rule), 1))
        p.drawLine(QPointF(rect.left(), y), QPointF(rect.right(), y))


def _fade(rect: QRectF, colour: QColor) -> QLinearGradient:
    """A gradient from `colour` at the top of rect to fully clear at the bottom."""
    clear = QColor(colour)
    clear.setAlpha(0)
    grad = QLinearGradient(rect.topLeft(), rect.bottomLeft())
    grad.setColorAt(0, colour)
    grad.setColorAt(1, clear)
    return grad
