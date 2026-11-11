"""Reminders, Memory and Connectors: the pages where you add, correct and connect things."""
import os
import threading
from datetime import datetime, timedelta

from PySide6.QtCore import QDateTime, QRectF, Signal
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QDateTimeEdit

from deskbuddy.ui.hub import styles, theme
from deskbuddy.ui.hub.icons import draw_glyph
from deskbuddy.ui.hub.page import Page, Snapshot, form_row, line_edit
from deskbuddy.ui.hub.widgets import button, card, matches, text

# slug, name, blob colour, blob letter
APPS = [("gmail", "Gmail", "#ea4335", "M"), ("googledrive", "Google Drive", "#1fa463", "D"),
        ("googlecalendar", "Google Calendar", "#4285f4", "C"), ("slack", "Slack", "#8b3fb0", "S"),
        ("notion", "Notion", "#2b2b2f", "N"), ("github", "GitHub", "#24292f", "G")]


def habit_when(habit) -> str:
    return habit.when().upper()


def habit_line(habit) -> str:
    days = f"seen on {habit.days} days"
    return f"Around {habit_when(habit)} · {days}"


class RemindersPage(Page):
    def __init__(self, memory, on_change):
        super().__init__()
        self.memory, self.on_change = memory, on_change
        self.what = line_edit("Remind me to…")
        self.what.setAccessibleName("Reminder text")
        self.what.returnPressed.connect(self.add)
        self.when = _date_edit()
        self._reset_time()
        self.top.addWidget(form_row((self.what, 1), (self.when, 0),
                                    (button("Add", "primary", self.add), 0)))
        self.error = text("", "error")
        self.error.hide()
        self.top.addWidget(self.error)

    def focus_input(self) -> None:
        self.what.setFocus()

    def _reset_time(self) -> None:
        soon = datetime.now().replace(second=0, microsecond=0) + timedelta(hours=1)
        self.when.setDateTime(QDateTime.fromSecsSinceEpoch(int(soon.timestamp())))

    def add(self) -> None:
        what = self.what.text().strip()
        due = self.when.dateTime().toSecsSinceEpoch()
        problem = ("Write what to remind you of first." if not what else
                   "That time has already passed. Pick a later one." if due <= datetime.now().timestamp()
                   else "")
        self.error.setText(problem)
        self.error.setVisible(bool(problem))
        if problem:
            return
        self.memory.add_reminder(what, due)
        self.what.clear()
        self._reset_time()
        self.on_change()

    def _remove(self, reminder_id: int) -> None:
        self.memory.remove_reminder(reminder_id)
        self.on_change()

    def fill(self, snap: Snapshot, query: str) -> None:
        items = [r for r in snap.reminders if matches(query, r[2])]
        if not self.changed((items, query)):
            return
        waiting = [r for r in items if not r[3]]
        shown = [r for r in items if r[3]]
        self.group("Waiting")
        if not waiting:
            self.empty("No matches." if query.strip() else "Nothing waiting. Add one above.")
        for rid, due, what, _fired in waiting:
            self.body.addWidget(card(what, meta=f"Due {theme.when_long(due)}", kind="waiting",
                                     actions=(("Remove", lambda r=rid: self._remove(r)),)))
        if shown:
            self.group("Already shown")
            for rid, due, what, _fired in shown:  # nothing disappears; it is marked shown
                self.body.addWidget(card(what, meta=theme.when_long(due), kind="shown", faded=True,
                                         actions=(("Remove", lambda r=rid: self._remove(r)),)))


class DateField(QDateTimeEdit):
    """The date box with a visible drop-down chevron (it opens the calendar)."""

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        p = QPainter(self)
        draw_glyph(p, "chev_d", QRectF(self.width() - 26, (self.height() - 14) / 2, 14, 14), styles.active().meta, 0.13)
        p.end()


def _date_edit() -> QDateTimeEdit:
    edit = DateField()
    edit.setObjectName("field")
    edit.setDisplayFormat("ddd MMM d, h:mm AP")
    edit.setCalendarPopup(True)
    edit.setMinimumWidth(190)
    edit.setAccessibleName("Reminder time")
    return edit


class MemoryPage(Page):
    def __init__(self, memory, on_change):
        super().__init__()
        self.memory, self.on_change = memory, on_change
        self.fact = line_edit("Remember…")
        self.fact.setAccessibleName("Something to remember")
        self.fact.returnPressed.connect(self.remember)
        self.top.addWidget(form_row((self.fact, 1), (button("Remember", "primary", self.remember), 0)))
        self.error = text("", "error")
        self.error.hide()
        self.top.addWidget(self.error)

    def focus_input(self) -> None:
        self.fact.setFocus()

    def remember(self) -> None:
        fact = self.fact.text().strip()
        self.error.setText("" if fact else "Write what to remember first.")
        self.error.setVisible(not fact)
        if not fact:
            return
        self.memory.add_pref(fact)
        self.fact.clear()
        self.on_change()

    def _forget(self, remove, item_id: int) -> None:
        remove(item_id)
        self.on_change()

    def fill(self, snap: Snapshot, query: str) -> None:
        facts = [f for f in snap.prefs if matches(query, f[1])]
        habits = [h for h in snap.habits if matches(query, h.order)]
        notes = [n for n in snap.notes if matches(query, n[1], n[2])]
        key = (facts, [(h.order, h.hour, h.days) for h in habits], notes, query)
        if not self.changed(key):
            return
        searching = bool(query.strip())
        self.group("What I know about you")
        if not facts:
            self.empty("No matches." if searching else "Nothing yet. Add something above, or tell me "
                       "\"remember that job replies are my important emails\".")
        for pref_id, fact in facts:
            self.body.addWidget(card(fact, actions=(
                ("Forget", lambda p=pref_id: self._forget(self.memory.remove_pref, p)),)))
        self.group("Routines I've noticed")
        if not habits:
            self.empty("No matches." if searching else "None yet. When you give the same order at about "
                       "the same time on three days, I offer it around then.")
        for habit in habits:
            self.body.addWidget(card(habit.order, meta=habit_line(habit)))
        self.group("Lessons from mistakes")
        if not notes:
            self.empty("No matches." if searching else "No lessons yet. When something fails on a site "
                       "or app, I note it so I do not repeat it.")
        for note_id, place, lesson in notes:
            self.body.addWidget(card(lesson, meta=place.capitalize(), actions=(
                ("Forget", lambda n=note_id: self._forget(self.memory.remove_note, n)),)))


def connectors_enabled() -> bool:
    return bool(os.environ.get("COMPOSIO_API_KEY", "").strip())


def fetch_connected() -> list[str]:
    from deskbuddy.connectors import tools as connectors

    return connectors.connected()


class ConnectorsPage(Page):
    loaded = Signal(object)

    def __init__(self, submit, goto):
        super().__init__()
        self.submit, self.goto = submit, goto
        self.result = "idle"   # idle | loading | None (off) | list of slugs | error text
        self._snap, self._query = Snapshot(), ""
        self.loaded.connect(self._on_loaded)

    def load(self) -> None:
        """Ask Composio which services are connected, off the UI thread."""
        if not connectors_enabled():
            self.result = None
            return
        self.result = "loading"

        def work() -> None:
            try:
                self.loaded.emit(fetch_connected())
            except Exception as error:
                self.loaded.emit(str(error) or "unknown error")

        threading.Thread(target=work, daemon=True).start()

    def _on_loaded(self, result) -> None:
        self.result = result
        if self.isVisible():
            self.fill(self._snap, self._query)

    def fill(self, snap: Snapshot, query: str) -> None:
        self._snap, self._query = snap, query
        result = self.result
        if not self.changed((str(result), query)):
            return
        if result == "idle":
            return
        if result == "loading":
            self.empty("Checking which services are connected…")
            return
        if result is None:
            self.body.addWidget(card(
                "Connectors are off", "Add a Composio key in Settings and press Save (no restart), or add Composio "
                "as an MCP server there. Keys: app.composio.dev.", kind="off",
                actions=(("Open Settings", lambda: self.goto("Settings", True)),)))
            return
        if isinstance(result, str):
            self.body.addWidget(card("I couldn't reach Composio", f"Because {result[:200]}", kind="couldnt",
                                     actions=(("Try again", self._retry),)))
            return
        known = {slug for slug, *_rest in APPS}
        for slug, name, color, letter in APPS:
            if not matches(query, name):
                continue
            if slug in result:
                self.body.addWidget(card(name, meta="Ready to use", kind="connected", blob=(color, letter)))
            else:
                self.body.addWidget(card(name, meta="Not connected", blob=(color, letter), actions=(
                    ("Connect", lambda n=name: self.submit(f"Connect my {n} account")),)))
        for slug in result:
            if slug not in known and matches(query, slug):
                self.body.addWidget(card(slug, meta="Ready to use", kind="connected",
                                         blob=("#8e8e93", slug[:1].upper())))
        if not query.strip():
            self.empty("For anything else, just tell me: \"connect my Spotify\".")

    def _retry(self) -> None:
        self.load()
        self.fill(self._snap, self._query)
