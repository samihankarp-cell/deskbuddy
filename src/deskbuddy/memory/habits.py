"""Noticing routines: orders the user gives at about the same time on several days.

Nothing extra is stored for this. Habits are worked out from the job history each time,
so memory does not fill up with guesses.
"""
import difflib
import statistics
import time
from dataclasses import dataclass
from datetime import datetime

LOOK_BACK_DAYS = 21
MIN_DAYS = 3            # seen on at least this many different days
HOUR_SPREAD = 1.5       # ...within this many hours of the usual time
SAME_ORDER = 0.82       # how alike two orders must read to count as the same
MAX_DECLINES = 3        # after this many "No", stop offering that habit


@dataclass
class Habit:
    key: str        # stable name for the habit
    order: str      # the order to run, as the user last said it
    hour: float     # usual time of day, e.g. 8.5 = half past eight
    days: int       # on how many days it was seen

    def when(self) -> str:
        hour, minute = int(self.hour), int(round((self.hour % 1) * 60 / 15) * 15) % 60
        return f"{hour % 12 or 12}:{minute:02d} {'am' if hour < 12 else 'pm'}"


def find_habits(rows: list[tuple[float, str]]) -> list[Habit]:
    """rows: (timestamp, order text) of orders that succeeded."""
    cutoff = time.time() - LOOK_BACK_DAYS * 86400
    clusters: list[dict] = []
    for ts, text in sorted(rows):
        if ts < cutoff or not text.strip():
            continue
        norm = " ".join(text.lower().split())
        moment = datetime.fromtimestamp(ts)
        seen = (moment.date(), moment.hour + moment.minute / 60, text)
        for cluster in clusters:
            if difflib.SequenceMatcher(None, norm, cluster["key"]).ratio() >= SAME_ORDER:
                cluster["seen"].append(seen)
                break
        else:
            clusters.append({"key": norm, "seen": [seen]})
    habits = []
    for cluster in clusters:
        by_day = {day: hour for day, hour, _ in cluster["seen"]}  # one sighting per day
        if len(by_day) < MIN_DAYS:
            continue
        usual = statistics.median(by_day.values())
        close = [h for h in by_day.values() if abs(h - usual) <= HOUR_SPREAD]
        if len(close) >= MIN_DAYS:
            habits.append(Habit(cluster["key"], cluster["seen"][-1][2],
                                statistics.median(close), len(close)))
    return sorted(habits, key=lambda h: -h.days)[:8]


def due_now(habits: list[Habit], done_today: set[str], state: dict[str, tuple[str, int]]) -> Habit | None:
    """The habit worth offering right now, if any. state: key -> (last offered day, declines)."""
    now = datetime.now()
    hour, today = now.hour + now.minute / 60, now.date().isoformat()
    for habit in habits:
        last_day, declines = state.get(habit.key, ("", 0))
        if last_day == today or declines >= MAX_DECLINES or habit.key in done_today:
            continue
        if -0.5 <= hour - habit.hour <= 0.75:
            return habit
    return None
