"""The left column: search, Desk Buddy's tile, one row per section, plugins and profile."""
import os

from PySide6.QtCore import QRectF, QSize, Qt, Signal
from PySide6.QtGui import QAction, QColor, QFontMetrics, QPainter
from PySide6.QtWidgets import QAbstractButton, QButtonGroup, QHBoxLayout, QLineEdit, QVBoxLayout

from deskbuddy.ui.hub import styles, theme
from deskbuddy.ui.hub.icons import GlyphButton, glyph_icon, paint_blob
from deskbuddy.ui.hub.page import Snapshot
from deskbuddy.ui.hub.surface import ShadowLabel, Surface
from deskbuddy.ui.hub.widgets import matches
from deskbuddy.ui.kettle import KettleWidget

WIDTH = 250


class SearchBox(QLineEdit):
    """Esc clears the text; Esc again leaves the box."""

    def __init__(self):
        super().__init__()
        self.setObjectName("search")
        self.setPlaceholderText("Search")
        self.setAccessibleName("Search")
        self.setClearButtonEnabled(False)
        self.magnifier = QAction("", self)
        self.addAction(self.magnifier, QLineEdit.ActionPosition.LeadingPosition)
        self.restyle()

    def restyle(self) -> None:
        self.magnifier.setIcon(glyph_icon("search", styles.active().side_meta, 16))

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Escape:
            if self.text():
                self.clear()
            else:
                self.clearFocus()
            return
        super().keyPressEvent(event)


class Row(QAbstractButton):
    """A section row: coloured blob, bold title, one grey preview line, a time on the right."""

    def __init__(self, title: str, color: str, glyph: str = "", mini: bool = False,
                 initials: str = "", subtitle: str = ""):
        super().__init__()
        self.title, self.color, self.glyph, self.mini, self.initials = title, color, glyph, mini, initials
        self.preview, self.stamp, self.unread = subtitle, "", False
        self.setCheckable(not mini and not initials)
        self.setFixedHeight(42 if mini else 56)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        self._describe()

    def sizeHint(self) -> QSize:
        return QSize(WIDTH, self.height())

    def set_content(self, preview: str, stamp: str, unread: bool) -> None:
        if (preview, stamp, unread) != (self.preview, self.stamp, self.unread):
            self.preview, self.stamp, self.unread = preview, stamp, unread
            self._describe()
            self.update()

    def _describe(self) -> None:
        said = f"{self.title}. {self.preview}" if self.preview else self.title
        self.setAccessibleName(said + (". Unread updates" if self.unread else ""))

    def keyPressEvent(self, event) -> None:
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.click()
        else:
            super().keyPressEvent(event)

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        style = styles.active()
        box = QRectF(self.rect()).adjusted(8, 1, -8, -1)
        style.paint_row(p, box, self.isChecked(), self.underMouse() or self.isDown(), self.hasFocus())
        size = 20 if self.mini else 24
        blob = QRectF(box.left() + 8, box.center().y() - size / 2, size, size)
        paint_blob(p, blob, self.color, self.glyph, letter=self.initials, circle=bool(self.initials))
        left, right = blob.right() + 11, box.right() - 8
        title_font, small_font = theme.ui_font(13, bold=True), theme.ui_font(12)
        shadow = style.text_shadow("rowTitle")

        def draw(rect, flags, line, font, colour, shaded=False):
            p.setFont(font)
            if shaded and shadow:
                p.setPen(QColor(shadow[2]))
                p.drawText(rect.translated(shadow[0], shadow[1]), int(flags), line)
            p.setPen(QColor(colour))
            p.drawText(rect, int(flags), line)

        if self.mini:
            width = int(right - left)
            draw(QRectF(left, box.top(), right - left, box.height()),
                 Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                 QFontMetrics(title_font).elidedText(self.title, Qt.TextElideMode.ElideRight, width),
                 title_font, style.side_ink, True)
            p.end()
            return
        stamp_font = theme.ui_font(11)
        stamp_w = QFontMetrics(stamp_font).horizontalAdvance(self.stamp) if self.stamp else 0
        draw(QRectF(right - stamp_w - 2, box.top() + 9, stamp_w + 2, 16),
             Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, self.stamp, stamp_font,
             style.side_meta)
        title_w = right - left - (stamp_w + 8 if stamp_w else 0)
        draw(QRectF(left, box.top() + 9, title_w, 16), Qt.AlignmentFlag.AlignVCenter,
             QFontMetrics(title_font).elidedText(self.title, Qt.TextElideMode.ElideRight, int(title_w)),
             title_font, style.side_ink, True)
        preview_w = right - left - (16 if self.unread else 0)
        draw(QRectF(left, box.top() + 27, preview_w, 16), Qt.AlignmentFlag.AlignVCenter,
             QFontMetrics(small_font).elidedText(self.preview, Qt.TextElideMode.ElideRight, int(preview_w)),
             small_font, style.side_ink if self.unread else style.side_meta)
        if self.unread:
            style.paint_unread(p, QRectF(right - 9, box.top() + 31, 9, 9))
        p.end()

    def enterEvent(self, event) -> None:
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self.update()
        super().leaveEvent(event)


def previews(snap: Snapshot, connectors_on: bool) -> dict[str, tuple[str, str]]:
    """Live preview line and time for each section, from real data."""
    out: dict[str, tuple[str, str]] = {}
    items = [i for i in snap.feed if i[1] != "user"] or snap.feed
    if items:
        ts, _role, line = items[0]
        out["Updates"] = (line.split("\n")[0], theme.short_time(ts))
    else:
        out["Updates"] = ("Nothing yet", "")
    if snap.jobs:
        ts, title, passed, _reason, _answer = snap.jobs[0]
        lead = "Working" if passed is None else "Done" if passed else "I couldn't"
        out["Activity"] = (f"{lead}: {title}", theme.short_time(ts))
    else:
        out["Activity"] = ("No jobs yet", "")
    waiting = snap.waiting
    out["Reminders"] = ((waiting[0][2], theme.short_time(waiting[0][1])) if waiting
                        else ("Nothing waiting", ""))
    if snap.prefs or snap.habits:
        facts, routines = len(snap.prefs), len(snap.habits)
        out["Memory"] = (f"{facts} {'fact' if facts == 1 else 'facts'} · "
                         f"{routines} {'routine' if routines == 1 else 'routines'}", "")
    else:
        out["Memory"] = ("Nothing remembered yet", "")
    out["Connectors"] = (("Gmail, Drive, Calendar and more" if connectors_on
                          else "Off · add a Composio key"), "")
    out["Settings"] = ("Keys, voice and alerts", "")
    return out


def user_name() -> str:
    try:
        name = os.getlogin()
    except OSError:
        name = ""
    return name or os.environ.get("USERNAME") or os.environ.get("USER") or "You"


def initials_of(name: str) -> str:
    parts = [p for p in name.replace(".", " ").replace("_", " ").replace("-", " ").split() if p]
    if not parts:
        return "?"
    return (parts[0][0] + parts[1][0]).upper() if len(parts) > 1 else parts[0][0].upper()


class Sidebar(Surface):
    section_chosen = Signal(str)
    new_order = Signal()
    plugins = Signal()
    profile = Signal()
    query_changed = Signal(str)

    def __init__(self):
        super().__init__("sidebar")
        self.setFixedWidth(WIDTH)
        box = QVBoxLayout(self)
        box.setContentsMargins(12, 14, 12, 12)
        box.setSpacing(0)

        top = QHBoxLayout()
        top.setSpacing(6)
        self.search = SearchBox()
        self.search.textChanged.connect(self.query_changed)
        top.addWidget(self.search, 1)
        plus = GlyphButton("plus", "New order", 30, "side", glyph_scale=0.55)
        plus.clicked.connect(self.new_order)
        top.addWidget(plus)
        box.addLayout(top)
        box.addSpacing(18)

        tile = Surface("tile")
        tile.setFixedSize(84, 84)
        inner = QVBoxLayout(tile)
        inner.setContentsMargins(0, 8, 0, 4)
        self.kettle = KettleWidget(width=62)
        inner.addWidget(self.kettle, 0, Qt.AlignmentFlag.AlignCenter)
        box.addWidget(tile, 0, Qt.AlignmentFlag.AlignHCenter)
        box.addSpacing(8)
        name = ShadowLabel("Desk Buddy")
        name.setObjectName("tileName")
        name.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        box.addWidget(name)
        box.addSpacing(14)

        self.group = QButtonGroup(self)
        self.rows: dict[str, Row] = {}
        for title, color, glyph in theme.SECTIONS:
            row = Row(title, color, glyph)
            row.clicked.connect(lambda _=False, t=title: self.section_chosen.emit(t))
            self.group.addButton(row)
            self.rows[title] = row
            box.addWidget(row)
        box.addStretch(1)

        self.plugins_row = Row("Plugins", theme.COLORS["Connectors"], "plug", mini=True)
        self.plugins_row.clicked.connect(self.plugins)
        box.addWidget(self.plugins_row)
        self.name = user_name()
        self.profile_row = Row(self.name, "#2b2b30", initials=initials_of(self.name), mini=True)
        self.profile_row.setAccessibleName(f"{self.name}, open Settings")
        self.profile_row.clicked.connect(self.profile)
        box.addWidget(self.profile_row)

    def set_current(self, name: str) -> None:
        self.rows[name].setChecked(True)

    def update_rows(self, snap: Snapshot, unread: int, connectors_on: bool) -> None:
        said = previews(snap, connectors_on)
        for title, row in self.rows.items():
            preview, stamp = said[title]
            row.set_content(preview, stamp, title == "Updates" and unread > 0)
        self.apply_filter(self.search.text())

    def apply_filter(self, query: str) -> None:
        for row in self.rows.values():
            row.setVisible(matches(query, row.title, row.preview))
