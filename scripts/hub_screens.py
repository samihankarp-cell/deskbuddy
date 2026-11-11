"""Save a 1180x760 screenshot of every dashboard section, using made-up sample data.

    uv run python scripts/hub_screens.py <output folder> [classic|skeuo|spatial|all] [light|dark|both]

With a look and one mode the pictures go straight into <output folder>. With "all" looks, or
mode "both", they go into <output folder>/<look>-<mode>/ for every look x mode asked for (so
"all" alone renders all six variants). Defaults: classic, light, into the folder.

Nothing is read from or written to your real memory or .env: it all lives in a temp folder.
"""
import os
import sys
import tempfile
import time
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.pop("COMPOSIO_API_KEY", None)

from PySide6.QtCore import QCoreApplication  # noqa: E402
from PySide6.QtGui import QFontDatabase  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from deskbuddy.memory.db import Memory  # noqa: E402
from deskbuddy.state import BuddyState  # noqa: E402
from deskbuddy.ui.hub import manage_pages, styles  # noqa: E402
from deskbuddy.ui.hub.window import Dashboard  # noqa: E402

MIN = 60.0
HOUR = 3600.0


def message(memory: Memory, ago: float, role: str, text: str) -> None:
    memory._run("INSERT INTO messages(ts,role,text) VALUES(?,?,?)", (time.time() - ago, role, text))


JOBS: list[tuple] = []


def job(memory: Memory, ago: float, order: str, title: str, passed, reason: str = "", answer: str = "") -> None:
    """Queued, then written oldest first by flush_jobs, so ids run in time order like real data."""
    JOBS.append((time.time() - ago, order, title, None if passed is None else int(passed), reason, answer))


def flush_jobs(memory: Memory) -> None:
    for row in sorted(JOBS):
        memory._run("INSERT INTO jobs(ts,order_text,title,passed,reason,answer) VALUES(?,?,?,?,?,?)", row)


def seed(memory: Memory) -> None:
    day = 24 * HOUR
    # the feed: orders, verdicts, a fired reminder, an unasked suggestion
    message(memory, 2 * day + 3 * HOUR, "user", "Open Gmail and tell me if anything needs me")
    message(memory, 2 * day + 3 * HOUR - 40, "buddy",
            "Done: checked Gmail. Two emails need you: a reply from Northwind about your interview, "
            "and a bill due Friday.")
    message(memory, day + 2 * HOUR, "user", "Make a folder called Old on my desktop and move notes.txt into it")
    message(memory, day + 2 * HOUR - 30, "buddy", "Done: made the folder Old and moved notes.txt into it.")
    message(memory, 5 * HOUR, "offer", "A new junior developer role at Lumen Labs was posted today. Shall I open it?")
    message(memory, 3 * HOUR, "user", "Remember that job application replies are my important emails")
    message(memory, 3 * HOUR - 20, "buddy", "Done: I will remember that.")
    message(memory, 90 * MIN, "reminder", "Submit the internship form")
    message(memory, 40 * MIN, "user", "Play Suna Suna by Shreya Ghoshal on YouTube")
    message(memory, 40 * MIN - 25, "buddy",
            "I couldn't: play Suna Suna on YouTube, because YouTube asked me to sign in and I never "
            "type passwords.")
    message(memory, 12 * MIN, "user", "Open Notepad and type hello")
    message(memory, 12 * MIN - 10, "buddy", "Done: opened Notepad and typed hello.")
    # a habit: the same order at about 8 PM on four days, then the jobs behind the feed
    midnight = time.mktime(time.localtime()[:3] + (0, 0, 0, 0, 0, -1))
    for back in (5, 3, 2, 1):
        job(memory, time.time() - (midnight - back * day + 20 * HOUR + back * 60), "Play Suna Suna by Shreya Ghoshal",
            "play Suna Suna on YouTube", True)
    job(memory, 2 * day + 3 * HOUR, "Open Gmail", "check Gmail", True, answer="Two emails need you.")
    job(memory, day + 2 * HOUR, "Make a folder", "make a folder called Old and move notes.txt", True)
    job(memory, 40 * MIN, "Play Suna Suna", "play Suna Suna on YouTube", False,
        "YouTube asked me to sign in and I never type passwords")
    job(memory, 12 * MIN, "Open Notepad", "open Notepad and type hello", True)
    job(memory, 2 * MIN, "Find a flight", "look up flights to Pune on Friday", None)
    flush_jobs(memory)
    # reminders: two waiting, one already shown
    memory.add_reminder("Call mom", time.time() + 20 * HOUR)
    memory.add_reminder("Pay the phone bill", time.time() + 3 * HOUR)
    shown = memory.add_reminder("Stand up and stretch", time.time() - 2 * HOUR)
    memory._run("UPDATE reminders SET fired=1 WHERE id=?", (shown,))
    # facts and a lesson
    for fact in ("Job application replies are my important emails", "I use the Comet browser",
                 "Call me Sam"):
        memory.add_pref(fact)
    memory.add_note("youtube", "The search box needs a click before typing, or the text is lost.")


def load_fonts() -> None:
    """The offscreen platform may know no fonts at all; borrow the Windows ones if present."""
    for name in ("segoeui.ttf", "segoeuib.ttf", "seguisb.ttf", "arial.ttf", "arialbd.ttf"):
        path = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts" / name
        if path.exists():
            QFontDatabase.addApplicationFont(str(path))


def settle(widget, focus=None) -> None:
    for _ in range(5):
        QCoreApplication.processEvents()
        QTest.qWait(60)
    if QApplication.focusWidget():
        QApplication.focusWidget().clearFocus()  # no stray focus ring in the pictures
    if focus is not None:
        focus.setFocus()
        QCoreApplication.processEvents()


def main(out: Path, look: str = "classic", mode: str = "light") -> None:
    out.mkdir(parents=True, exist_ok=True)
    app = QApplication.instance() or QApplication(sys.argv)
    load_fonts()
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        memory = Memory(Path(tmp) / "memory.db")
        seed(memory)
        memory.set("updates_seen", str(time.time() - 4 * HOUR))
        os.environ.update(DESKBUDDY_API_KEY="sample-key", DESKBUDDY_BASE_URL="https://api.example.com/v1",
                          DESKBUDDY_FAST_MODEL="small-fast-model", DESKBUDDY_AGENT_MODEL="large-agent-model",
                          DESKBUDDY_HOTKEY="right ctrl")
        memory.set("hub_style", look)
        memory.set("hub_mode", mode)   # light or dark, so the picture never depends on this PC
        dash = Dashboard(memory, lambda text: None, env_file=Path(tmp) / ".env")
        dash.resize(1180, 760)
        dash.set_state(BuddyState.WORKING)
        dash.set_status("Looking up flights to Pune")
        dash.show_section("Activity")  # away from Updates, so its blue dot shows
        dash.open()
        settle(dash)
        shots = [("Updates", "1-updates"), ("Activity", "2-activity"), ("Reminders", "3-reminders"),
                 ("Memory", "4-memory"), ("Connectors", "5-connectors-off"), ("Settings", "6-settings")]
        dash.grab().save(str(out / "0-unread-dot.png"))
        for name, stem in shots:
            dash.show_section(name)
            settle(dash, dash.updates.composer.edit if name == "Updates" else None)
            dash.grab().save(str(out / f"{stem}.png"))
        # Connectors with the service connected
        os.environ["COMPOSIO_API_KEY"] = "sample"
        manage_pages.fetch_connected = lambda: ["gmail", "slack"]
        dash.show_section("Connectors")
        settle(dash)
        dash.grab().save(str(out / "5-connectors-on.png"))
        # a search, and the right panel folded away
        dash.show_section("Updates")
        dash.sidebar.search.setText("gmail")
        settle(dash)
        dash.grab().save(str(out / "7-search.png"))
        dash.sidebar.search.clear()
        dash.set_right_open(False)
        settle(dash)
        dash.grab().save(str(out / "8-panel-closed.png"))
        dash.set_right_open(True)
        dash.close()
        memory._db.close()
    print(f"Saved {look}-{mode} screenshots to {out}")


def run(folder: Path, choice: str = "classic", mode_choice: str = "") -> None:
    looks = list(styles.ORDER) if choice == "all" else [choice]
    modes = ["light", "dark"] if (mode_choice == "both" or (choice == "all" and not mode_choice))         else [mode_choice or "light"]
    nested = choice == "all" or len(modes) > 1
    for name in looks:
        for mode in modes:
            main(folder / f"{name}-{mode}" if nested else folder, name, mode)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit("usage: hub_screens.py <output folder> [classic|skeuo|spatial|all] [light|dark|both]")
    choice = sys.argv[2] if len(sys.argv) > 2 else "classic"
    mode_choice = sys.argv[3] if len(sys.argv) > 3 else ""
    if choice != "all" and choice not in styles.STYLES:
        raise SystemExit(f"unknown style {choice!r}; choose from {', '.join(styles.ORDER)} or all")
    if mode_choice not in ("", "light", "dark", "both"):
        raise SystemExit(f"unknown mode {mode_choice!r}; choose light, dark or both")
    run(Path(sys.argv[1]), choice, mode_choice)
