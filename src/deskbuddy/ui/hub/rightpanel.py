"""The right column: Kettle's live preview and status, then the Routines list."""
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QScrollArea, QVBoxLayout, QWidget

from deskbuddy.state import STATE_COLORS, BuddyState
from deskbuddy.ui.hub.icons import Glyph, GlyphButton
from deskbuddy.ui.hub.manage_pages import habit_line
from deskbuddy.ui.hub import theme
from deskbuddy.ui.hub.page import Snapshot
from deskbuddy.ui.hub.surface import ShadowLabel, Surface
from deskbuddy.ui.hub.widgets import clear, text
from deskbuddy.ui.kettle import KettleWidget

WIDTH = 270
SHOWN_ROUTINES = 6


class RightPanel(Surface):
    collapse = Signal()
    settings = Signal()
    add_routine = Signal()

    def __init__(self):
        super().__init__("right", "rightpanel")
        self.setFixedWidth(WIDTH)
        box = QVBoxLayout(self)
        box.setContentsMargins(16, 12, 16, 14)
        box.setSpacing(0)

        top = QHBoxLayout()
        top.addStretch(1)
        gear = GlyphButton("gear", "Settings", 28, "meta", glyph_scale=0.62)
        gear.clicked.connect(self.settings)
        hide = GlyphButton("dchev_r", "Hide this panel", 28, "meta", glyph_scale=0.62)
        hide.clicked.connect(self.collapse)
        top.addWidget(gear)
        top.addWidget(hide)
        box.addLayout(top)
        box.addSpacing(8)

        preview = Surface("preview")
        preview.setFixedHeight(214)
        inner = QVBoxLayout(preview)
        inner.setContentsMargins(12, 14, 12, 12)
        inner.setSpacing(6)
        self.kettle = KettleWidget(width=140)
        inner.addWidget(self.kettle, 0, Qt.AlignmentFlag.AlignHCenter)
        inner.addStretch(1)
        status = QHBoxLayout()
        status.setSpacing(7)
        status.addStretch(1)
        self.dot = QLabel()
        self.dot.setFixedSize(8, 8)
        self.status = text("Idle", "status", select=False)
        self.status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        dot_box = QVBoxLayout()
        dot_box.setContentsMargins(0, 5, 0, 0)
        dot_box.addWidget(self.dot)
        dot_box.addStretch(1)
        status.addLayout(dot_box)
        status.addWidget(self.status, 0)
        status.addStretch(1)
        inner.addLayout(status)
        box.addWidget(preview)
        box.addSpacing(18)

        head = QHBoxLayout()
        title = ShadowLabel("Routines")
        title.setObjectName("panelTitle")
        head.addWidget(title, 1)
        plus = GlyphButton("plus", "Add a reminder", 26, "ink", glyph_scale=0.58)
        plus.clicked.connect(self.add_routine)
        head.addWidget(plus)
        box.addLayout(head)
        box.addSpacing(4)

        holder = QWidget()
        holder.setObjectName("holder")
        self.list = QVBoxLayout(holder)
        self.list.setContentsMargins(0, 0, 4, 0)
        self.list.setSpacing(4)
        self.list.setAlignment(Qt.AlignmentFlag.AlignTop)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setWidget(holder)
        holder.setAutoFillBackground(False)
        scroll.viewport().setAutoFillBackground(False)
        self.pad = Surface("notepad")   # the look may lay the list on a pad of paper
        pad_box = QVBoxLayout(self.pad)
        pad_box.setContentsMargins(0, 0, 0, 0)
        pad_box.addWidget(scroll)
        box.addWidget(self.pad, 1)
        self._shown = object()
        self.set_state(BuddyState.IDLE)

    def set_state(self, state: BuddyState) -> None:
        self.kettle.set_state(state)
        self.dot.setStyleSheet(f"background:{STATE_COLORS[state]};border-radius:4px;")

    def set_status(self, value: str) -> None:
        line = value.split("\n")[0].strip()
        self.status.setText(line[:110] or "Idle")

    def fill(self, snap: Snapshot) -> None:
        waiting = snap.waiting[:SHOWN_ROUTINES]
        habits = snap.habits[:SHOWN_ROUTINES]
        key = (waiting, [(h.order, h.hour, h.days) for h in habits])
        if key == self._shown:
            return
        self._shown = key
        clear(self.list)
        for _rid, due, what, _fired in waiting:
            self._row(what, theme.when_long(due))
        for habit in habits:
            self._row(habit.order, habit_line(habit))
        if not waiting and not habits:
            self.list.addWidget(text("No reminders or routines yet. Tap + to add a reminder.", "empty"))

    def _row(self, title: str, sub: str) -> None:
        widget = Surface("rule")   # a look may rule a line under each routine
        row = QHBoxLayout(widget)
        row.setContentsMargins(0, 0, 0, 6)
        row.setSpacing(10)
        row.addWidget(Glyph("check_circle", "green", 20), 0, Qt.AlignmentFlag.AlignTop)
        col = QVBoxLayout()
        col.setSpacing(1)
        col.addWidget(text(title, "rowTitle"))
        col.addWidget(text(sub, "rowSub"))
        row.addLayout(col, 1)
        self.list.addWidget(widget)
