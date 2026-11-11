"""Updates (the conversation-like feed with the composer) and Activity (jobs by day)."""
import os

from PySide6.QtCore import QTimer

from deskbuddy.ui.hub import theme
from deskbuddy.ui.hub.page import Composer, Page, Snapshot
from deskbuddy.ui.hub.widgets import bubble, card, day_label, matches, note


def hotkey_name() -> str:
    return os.environ.get("DESKBUDDY_HOTKEY", "").strip().title() or "Right Ctrl"


class UpdatesPage(Page):
    """What Desk Buddy did and said, with your own orders as black bubbles on the right."""

    def __init__(self, submit, after_submit, shortcuts):
        super().__init__()
        self.composer = Composer("Tell Desk Buddy…", f"Hold {hotkey_name()} and speak, or type here")
        self.composer.menu_items = shortcuts
        self.composer.submitted.connect(submit)
        self._soon = QTimer(self)  # the brain writes the order to memory a moment later
        self._soon.setSingleShot(True)
        self._soon.timeout.connect(after_submit)
        self.composer.submitted.connect(lambda _text: self._soon.start(400))
        self.foot.addWidget(self.composer)

    def refresh_hotkey(self, _name: str = "") -> None:
        """The talk key changed: the mic hint and the empty-feed text follow."""
        self.composer.hint = f"Hold {hotkey_name()} and speak, or type here"
        self._shown = object()   # redraw the empty-feed text on the next refresh

    def focus_input(self) -> None:
        self.composer.edit.setFocus()

    def fill(self, snap: Snapshot, query: str) -> None:
        feed = [item for item in snap.feed if matches(query, item[2])]
        if not self.changed((feed, query)):
            return
        if not feed:
            self.empty("No matches." if query.strip() else
                       "Nothing yet. Type an order below, or hold "
                       f"{hotkey_name()} and say it.")
            return
        last_day = None
        for ts, role, line in reversed(feed):  # oldest first, like a conversation
            day = theme.day_label(ts)
            if day != last_day:
                last_day = day
                self.body.addWidget(day_label(day))
            if role == "user":
                self.body.addWidget(bubble(line, ts, mine=True))
            elif role == "reminder":
                self.body.addWidget(note(f"Reminder: {line}", ts))
            elif role == "offer":
                self.body.addWidget(bubble(line, ts, kind="suggestion"))
            else:
                self.body.addWidget(bubble(line, ts, kind=theme.verdict_of(line)))
        if not query.strip():
            self.scroll_to_end()


class ActivityPage(Page):
    """Every job, newest first and grouped by day, with its verdict and the real reason."""

    def fill(self, snap: Snapshot, query: str) -> None:
        jobs = [j for j in snap.jobs if matches(query, j[1], j[3], j[4])]
        if not self.changed((jobs, query)):
            return
        if not jobs:
            self.empty("No matches." if query.strip() else
                       "No jobs yet. Each one lands here with Done or I couldn't, and the reason.")
            return
        current = None
        for ts, title, passed, reason, answer in jobs:
            day = theme.day_label(ts)
            if day != current:
                current = day
                self.group(day)
            when = theme.clock(ts)
            if passed is None:
                self.body.addWidget(card(title, meta=when, kind="working"))
            elif passed:
                self.body.addWidget(card(title, answer or "", when, "done"))
            else:
                self.body.addWidget(card(title, f"Because {reason}" if reason else "", when, "couldnt"))
