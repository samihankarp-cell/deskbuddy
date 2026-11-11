"""The dashboard window: three calm columns (sections, the page, Kettle and routines)."""
import time
from pathlib import Path

from PySide6.QtCore import QTimer, Signal
from PySide6.QtGui import QGuiApplication, QKeySequence, QPainter, QShortcut
from PySide6.QtWidgets import QHBoxLayout, QStackedWidget, QVBoxLayout, QWidget

from deskbuddy.state import BuddyState
from deskbuddy.ui.hub import styles, theme
from deskbuddy.ui.hub.feed_pages import ActivityPage, UpdatesPage
from deskbuddy.ui.hub.icons import Blob, GlyphButton
from deskbuddy.ui.hub.manage_pages import (ConnectorsPage, MemoryPage, RemindersPage,
                                           connectors_enabled)
from deskbuddy.ui.hub.page import Snapshot
from deskbuddy.ui.hub.rightpanel import RightPanel
from deskbuddy.ui.hub.settings_page import SettingsPage
from deskbuddy.ui.hub.sidebar import Sidebar
from deskbuddy.ui.hub.styles import modes
from deskbuddy.ui.hub.surface import ShadowLabel, Surface

REFRESH_MS = 1500
SEEN_KEY = "updates_seen"      # when Updates was last looked at (memory.get / set)
RIGHT_KEY = "hub_right_open"   # whether the right panel is open
STYLE_KEY = "hub_style"        # which look: classic, skeuo or spatial
MODE_KEY = modes.MODE_KEY      # light, dark or system (follow Windows); default system


def unread_count(feed: list, seen: float) -> int:
    """Items Desk Buddy added since `seen`. Your own orders never count as news."""
    return sum(1 for ts, role, _line in feed if role != "user" and ts > seen)


class Dashboard(QWidget):
    hotkey_changed = Signal(str)   # a new hold-to-talk key was saved in Settings (the app rebinds it)
    settings_saved = Signal()      # Save was pressed in Settings (the app applies the new settings)

    def __init__(self, memory, submit, open_settings=None, env_file: Path | None = None):
        """`open_settings` is accepted for older callers; Settings is a page of this window now."""
        super().__init__()
        self.memory, self.submit = memory, submit
        self.query = ""
        self.current = theme.NAMES[0]
        self._habits, self._habits_for = [], None
        self.setObjectName("hub")
        self.mode = modes.clean(memory.get(MODE_KEY, modes.DEFAULT_MODE))
        styles.set_active(memory.get(STYLE_KEY, styles.DEFAULT), modes.is_dark(self.mode))
        self.setStyleSheet(theme.stylesheet())
        self.setWindowTitle("Desk Buddy")
        self.resize(1180, 760)
        self.setMinimumSize(880, 540)
        if not memory.get(SEEN_KEY):
            memory.set(SEEN_KEY, str(time.time()))  # a fresh install starts with nothing unread

        self.sidebar = Sidebar()
        self.right = RightPanel()
        centre = Surface("centre", "center")
        column = QVBoxLayout(centre)
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(0)
        column.addWidget(self._header())
        self.stack = QStackedWidget()
        column.addWidget(self.stack, 1)

        shortcuts = [("New reminder", lambda: self.open_section("Reminders", True)),
                     ("Remember something", lambda: self.open_section("Memory", True)),
                     ("Connect an app", lambda: self.open_section("Connectors"))]
        self.updates = UpdatesPage(submit, self.refresh, shortcuts)
        self.activity = ActivityPage()
        self.reminders = RemindersPage(memory, self.refresh)
        self.memory_page = MemoryPage(memory, self.refresh)
        self.connectors = ConnectorsPage(submit, self.open_section)
        self.settings = SettingsPage(memory, env_file, self.set_style, self.set_mode)
        self.settings.hotkey_changed.connect(self.hotkey_changed)
        self.settings.settings_saved.connect(self.settings_saved)
        self.settings.hotkey_changed.connect(self.updates.refresh_hotkey)
        self.pages = {"Updates": self.updates, "Activity": self.activity, "Reminders": self.reminders,
                      "Memory": self.memory_page, "Connectors": self.connectors, "Settings": self.settings}
        for name in theme.NAMES:
            self.stack.addWidget(self.pages[name])

        self.root = root = QHBoxLayout(self)
        root.addWidget(self.sidebar)
        root.addWidget(centre, 1)
        root.addWidget(self.right)

        self.sidebar.section_chosen.connect(self.show_section)
        self.sidebar.new_order.connect(lambda: self.open_section("Updates", True))
        self.sidebar.plugins.connect(lambda: self.open_section("Connectors"))
        self.sidebar.profile.connect(lambda: self.open_section("Settings"))
        self.sidebar.query_changed.connect(self._on_query)
        self.right.settings.connect(lambda: self.open_section("Settings"))
        self.right.add_routine.connect(lambda: self.open_section("Reminders", True))
        self.right.collapse.connect(lambda: self.set_right_open(False))
        self.expand.clicked.connect(lambda: self.set_right_open(True))

        hints = QGuiApplication.styleHints()   # Windows switched between light and dark
        if hasattr(hints, "colorSchemeChanged"):
            hints.colorSchemeChanged.connect(self._system_scheme_changed)

        QShortcut(QKeySequence("Ctrl+K"), self, activated=self.focus_search)
        for number, name in enumerate(theme.NAMES, 1):
            QShortcut(QKeySequence(f"Ctrl+{number}"), self, activated=lambda n=name: self.show_section(n))

        self.apply_style()
        self.set_right_open(memory.get(RIGHT_KEY, "1") != "0", remember=False)
        self.set_state(BuddyState.IDLE)
        self.show_section(self.current)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.refresh)
        self._timer.start(REFRESH_MS)

    # ---- layout pieces ---------------------------------------------------------
    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        styles.active().paint_window(p, self)
        p.end()

    def set_style(self, key: str) -> None:
        """Switch the look at once and remember it."""
        if key in styles.STYLES:
            styles.set_active(key, modes.is_dark(self.mode))
            self.memory.set(STYLE_KEY, key)
            self.apply_style()

    def set_mode(self, mode: str) -> None:
        """Switch Light / Dark / System at once and remember it (an unknown mode is ignored)."""
        if mode in modes.MODES:
            self.mode = mode
            self.memory.set(MODE_KEY, mode)
            self._follow_mode()

    def _follow_mode(self) -> None:
        """Paint with the variant of the current look that the mode asks for."""
        styles.set_active(styles.active().key, modes.is_dark(self.mode))
        self.apply_style()

    def _system_scheme_changed(self, _scheme=None) -> None:
        """Windows switched. A hidden window catches up when it is opened (see open())."""
        if self.mode == "system" and self.isVisible():
            self._follow_mode()

    def apply_style(self) -> None:
        """Re-skin everything that is already built: no widget is rebuilt, no restart."""
        look = styles.active()
        self.setStyleSheet(look.stylesheet())
        self.root.setContentsMargins(*look.window_margins)
        self.root.setSpacing(look.pane_gap)
        for surface in self.findChildren(Surface):
            surface.restyle()
        self.sidebar.search.restyle()
        self.settings.look.set_current(look.key)
        self.settings.mode.set_current(self.mode)
        for widget in self.findChildren(QWidget):
            widget.update()
        self.update()

    def _header(self) -> Surface:
        header = Surface("header")
        header.setFixedHeight(48)
        row = QHBoxLayout(header)
        row.setContentsMargins(26, 0, 14, 0)
        row.setSpacing(9)
        self.header_blob = Blob(theme.COLORS[self.current], theme.GLYPHS[self.current], size=20)
        self.header_title = ShadowLabel(self.current)
        self.header_title.setObjectName("headerTitle")
        row.addWidget(self.header_blob)
        row.addWidget(self.header_title, 1)
        self.expand = GlyphButton("dchev_l", "Show the side panel", 28, "meta", glyph_scale=0.62)
        row.addWidget(self.expand)
        return header

    # ---- called from the app -----------------------------------------------------
    def open(self) -> None:
        if self.mode == "system" and styles.active().dark != modes.is_dark(self.mode):
            self._follow_mode()   # Windows changed while this window was away
        self.show()
        self.raise_()
        self.activateWindow()
        self.refresh()
        if self.current == "Updates":
            self.updates.focus_input()  # ready to type

    def open_section(self, name: str, focus: bool = False) -> bool:
        """Show the window on one section. Returns False for a name that does not exist."""
        match = next((n for n in theme.NAMES if n.lower() == name.lower()), None)
        if match is None:
            return False
        self.show_section(match)
        self.open()
        if focus:
            self.pages[match].focus_input()
        return True

    def set_state(self, state: BuddyState) -> None:
        self.sidebar.kettle.set_state(state)
        self.right.set_state(state)

    def set_status(self, value: str) -> None:
        self.right.set_status(value)

    def set_right_open(self, opened: bool, remember: bool = True) -> None:
        self.right.setVisible(opened)
        self.expand.setVisible(not opened)
        if remember:
            self.memory.set(RIGHT_KEY, "1" if opened else "0")

    def focus_search(self) -> None:
        self.sidebar.search.setFocus()
        self.sidebar.search.selectAll()

    # ---- showing data --------------------------------------------------------------
    def show_section(self, name: str) -> None:
        self.current = name
        self.sidebar.set_current(name)
        self.stack.setCurrentWidget(self.pages[name])
        self.header_title.setText(name)
        self.header_blob.color, self.header_blob.glyph = theme.COLORS[name], theme.GLYPHS[name]
        self.header_blob.update()
        if name == "Connectors":
            self.connectors.load()
        self.refresh()

    def _on_query(self, query: str) -> None:
        self.query = query
        self.sidebar.apply_filter(query)
        self.refresh()

    def _snapshot(self) -> Snapshot:
        jobs = self.memory.jobs_recent(80)
        if jobs != self._habits_for:  # the routine search is the costly part; redo it only on new jobs
            self._habits_for, self._habits = jobs, self.memory.habits()
        return Snapshot(feed=self.memory.feed(40), jobs=jobs, reminders=self.memory.reminders(),
                        prefs=self.memory.prefs(), notes=self.memory.notes_all(), habits=self._habits)

    def refresh(self) -> None:
        if not self.isVisible():
            return
        snap = self._snapshot()
        seen = float(self.memory.get(SEEN_KEY, "0") or 0)
        if self.current == "Updates" and snap.feed:
            newest = max(ts for ts, _role, _line in snap.feed)
            if newest > seen:  # you are looking at them: they are read
                self.memory.set(SEEN_KEY, str(newest))
                seen = newest
        self.sidebar.update_rows(snap, unread_count(snap.feed, seen), connectors_enabled())
        self.right.fill(snap)
        self.pages[self.current].fill(snap, self.query)

