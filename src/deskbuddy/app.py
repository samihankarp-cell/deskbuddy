"""Starts Desk Buddy and connects its parts: window, brain, browser link, ears, routines."""
import sys
import threading
from datetime import datetime

from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtWidgets import QApplication

from deskbuddy import alerts, config
from deskbuddy.state import BuddyState
from deskbuddy.ui.tray import make_tray
from deskbuddy.ui.window import BuddyWindow

OFFER_SECONDS = 60          # an unasked offer goes away by itself after this long
HABIT_CHECK_MS = 60_000
IDEA_CHECK_MS = 10 * 60_000


class Signals(QObject):
    idea = Signal(object)  # an Offer thought up on a background thread


def greeting() -> str:
    hour = datetime.now().hour
    return "Good morning" if hour < 12 else "Good afternoon" if hour < 18 else "Good evening"


def main() -> int:
    from deskbuddy import log

    log.setup()   # first, so a crash while starting up is in the log too
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)  # hiding the robot must not quit the app
    window = BuddyWindow()

    parts: dict = {}  # filled in once the brain is up

    def open_dashboard() -> None:
        if parts.get("dash"):
            parts["dash"].open()
        else:  # only in the first moment, before the brain has started
            window.say("I'm still starting up. One moment.")

    tray = make_tray(app, window, open_dashboard)
    window.dashboard_requested.connect(open_dashboard)
    window.show()

    from deskbuddy.mcpclient import hub as mcp_hub
    from deskbuddy.mcpclient import servers as mcp_servers
    from deskbuddy.memory.db import Memory
    from deskbuddy.ui.dashboard import Dashboard

    config.load_env()   # the Settings page shows what the .env holds
    memory = Memory(config.data_dir() / "memory.db")
    memory.prune()
    problem: dict = {"text": ""}   # why the brain is not running, while it is not

    def submit(text: str) -> None:
        if parts.get("submit"):
            parts["submit"](text)
        else:
            window.set_state(BuddyState.COULDNT)
            window.say(f"I can't do that yet because {problem['text']}. Add it in Settings and press Save.")
            parts["dash"].open_section("Settings")

    dash = Dashboard(memory, submit)
    parts["dash"] = dash
    window.order_submitted.connect(submit)
    mcp_hub.get().apply(mcp_servers.load())   # connects in the background

    def start_brain(settings) -> None:
        from deskbuddy.apps.win import installed_apps
        from deskbuddy.brain import proactive
        from deskbuddy.brain.runner import Runner
        from deskbuddy.browser.bridge import Bridge
        from deskbuddy.voice import hotkey as keys
        from deskbuddy.voice.listen import Listener

        bridge = Bridge(settings.ws_port, settings.data_dir / "paired.json")
        runner = Runner(settings, memory, bridge)
        parts["settings"] = settings
        bridge.approve = runner.ask_user  # a new add-on must be allowed once
        bridge.start()
        threading.Thread(target=installed_apps, daemon=True).start()  # so "not installed" is quick

        # ---- unasked offers (routines and ideas): one at a time, Yes / No ------
        offer: dict = {"yes": None, "no": None, "token": 0}

        def clear_offer() -> None:
            offer["yes"] = offer["no"] = None

        def make_offer(text: str, on_yes, on_no) -> bool:
            if runner.busy or offer["yes"] is not None:
                return False
            memory.add_message("offer", text)
            offer["yes"], offer["no"] = on_yes, on_no
            offer["token"] += 1
            token = offer["token"]
            window.set_state(BuddyState.ASKING)
            window.ask(text)

            def expire() -> None:
                if offer["yes"] is not None and offer["token"] == token:
                    clear_offer()
                    window.set_state(BuddyState.IDLE)
                    window.say("")

            QTimer.singleShot(OFFER_SECONDS * 1000, expire)
            return True

        def on_answer(yes: bool) -> None:
            if offer["yes"] is None:
                runner.answer(yes)  # it was the brain's own safety question
                return
            action = offer["yes"] if yes else offer["no"]
            clear_offer()
            if not yes:
                window.set_state(BuddyState.IDLE)
                window.say("")
            action()

        def on_runner_ask(question: str) -> None:
            clear_offer()  # a safety question always wins over an offer
            window.ask(question)

        parts["submit"] = lambda text: (clear_offer(), runner.submit(text))
        runner.state.connect(dash.set_state)
        runner.say.connect(dash.set_status)
        runner.state.connect(window.set_state)
        runner.say.connect(window.say)
        runner.ask.connect(on_runner_ask)
        window.answered.connect(on_answer)
        window.stop_requested.connect(runner.stop)

        # ---- routines: "you usually ask for this around now" --------------------
        def check_habits() -> None:
            habit = memory.due_habit()
            if habit is None:
                return
            made = make_offer(
                f"{greeting()}. Your usual around now: \"{habit.order[:70]}\". Shall I?",
                lambda: (memory.mark_offered(habit.key, False), runner.submit(habit.order)),
                lambda: memory.mark_offered(habit.key, True),
            )
            if made:
                memory.mark_offered(habit.key, False)  # at most one offer a day per routine

        habit_timer = QTimer()
        habit_timer.timeout.connect(check_habits)
        habit_timer.start(HABIT_CHECK_MS)

        # ---- ideas: now and then, something that fits what they are working on --
        signals = Signals()
        thinking = threading.Event()

        def show_idea(idea) -> None:
            made = make_offer(
                idea.say,
                lambda: (proactive.note_answer(memory, True), runner.open_url(idea.url)),
                lambda: proactive.note_answer(memory, False),
            )
            if made:
                proactive.note_offer_made(memory)

        def check_ideas() -> None:
            if not alerts.alert_on(memory, alerts.SUGGESTIONS):
                return
            if runner.busy or offer["yes"] is not None or thinking.is_set():
                return
            if not proactive.allowed_now(memory):
                return
            thinking.set()

            def work() -> None:
                try:
                    idea = proactive.think_of_offer(settings, memory)
                    if idea is not None:
                        signals.idea.emit(idea)
                finally:
                    thinking.clear()

            threading.Thread(target=work, daemon=True, name="buddy-ideas").start()

        signals.idea.connect(show_idea)
        idea_timer = QTimer()
        idea_timer.timeout.connect(check_ideas)
        idea_timer.start(IDEA_CHECK_MS)

        # ---- reminders ------------------------------------------------------------
        def check_reminders() -> None:
            for text in memory.take_due_reminders():
                memory.add_message("reminder", text)
                if alerts.alert_on(memory, alerts.REMINDER_TOASTS):
                    tray.showMessage("Desk Buddy reminder", text)
                if not runner.busy and offer["yes"] is None:
                    window.set_state(BuddyState.ASKING)
                    window.say(f"Reminder: {text}")

        reminder_timer = QTimer()
        reminder_timer.timeout.connect(check_reminders)
        reminder_timer.start(20_000)

        # ---- ears ---------------------------------------------------------------
        ears = Listener(settings.hotkey, settings.whisper_size)

        def on_listening(active: bool) -> None:
            if active:
                clear_offer()
                runner.stop()  # starting to talk interrupts whatever it is doing
                window.set_state(BuddyState.LISTENING)
                window.say("Listening...")
            elif not runner.busy:
                window.set_state(BuddyState.THINKING)
                window.say("Got it...")

        def on_heard(text: str) -> None:
            window.say(f"\"{text}\"")  # show what was heard, so a mishearing is visible
            runner.submit(text)

        def on_problem(text: str) -> None:
            if not runner.busy:
                window.set_state(BuddyState.COULDNT)
                window.say(text)

        ears.listening.connect(on_listening)
        ears.heard.connect(on_heard)
        ears.problem.connect(on_problem)
        ears.escape.connect(runner.stop)
        parts["ears"] = ears
        ears.start()

        window.set_state(BuddyState.IDLE)
        window.say(f"{greeting()}. Click me to type, or hold {keys.friendly(settings.hotkey)} to talk.")
        QTimer.singleShot(3000, check_habits)
        parts["runner"] = runner


    def apply_settings() -> None:
        """Settings were saved: use them now, with no restart."""
        mcp_hub.get().apply(mcp_servers.load())
        try:
            if parts.get("settings") is None:
                start_brain(config.load())
                dash.settings.say_applied("Saved. I'm up and running.")
                window.set_state(BuddyState.IDLE)
                window.say("Got your settings. Ready when you are.")
                return
            changed = config.reload(parts["settings"])
        except config.ConfigError as error:
            problem["text"] = str(error)
            dash.settings.say_applied(f"Saved, but I can't use it yet: {error}.", ok=False)
            return
        if "hotkey" in changed:
            parts["ears"].set_hotkey(parts["settings"].hotkey)
        later = [config.RESTART_FIELDS[n] for n in changed if n in config.RESTART_FIELDS]
        note = "Saved and applied." if not later else f"Saved and applied. {later[0].capitalize()} changes on restart."
        dash.settings.say_applied(note)

    dash.settings_saved.connect(apply_settings)
    dash.hotkey_changed.connect(lambda name: parts.get("ears") and parts["ears"].set_hotkey(name))

    try:
        start_brain(config.load())
    except config.ConfigError as error:
        # No usable AI key yet: the dashboard still opens, on Settings, so it can be added.
        problem["text"] = str(error)
        window.set_state(BuddyState.COULDNT)
        window.say(f"I couldn't start my brain because {error}. Add it in Settings on the dashboard.")
        return app.exec()
    return app.exec()
