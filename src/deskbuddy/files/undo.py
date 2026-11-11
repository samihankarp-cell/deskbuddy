"""'Undo that': reverse every file change of the most recent job, newest first."""
import shutil
from pathlib import Path

from send2trash import send2trash

from deskbuddy.brain.types import CheckResult, JobResult
from deskbuddy.files import recycle

TITLE = "undo the last file changes"


def _reverse(kind: str, a: str, b: str) -> str | None:
    """Undo one entry. Returns a problem in plain words, or None when it is back."""
    first, second = Path(a), Path(b) if b else None
    if kind == "created":
        if first.exists():
            send2trash(str(first))
        return None if not first.exists() else f"{first.name} is still there"
    if kind == "moved":  # a = where it was, b = where it went
        if not second.exists():
            return f"{second.name} is no longer where I put it"
        if first.exists():
            return f"something else is now at {first}"
        first.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(second), str(first))
        return None if first.exists() else f"{first.name} did not come back"
    if kind == "edited":  # a = the file, b = the saved copy of its old contents
        if not second.exists():
            return f"the saved copy of {first.name} is missing"
        shutil.copy2(str(second), str(first))
        return None if first.read_bytes() == second.read_bytes() else f"{first.name} did not change back"
    if kind == "trashed":
        if first.exists():
            return f"something else is now at {first}"
        return None if recycle.restore(first) else f"{first.name} was not in the Recycle Bin any more"
    return f"I do not know how to undo '{kind}'"


def undo_last(memory, current_job: int) -> JobResult:
    entries = memory.take_last_undo(current_job)
    if not entries:
        return JobResult(TITLE, CheckResult(False, "there is no file change I can undo"))
    problems = []
    for kind, a, b in entries:
        try:
            problem = _reverse(kind, a, b)
        except Exception as error:
            problem = f"{Path(a).name}: {error}"
        if problem:
            problems.append(problem)
    if problems:
        return JobResult(TITLE, CheckResult(False, "; ".join(problems)))
    count = len(entries)
    return JobResult(TITLE, CheckResult(True),
                     summary=f"Put {count} thing{'s' if count != 1 else ''} back the way it was")
