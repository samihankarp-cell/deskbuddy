"""Everything Desk Buddy remembers, in one local SQLite file."""
import sqlite3
import threading
import time
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS messages(id INTEGER PRIMARY KEY, ts REAL, role TEXT, text TEXT);
CREATE TABLE IF NOT EXISTS jobs(id INTEGER PRIMARY KEY, ts REAL, order_text TEXT, title TEXT,
    passed INTEGER, reason TEXT, answer TEXT);
CREATE TABLE IF NOT EXISTS undo(id INTEGER PRIMARY KEY, job_id INTEGER, kind TEXT, a TEXT, b TEXT);
CREATE TABLE IF NOT EXISTS notes(id INTEGER PRIMARY KEY, ts REAL, place TEXT, lesson TEXT);
CREATE TABLE IF NOT EXISTS prefs(id INTEGER PRIMARY KEY, ts REAL, text TEXT);
CREATE TABLE IF NOT EXISTS habit_state(key TEXT PRIMARY KEY, last_day TEXT, declines INTEGER);
CREATE TABLE IF NOT EXISTS kv(key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE IF NOT EXISTS reminders(id INTEGER PRIMARY KEY, due REAL, text TEXT, fired INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS offered(url TEXT PRIMARY KEY, ts REAL);
"""


class Memory:
    def __init__(self, path: Path):
        self._db = sqlite3.connect(str(path), check_same_thread=False)
        self._lock = threading.Lock()
        with self._lock:
            self._db.executescript(SCHEMA)
            self._db.commit()

    def _run(self, sql: str, args: tuple = ()) -> sqlite3.Cursor:
        with self._lock:
            cur = self._db.execute(sql, args)
            self._db.commit()
            return cur

    def _rows(self, sql: str, args: tuple = ()) -> list[tuple]:
        with self._lock:
            return self._db.execute(sql, args).fetchall()

    # ---- conversation --------------------------------------------------
    def add_message(self, role: str, text: str) -> None:
        self._run("INSERT INTO messages(ts,role,text) VALUES(?,?,?)", (time.time(), role, text))

    def recent_messages(self, n: int = 8) -> list[tuple[str, str]]:
        rows = self._rows("SELECT role,text FROM messages ORDER BY id DESC LIMIT ?", (n,))
        return rows[::-1]

    def last_order(self) -> str | None:
        """The most recent real order, skipping 'again' and 'undo' themselves."""
        rows = self._rows(
            "SELECT text FROM messages WHERE role='user' ORDER BY id DESC LIMIT 20"
        )
        from deskbuddy.brain.intake import is_repeat, is_undo

        for (text,) in rows:
            if not is_repeat(text) and not is_undo(text):
                return text
        return None

    # ---- jobs ----------------------------------------------------------
    def start_job(self, order_text: str, title: str) -> int:
        cur = self._run(
            "INSERT INTO jobs(ts,order_text,title) VALUES(?,?,?)", (time.time(), order_text, title)
        )
        return cur.lastrowid

    def finish_job(self, job_id: int, passed: bool, reason: str, answer: str) -> None:
        self._run(
            "UPDATE jobs SET passed=?,reason=?,answer=? WHERE id=?",
            (int(passed), reason, answer, job_id),
        )

    # ---- undo journal --------------------------------------------------
    def add_undo(self, job_id: int, kind: str, a: str, b: str = "") -> None:
        self._run("INSERT INTO undo(job_id,kind,a,b) VALUES(?,?,?,?)", (job_id, kind, a, b))

    def take_last_undo(self, before_job: int) -> list[tuple[str, str, str]]:
        """Entries of the newest job that changed files, newest first. Removes them."""
        row = self._rows("SELECT MAX(job_id) FROM undo WHERE job_id<?", (before_job,))
        if not row or row[0][0] is None:
            return []
        newest = row[0][0]
        # one order can be split into several jobs; undo all of them together
        siblings = self._rows(
            "SELECT b.id FROM jobs a JOIN jobs b ON b.order_text=a.order_text "
            "AND ABS(b.ts-a.ts)<600 WHERE a.id=? AND b.id<?", (newest, before_job))
        ids = [r[0] for r in siblings] or [newest]
        marks = ",".join("?" * len(ids))
        entries = self._rows(
            f"SELECT kind,a,b FROM undo WHERE job_id IN ({marks}) ORDER BY id DESC", tuple(ids))
        self._run(f"DELETE FROM undo WHERE job_id IN ({marks})", tuple(ids))
        return entries

    # ---- notebook of lessons -------------------------------------------
    def add_note(self, place: str, lesson: str) -> None:
        place = place.lower()
        if self._rows("SELECT 1 FROM notes WHERE place=? AND lesson=?", (place, lesson)):
            return
        self._run("INSERT INTO notes(ts,place,lesson) VALUES(?,?,?)", (time.time(), place, lesson))
        # keep the notebook small: only the 6 newest lessons per place
        self._run(
            "DELETE FROM notes WHERE place=? AND id NOT IN "
            "(SELECT id FROM notes WHERE place=? ORDER BY id DESC LIMIT 6)",
            (place, place),
        )

    def notes_for(self, text: str) -> list[str]:
        text = text.lower()
        rows = self._rows("SELECT place,lesson FROM notes ORDER BY id DESC LIMIT 200")
        return [f"[{place}] {lesson}" for place, lesson in rows if place in text][:8]

    # ---- lasting facts about the user ----------------------------------
    MAX_PREFS = 40

    def add_pref(self, text: str) -> None:
        if not text or self._rows("SELECT 1 FROM prefs WHERE text=?", (text,)):
            return
        self._run("INSERT INTO prefs(ts,text) VALUES(?,?)", (time.time(), text[:300]))
        self._run("DELETE FROM prefs WHERE id NOT IN (SELECT id FROM prefs ORDER BY id DESC LIMIT ?)",
                  (self.MAX_PREFS,))

    def remove_pref(self, pref_id: int) -> None:
        self._run("DELETE FROM prefs WHERE id=?", (pref_id,))

    def prefs(self) -> list[tuple[int, str]]:
        return self._rows("SELECT id,text FROM prefs ORDER BY id")

    # ---- small facts the app itself keeps --------------------------------
    def get(self, key: str, default: str = "") -> str:
        rows = self._rows("SELECT value FROM kv WHERE key=?", (key,))
        return rows[0][0] if rows else default

    def set(self, key: str, value: str) -> None:
        self._run("INSERT OR REPLACE INTO kv(key,value) VALUES(?,?)", (key, value))

    def was_offered(self, url: str) -> bool:
        return bool(self._rows("SELECT 1 FROM offered WHERE url=?", (url,)))

    def mark_url_offered(self, url: str) -> None:
        self._run("INSERT OR REPLACE INTO offered(url,ts) VALUES(?,?)", (url, time.time()))

    def recent_orders(self, days: int = 14, limit: int = 15) -> list[str]:
        rows = self._rows(
            "SELECT order_text FROM jobs WHERE passed=1 AND ts>? GROUP BY order_text "
            "ORDER BY MAX(ts) DESC LIMIT ?", (time.time() - days * 86400, limit))
        return [r[0] for r in rows]

    # ---- routines ------------------------------------------------------
    def habits(self):
        from deskbuddy.brain.intake import is_repeat, is_undo
        from deskbuddy.memory.habits import find_habits

        rows = self._rows("SELECT MIN(ts),order_text FROM jobs WHERE passed=1 "
                          "GROUP BY order_text, CAST(ts/600 AS INTEGER)")
        return find_habits([(ts, t) for ts, t in rows if not is_repeat(t) and not is_undo(t)])

    def due_habit(self):
        import difflib
        from datetime import datetime

        from deskbuddy.memory.habits import SAME_ORDER, due_now

        habits = self.habits()
        if not habits:
            return None
        midnight = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
        today = [" ".join(t.lower().split()) for (t,) in
                 self._rows("SELECT order_text FROM jobs WHERE ts>=?", (midnight,))]
        done = {h.key for h in habits
                if any(difflib.SequenceMatcher(None, t, h.key).ratio() >= SAME_ORDER for t in today)}
        state = {k: (d, n) for k, d, n in self._rows("SELECT key,last_day,declines FROM habit_state")}
        return due_now(habits, done, state)

    def mark_offered(self, key: str, declined: bool) -> None:
        from datetime import date

        old = self._rows("SELECT declines FROM habit_state WHERE key=?", (key,))
        declines = ((old[0][0] if old else 0) + 1) if declined else 0
        self._run("INSERT OR REPLACE INTO habit_state(key,last_day,declines) VALUES(?,?,?)",
                  (key, date.today().isoformat(), declines))

    # ---- keeping memory tidy -------------------------------------------
    def prune(self) -> None:
        now = time.time()
        self._run("DELETE FROM messages WHERE id NOT IN (SELECT id FROM messages ORDER BY id DESC LIMIT 400)")
        self._run("DELETE FROM jobs WHERE ts<?", (now - 60 * 86400,))
        self._run("DELETE FROM undo WHERE job_id NOT IN (SELECT id FROM jobs ORDER BY id DESC LIMIT 200)")
        self._run("DELETE FROM notes WHERE ts<?", (now - 90 * 86400,))
        self._run("DELETE FROM offered WHERE ts<?", (now - 60 * 86400,))

    # ---- reminders -----------------------------------------------------
    def add_reminder(self, text: str, due: float) -> int:
        return self._run("INSERT INTO reminders(due,text) VALUES(?,?)", (due, text[:300])).lastrowid

    def reminders(self) -> list[tuple]:
        return self._rows("SELECT id,due,text,fired FROM reminders ORDER BY fired, due LIMIT 100")

    def remove_reminder(self, reminder_id: int) -> None:
        self._run("DELETE FROM reminders WHERE id=?", (reminder_id,))

    def take_due_reminders(self) -> list[str]:
        """Reminders whose time has come. Each is returned once."""
        rows = self._rows("SELECT id,text FROM reminders WHERE fired=0 AND due<=?", (time.time(),))
        for reminder_id, _text in rows:
            self._run("UPDATE reminders SET fired=1 WHERE id=?", (reminder_id,))
        return [text for _id, text in rows]

    # ---- what the dashboard shows ----------------------------------------
    def feed(self, n: int = 40) -> list[tuple]:
        return self._rows("SELECT ts,role,text FROM messages ORDER BY id DESC LIMIT ?", (n,))

    def jobs_recent(self, n: int = 80) -> list[tuple]:
        return self._rows("SELECT ts,title,passed,reason,answer FROM jobs ORDER BY id DESC LIMIT ?", (n,))

    def notes_all(self) -> list[tuple]:
        return self._rows("SELECT id,place,lesson FROM notes ORDER BY id DESC LIMIT 60")

    def remove_note(self, note_id: int) -> None:
        self._run("DELETE FROM notes WHERE id=?", (note_id,))

    def stats(self) -> dict:
        from datetime import datetime

        midnight = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
        one = lambda sql, args=(): self._rows(sql, args)[0][0]  # noqa: E731
        return {
            "done_today": one("SELECT COUNT(*) FROM jobs WHERE passed=1 AND ts>=?", (midnight,)),
            "failed_today": one("SELECT COUNT(*) FROM jobs WHERE passed=0 AND ts>=?", (midnight,)),
            "reminders": one("SELECT COUNT(*) FROM reminders WHERE fired=0"),
            "facts": one("SELECT COUNT(*) FROM prefs"),
        }
