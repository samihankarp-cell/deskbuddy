"""Classic: the flat Grok-style look the dashboard shipped with (light), plus its dark twin. Also the
base the other looks build on: it implements every hook, so a new look overrides only what differs.
Colours come from classic_tokens.py (one dict per mode); the code below never holds a literal one
except the white glyphs on the coloured section tiles."""
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPen

from deskbuddy.ui.hub import glyphs, theme
from deskbuddy.ui.hub.styles.base import FIELD, FIELD_FOCUS, Style
from deskbuddy.ui.hub.styles.classic_tokens import DARK, LIGHT

# role -> (token holding its fill, radius) for the plain rounded surfaces
ROUNDED = {"tile": ("tile", 16), "preview": ("preview", 18), "card": ("card", 12), "form": ("card", 14),
           "note": ("card", 12), "bubbleBot": ("bubble", 14), "bubbleMe": ("me_fill", 14)}


class ClassicStyle(Style):
    key = "classic"
    label = "Classic"
    blurb = "Flat, light and calm."

    def tokens(self) -> dict:
        return DARK if self.dark else LIGHT

    def ph(self, colour: str) -> str:
        """Placeholder colour for an input. Light keeps Qt's own; dark must say it (the default
        follows the system palette and would vanish on a dark input)."""
        return f"placeholder-text-color: {colour};" if self.dark else ""

    def font_css(self) -> str:
        return ", ".join(f'"{name}"' for name in self.families)

    def surface_insets(self, role: str) -> tuple[int, int, int, int]:
        return {"sidebar": (0, 0, 1, 0), "right": (1, 0, 0, 0), "header": (0, 0, 0, 1),
                "composer": (1, 1, 1, 1)}.get(role, (0, 0, 0, 0))

    def surface_margins(self, role: str):
        return (0, 0, 0, 0) if role == "notepad" else None

    # ---- QSS ---------------------------------------------------------------------------------
    def stylesheet(self) -> str:
        return self.label_qss() + self.control_qss()

    def label_qss(self) -> str:
        """Fonts and label colours; they follow the colour tokens, so a look rarely overrides them."""
        c = self
        return f"""
    QWidget {{ font-family: {self.font_css()}; font-size: 13px; }}
    QWidget#holder, QWidget#page {{ background: transparent; }}
    QScrollArea {{ background: transparent; border: none; }}
    QLabel {{ background: transparent; color: {c.ink}; }}
    QToolTip {{ background: {c.t.tip_bg}; color: {c.t.tip_ink}; border: none; padding: 4px 8px; }}

    QFrame#sidebar QLabel#tileName {{ font-size: 13px; font-weight: 600; color: {c.side_ink}; }}
    QLabel#headerTitle {{ font-size: 13px; font-weight: 600; }}
    QLabel#panelTitle {{ font-size: 13px; font-weight: 600; }}
    QLabel#status {{ color: {c.body}; font-size: 12px; }}
    QLabel#rowTitle {{ font-size: 13px; font-weight: 600; }}
    QLabel#rowSub {{ color: {c.meta}; font-size: 12px; }}
    QLabel#group {{ color: {c.meta}; font-size: 12px; font-weight: 600; padding-top: 12px; }}
    QLabel#empty {{ color: {c.meta}; font-size: 13px; padding: 6px 2px; }}
    QLabel#dayLabel {{ color: {c.meta}; font-size: 11px; font-weight: 600; padding: 8px 0 2px 0; }}
    QLabel#stamp {{ color: {c.meta}; font-size: 11px; }}
    QLabel#error {{ color: {c.error_ink}; font-size: 12px; }}
    QLabel#saved {{ color: {c.error_ink}; font-size: 12px; font-weight: 600; }}
    QLabel#saved[ok="true"] {{ color: {c.ok_ink}; }}
    QLabel#pill {{ font-size: 11px; font-weight: 600; }}
    QLabel#pageTitle {{ font-size: 18px; font-weight: 600; }}

    QLabel#cardTitle {{ font-size: 13px; font-weight: 600; }}
    QLabel#cardTitleFaded {{ color: {c.meta}; font-size: 13px; font-weight: 600; }}
    QLabel#cardBody {{ color: {c.body}; font-size: 13px; }}
    QLabel#cardMeta {{ color: {c.meta}; font-size: 12px; }}
    QLabel#fieldLabel {{ color: {c.body}; font-size: 12px; font-weight: 600; }}
    QLabel#hint {{ color: {c.meta}; font-size: 12px; }}

    QLabel#bubbleBotText {{ color: {c.ink}; font-size: 13px; }}
    QLabel#bubbleMeText {{ color: {c.t.me_ink}; font-size: 13px; }}
    QLabel#noteText {{ color: {c.body}; font-size: 12px; }}
    """

    def control_qss(self) -> str:
        """Inputs, buttons, scroll bars, menus: what a look usually restyles."""
        c, t = self, self.t
        return f"""
    QLineEdit#search {{ background: {t.hover}; color: {c.side_ink}; border: 2px solid transparent;
        border-radius: 11px; padding: 5px 6px 5px 2px; {c.ph(c.side_meta)} }}
    QLineEdit#search:focus {{ background: {t.bg}; border: 2px solid {c.ink}; }}
    {FIELD} {{ background: {t.field}; color: {c.ink};
        border: 1px solid {t.edge}; border-radius: 10px; padding: 7px 10px;
        selection-background-color: {c.ink}; selection-color: {t.bg}; {c.ph(c.meta)} }}
    {FIELD_FOCUS} {{ border: 2px solid {c.ink}; padding: 6px 9px; }}
    QLineEdit#composerEdit {{ background: transparent; color: {c.ink}; border: none; padding: 6px 4px;
        font-size: 14px; {c.ph(c.meta)} }}
    QDateTimeEdit#field::drop-down {{ border: none; width: 22px; }}

    QPushButton#primary {{ background: {c.ink}; color: {t.on_ink}; border: 2px solid {c.ink}; border-radius: 16px;
        padding: 5px 16px; font-weight: 600; }}
    QPushButton#primary:hover {{ background: {t.primary_hot}; border-color: {t.primary_hot}; }}
    QPushButton#primary:pressed {{ background: {t.primary_down}; }}
    QPushButton#primary:focus {{ border: 2px solid {c.accent}; }}
    QPushButton#quiet {{ background: {t.quiet}; color: {c.ink}; border: 1px solid {t.edge}; border-radius: 12px;
        padding: 4px 12px; font-size: 12px; }}
    QPushButton#quiet:hover {{ background: {t.hover}; }}
    QPushButton#quiet:focus {{ border: 2px solid {c.ink}; padding: 3px 11px; }}

    QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
    QScrollBar::handle:vertical {{ background: {t.sb}; border-radius: 3px; min-height: 36px; }}
    QScrollBar::handle:vertical:hover {{ background: {t.sb_hot}; }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; }}

    QMenu {{ background: {t.menu}; border: 1px solid {t.edge}; border-radius: 10px; padding: 6px; }}
    QMenu::item {{ padding: 7px 18px; border-radius: 6px; color: {c.ink}; }}
    QMenu::item:selected {{ background: {t.hover}; color: {c.ink}; }}
    """

    # ---- window and surfaces -----------------------------------------------------------------
    def paint_window(self, p: QPainter, window) -> None:
        p.fillRect(window.rect(), QColor(self.t.bg))

    def paint_surface(self, p: QPainter, widget, role: str) -> None:
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r, t = QRectF(widget.rect()), self.t
        line = QColor(t.line)
        if role in ("sidebar", "centre", "right", "header"):
            p.fillRect(r, QColor(t.side_bg if role == "sidebar" else t.bg))
            p.setPen(line)
            if role == "sidebar":
                p.drawLine(QPointF(r.right() - 0.5, r.top()), QPointF(r.right() - 0.5, r.bottom()))
            elif role == "right":
                p.drawLine(QPointF(r.left() + 0.5, r.top()), QPointF(r.left() + 0.5, r.bottom()))
            elif role == "header":
                p.drawLine(QPointF(r.left(), r.bottom() - 0.5), QPointF(r.right(), r.bottom() - 0.5))
        elif role == "composer":
            focused = bool(widget.property("focused"))
            width = 2.0 if focused else 1.0
            p.setPen(QPen(QColor(self.ink if focused else t.edge), width))
            p.setBrush(QColor(t.composer))
            box = r.adjusted(width / 2, width / 2, -width / 2, -width / 2)
            p.drawRoundedRect(box, 24 - width / 2, 24 - width / 2)
        elif role in ROUNDED:
            fill, radius = ROUNDED[role]
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(getattr(t, fill)))
            p.drawRoundedRect(r, radius, radius)

    # ---- icons and controls ------------------------------------------------------------------
    def paint_tile(self, p, rect, color, glyph="", letter="", circle=False) -> None:
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(color))
        radius = rect.width() / 2 if circle else rect.width() * 0.3
        p.drawRoundedRect(rect, radius, radius)
        if glyph:
            inset = rect.width() * 0.22
            glyphs.draw_glyph(p, glyph, rect.adjusted(inset, inset, -inset, -inset), "#ffffff", 0.12)
        elif letter:
            p.setPen(QColor("#ffffff"))
            p.setFont(theme.ui_font(max(9, int(rect.height() * 0.42)), bold=True))
            p.drawText(rect, Qt.AlignmentFlag.AlignCenter, letter)

    def paint_check(self, p, rect) -> None:
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(self.green))
        p.drawEllipse(rect.adjusted(rect.width() * 0.04, rect.height() * 0.04,
                                    -rect.width() * 0.04, -rect.height() * 0.04))
        tick = QRectF(rect.left() + rect.width() * 0.2, rect.top() + rect.height() * 0.2,
                      rect.width() * 0.6, rect.height() * 0.6)
        glyphs.draw_glyph(p, "check", tick, "#ffffff", 0.16)
        p.restore()

    def paint_round_button(self, p, rect, fill, hot, down, focused) -> None:
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        base = {"strong": self.ink, "soft": self.t.bubble}.get(fill) or (self.t.hover if hot or down else "")
        if base:
            colour = QColor(base)
            if fill and (hot or down):
                colour = colour.lighter(150) if colour.lightness() < 128 else colour.darker(106)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(colour)
            p.drawEllipse(rect)
        if focused:
            p.setPen(QPen(QColor(self.accent), 2))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(rect)

    def paint_row(self, p, box, checked, hot, focused) -> None:
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        if checked or hot:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(self.t.select if checked else self.t.row_hot))
            p.drawRoundedRect(box, 11, 11)
        if focused:
            p.setPen(QPen(QColor(self.ink), 2))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(box.adjusted(1, 1, -1, -1), 10, 10)

    def paint_unread(self, p, rect) -> None:
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(self.accent))
        p.drawEllipse(rect)

    def paint_toggle(self, p, rect, on, focused) -> None:
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        track = rect.adjusted(1, 1, -1, -1)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(self.ink if on else self.t.toggle_off))
        p.drawRoundedRect(track, track.height() / 2, track.height() / 2)
        if focused:
            p.setPen(QPen(QColor(self.accent), 2))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(track.adjusted(-1, -1, 1, 1), 12, 12)
        d = track.height() - 6
        x = track.right() - d - 3 if on else track.left() + 3
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(self.t.knob_on if on else self.t.knob_off))
        p.drawEllipse(QRectF(x, track.top() + 3, d, d))

    def pill_colors(self, group: str) -> tuple[str, str]:
        return self.t.pills[group]

    def paint_pill(self, p, rect, group) -> str:
        ink, fill = self.pill_colors(group)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(fill))
        p.drawRoundedRect(rect, 9, 9)
        return ink

    def paint_preview(self, p, rect) -> None:
        t = self.t
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        p.fillRect(rect, QColor(t.bg))
        side = QRectF(rect.left(), rect.top(), rect.width() * 0.28, rect.height())
        p.fillRect(side, QColor(t.side_bg))
        for i, colour in enumerate(("#ff6b2c", "#2d8cff", "#ffb020", "#8b6cff")):
            y = rect.top() + 12 + i * 12
            p.setBrush(QColor(colour))
            p.drawRoundedRect(QRectF(side.left() + 7, y, 8, 8), 2.5, 2.5)
            p.setBrush(QColor(t.edge))
            p.drawRoundedRect(QRectF(side.left() + 19, y + 2, side.width() - 28, 4), 2, 2)
        left = side.right() + 10
        p.setBrush(QColor(t.bubble))
        p.drawRoundedRect(QRectF(left, rect.top() + 12, rect.width() * 0.38, 15), 7, 7)
        p.setBrush(QColor(t.me_fill))
        p.drawRoundedRect(QRectF(rect.right() - 14 - rect.width() * 0.3, rect.top() + 34,
                                 rect.width() * 0.3, 15), 7, 7)
        p.setBrush(QColor(t.bubble))
        p.drawRoundedRect(QRectF(left, rect.top() + 56, rect.width() * 0.46, 15), 7, 7)
        p.setPen(QPen(QColor(t.edge), 1))
        p.setBrush(QColor(t.composer))
        p.drawRoundedRect(QRectF(left, rect.bottom() - 22, rect.right() - left - 10, 14), 7, 7)

    # ---- the Mode control --------------------------------------------------------------------
    def paint_segment_track(self, p, rect) -> None:
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(self.t.seg_track))
        p.drawRoundedRect(rect, rect.height() / 2, rect.height() / 2)

    def paint_segment(self, p, rect, on, hot, focused) -> None:
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        body = rect.adjusted(3, 3, -3, -3)
        radius = body.height() / 2
        if on or hot:
            p.setPen(QPen(QColor(self.t.seg_edge), 1) if on else Qt.PenStyle.NoPen)
            p.setBrush(QColor(self.t.seg_on if on else self.t.row_hot))
            p.drawRoundedRect(body, radius, radius)
        if focused:
            p.setPen(QPen(QColor(self.accent), 2))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(rect.adjusted(1, 1, -1, -1), rect.height() / 2 - 1, rect.height() / 2 - 1)
