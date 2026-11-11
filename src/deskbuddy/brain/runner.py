"""Runs orders on a background thread and tells the window what to show."""
import queue
import threading
from dataclasses import dataclass
from typing import Any, Callable

from PySide6.QtCore import QObject, Signal

from deskbuddy.brain.agent import friendly_error
from deskbuddy.brain.intake import is_repeat, is_undo
from deskbuddy.brain.report import format_report
from deskbuddy.brain.types import CheckResult, JobResult
from deskbuddy.state import BuddyState

CONFIRM_TIMEOUT = 180  # seconds to wait for Yes / No before treating it as No


@dataclass
class Deps:
    settings: Any
    memory: Any
    bridge: Any
    step: Callable[[str], None]
    confirm: Callable[[str], bool]
    stopped: Callable[[], bool]


class Runner(QObject):
    state = Signal(object)   # BuddyState
    say = Signal(str)        # bubble text
    ask = Signal(str)        # Yes / No question

    def __init__(self, settings, memory, bridge):
        super().__init__()
        self._orders: queue.Queue[str] = queue.Queue()
        self._busy = False
        self._stop = threading.Event()
        self._answer = threading.Event()
        self._answer_value = False
        self._ask_lock = threading.Lock()
        self._asking = False
        self.deps = Deps(settings, memory, bridge, self._step, self._confirm, self._stop.is_set)
        self._graph = None
        threading.Thread(target=self._loop, daemon=True, name="buddy-brain").start()

    # ---- called from the window (UI thread) -----------------------------
    def submit(self, order: str) -> None:
        order = order.strip()
        if not order:
            return
        if self._busy:
            # a new order interrupts: stop the current job and drop anything waiting
            self._stop.set()
            self._answer_value = False
            self._answer.set()
            while not self._orders.empty():
                try:
                    self._orders.get_nowait()
                except queue.Empty:
                    break
            self.state.emit(BuddyState.THINKING)
            self.say.emit("Stopping that. On it.")
        else:
            self.state.emit(BuddyState.THINKING)
            self.say.emit("On it.")
        self._orders.put(order)

    def answer(self, yes: bool) -> None:
        self._answer_value = yes
        self._answer.set()

    def stop(self) -> None:
        if self._busy:
            self._stop.set()
            self._answer_value = False
            self._answer.set()

    @property
    def busy(self) -> bool:
        return self._busy

    # ---- called from job threads ----------------------------------------
    def _step(self, label: str) -> None:
        if self._asking or self._stop.is_set():  # keep a question, or the interruption, on show
            return
        self.state.emit(BuddyState.WORKING)
        self.say.emit(label)

    def _confirm(self, question: str) -> bool:
        with self._ask_lock:  # one question on screen at a time
            if self._stop.is_set():
                return False
            self._answer.clear()
            self._asking = True
            self.state.emit(BuddyState.ASKING)
            self.ask.emit(question)
            answered = self._answer.wait(CONFIRM_TIMEOUT)
            self._asking = False
            self.state.emit(BuddyState.WORKING)
            return answered and self._answer_value

    # ---- the worker ------------------------------------------------------
    def _loop(self) -> None:
        while True:
            order = self._orders.get()
            self._busy = True
            self._stop.clear()
            try:
                results = self._run(order)
            except Exception as error:
                results = [JobResult(order, CheckResult(False, friendly_error(error)))]
            report = format_report(results)
            if self._stop.is_set() and self._orders.qsize() > 0:
                # interrupted by a newer order: note it quietly and move straight on
                self.deps.memory.add_message("buddy", f"Stopped: {order[:120]}")
                continue
            self.deps.memory.add_message("buddy", report)
            ok = bool(results) and all(r.check.passed for r in results)
            self.state.emit(BuddyState.DONE if ok else BuddyState.COULDNT)
            self.say.emit(report)
            self._busy = self._orders.qsize() > 0

    def _run(self, order: str) -> list[JobResult]:
        memory = self.deps.memory
        if is_repeat(order):
            previous = memory.last_order()
            memory.add_message("user", order)
            if not previous:
                return [JobResult("do that again", CheckResult(False, "there is nothing earlier to repeat"))]
            self._step(f"Again: {previous[:60]}")
            order = previous
        else:
            memory.add_message("user", order)
        if is_undo(order):
            from deskbuddy.files.undo import undo_last

            self._step("Undoing that")
            job_id = memory.start_job(order, "undo the last file changes")
            result = undo_last(memory, job_id)
            memory.finish_job(job_id, result.check.passed, result.check.reason, "")
            return [result]
        if self._graph is None:
            from deskbuddy.brain.graph import build_graph

            self._graph = build_graph(self.deps)
        state = self._graph.invoke({"order": order, "results": []})
        return state.get("results", [])
