"""Data and wording shared by every look: sections, verdict words, fonts, time phrases.
Colours, shapes and the stylesheet live in the active style (hub/styles/)."""
from datetime import datetime

from PySide6.QtGui import QFont

FAMILIES = ["Segoe UI Variable Text", "Segoe UI", "Helvetica Neue", "Arial"]

# section name, tile colour, glyph
SECTIONS = [
    ("Updates", "#ff6b2c", "updates"),
    ("Activity", "#2d8cff", "activity"),
    ("Reminders", "#ffb020", "clock"),
    ("Memory", "#8b6cff", "memory"),
    ("Connectors", "#14c3b0", "plug"),
    ("Settings", "#ff3fa4", "gear"),
]
NAMES = [name for name, _color, _glyph in SECTIONS]
COLORS = {name: color for name, color, _glyph in SECTIONS}
GLYPHS = {name: glyph for name, _color, glyph in SECTIONS}

# a verdict is always a word; its colour group (good/bad/warn/quiet/idea) only backs it up.
# The active style decides what each group looks like (Style.pill_colors).
PILLS = {
    "done": ("Done", "good"),
    "couldnt": ("I couldn't", "bad"),
    "working": ("Working", "warn"),
    "stopped": ("Stopped", "quiet"),
    "reminder": ("Reminder", "warn"),
    "waiting": ("Waiting", "warn"),
    "shown": ("Shown", "quiet"),
    "suggestion": ("Suggestion", "idea"),
    "connected": ("Connected", "good"),
    "off": ("Off", "quiet"),
}


def ui_font(px: int, bold: bool = False) -> QFont:
    from deskbuddy.ui.hub import styles

    font = QFont()
    font.setFamilies(list(styles.active().families))
    font.setPixelSize(px)
    font.setWeight(QFont.Weight.DemiBold if bold else QFont.Weight.Normal)
    return font


def verdict_of(line: str) -> str:
    """Which verdict a report line carries. The wording itself stays in the text."""
    if "I couldn't" in line:
        return "couldnt"
    if line.startswith("Done"):
        return "done"
    if line.startswith("Stopped"):
        return "stopped"
    return ""


# ---- time wording --------------------------------------------------------------
def clock(ts: float) -> str:
    moment = datetime.fromtimestamp(ts)
    return f"{moment.hour % 12 or 12}:{moment.minute:02d} {'AM' if moment.hour < 12 else 'PM'}"


def _days_from_today(ts: float) -> int:
    return (datetime.fromtimestamp(ts).date() - datetime.now().date()).days


def day_label(ts: float) -> str:
    delta, moment = _days_from_today(ts), datetime.fromtimestamp(ts)
    names = {0: "Today", -1: "Yesterday", 1: "Tomorrow"}
    return names.get(delta) or f"{moment:%a}, {moment:%b} {moment.day}"


def short_time(ts: float) -> str:
    """Right-hand stamp on a row: the time today, else the day."""
    delta, moment = _days_from_today(ts), datetime.fromtimestamp(ts)
    if delta == 0:
        return clock(ts)
    if delta in (-1, 1):
        return day_label(ts)
    if -6 <= delta <= 6:
        return f"{moment:%A}"
    return f"{moment:%b} {moment.day}"


def when_long(ts: float) -> str:
    return f"{day_label(ts)} at {clock(ts)}"


def stylesheet() -> str:
    """The one stylesheet of the look that is active right now."""
    from deskbuddy.ui.hub import styles

    return styles.active().stylesheet()
