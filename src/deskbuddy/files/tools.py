"""File and folder tools. Each one re-reads the disk before it reports success."""
import shutil
import time
from pathlib import Path

from send2trash import send2trash

from deskbuddy.brain.tools import Ctx, Outcome, tool
from deskbuddy.files.paths import important, protected, resolve

READ_LIMIT = 6000
PATH = "string: a full path, or a name inside Desktop / Documents / Downloads, e.g. 'Desktop/notes.txt'"


def _windows_risk(*keys):
    def risk(_ctx: Ctx, args: dict) -> str | None:
        for key in keys:
            if args.get(key) and protected(resolve(args[key])):
                return f"change something inside Windows' own folders ({resolve(args[key])})"
        return None

    return risk


def _refuse(text, verb: str) -> Outcome | None:
    """Never touch a whole important folder, and never guess when no path was given."""
    if not str(text or "").strip():
        return Outcome(False, f"I need to know which file or folder to {verb}, and none was given")
    target = resolve(text)
    if important(target):
        return Outcome(False, f"I won't {verb} your whole {target.name or target} folder")
    return None


def _name(args: dict, key: str = "path") -> str:
    return Path(str(args.get(key, ""))).name or "it"


@tool("file_list", "List what is inside a folder.", {"path": PATH},
      label=lambda a: f"Looking in {_name(a)}", reads_only=True)
def file_list(ctx: Ctx, path: str) -> Outcome:
    folder = resolve(path)
    if not folder.is_dir():
        return Outcome(False, f"There is no folder at {folder}")
    items = sorted(folder.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))[:200]
    lines = [f"{'[folder]' if p.is_dir() else '[file]'} {p.name}" for p in items]
    return Outcome(True, f"{folder}:\n" + ("\n".join(lines) or "(empty)"), verified=True)


@tool("file_read", "Read a text file.", {"path": PATH},
      label=lambda a: f"Reading {_name(a)}", reads_only=True)
def file_read(ctx: Ctx, path: str) -> Outcome:
    target = resolve(path)
    if not target.is_file():
        return Outcome(False, f"There is no file at {target}")
    text = target.read_text(encoding="utf-8", errors="replace")
    more = "" if len(text) <= READ_LIMIT else f"\n...(cut, {len(text)} characters in total)"
    return Outcome(True, text[:READ_LIMIT] + more, verified=True)


@tool("file_write", "Create a text file, or replace the whole contents of an existing one. "
      "To edit a file: file_read it, then file_write the full new text.",
      {"path": PATH, "content": "string: the complete text of the file"},
      label=lambda a: f"Writing {_name(a)}", risk=_windows_risk("path"))
def file_write(ctx: Ctx, path: str, content: str) -> Outcome:
    if refused := _refuse(path, "overwrite"):
        return refused
    target = resolve(path)
    if target.is_dir():
        return Outcome(False, f"{target} is a folder, not a file")
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        backups = ctx.settings.data_dir / "backups"
        backups.mkdir(exist_ok=True)
        saved = backups / f"{int(time.time() * 1000)}_{target.name}"
        shutil.copy2(target, saved)
        ctx.memory.add_undo(ctx.job_id, "edited", str(target), str(saved))
        verb = "Changed"
    else:
        ctx.memory.add_undo(ctx.job_id, "created", str(target))
        verb = "Created"
    target.write_text(content, encoding="utf-8")
    same = target.read_text(encoding="utf-8") == content
    return Outcome(same, f"{verb} {target}" if same else f"{target} does not hold the new text", same)


@tool("folder_create", "Create a folder.", {"path": PATH},
      label=lambda a: f"Making folder {_name(a)}", risk=_windows_risk("path"))
def folder_create(ctx: Ctx, path: str) -> Outcome:
    target = resolve(path)
    if target.is_dir():
        return Outcome(True, f"{target} already exists", verified=True)
    if target.exists():
        return Outcome(False, f"A file with that name already exists at {target}")
    target.mkdir(parents=True)
    ctx.memory.add_undo(ctx.job_id, "created", str(target))
    return Outcome(target.is_dir(), f"Created folder {target}", target.is_dir())


def _destination(source: Path, destination: str) -> Path:
    target = resolve(destination)
    return target / source.name if target.is_dir() else target


@tool("file_move", "Move or rename a file or folder. Never overwrites.",
      {"source": PATH, "destination": "string: the new path, or a folder to move it into"},
      label=lambda a: f"Moving {_name(a, 'source')}", risk=_windows_risk("source", "destination"))
def file_move(ctx: Ctx, source: str, destination: str) -> Outcome:
    if refused := _refuse(source, "move"):
        return refused
    src = resolve(source)
    if not src.exists():
        return Outcome(False, f"There is nothing at {src}")
    dst = _destination(src, destination)
    if dst.exists():
        return Outcome(False, f"{dst} already exists, and I never overwrite")
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src), str(dst))
    ctx.memory.add_undo(ctx.job_id, "moved", str(src), str(dst))
    good = dst.exists() and not src.exists()
    return Outcome(good, f"Moved {src} to {dst}" if good else "The move did not complete", good)


@tool("file_copy", "Copy a file or folder. Never overwrites.",
      {"source": PATH, "destination": "string: the new path, or a folder to copy it into"},
      label=lambda a: f"Copying {_name(a, 'source')}", risk=_windows_risk("destination"))
def file_copy(ctx: Ctx, source: str, destination: str) -> Outcome:
    src = resolve(source)
    if not src.exists():
        return Outcome(False, f"There is nothing at {src}")
    dst = _destination(src, destination)
    if dst.exists():
        return Outcome(False, f"{dst} already exists, and I never overwrite")
    dst.parent.mkdir(parents=True, exist_ok=True)
    if src.is_dir():
        shutil.copytree(src, dst)
    else:
        shutil.copy2(src, dst)
    ctx.memory.add_undo(ctx.job_id, "created", str(dst))
    return Outcome(dst.exists(), f"Copied {src} to {dst}", dst.exists())


@tool("file_delete", "Delete a file or folder by sending it to the Recycle Bin.", {"path": PATH},
      label=lambda a: f"Binning {_name(a)}", risk=_windows_risk("path"))
def file_delete(ctx: Ctx, path: str) -> Outcome:
    if refused := _refuse(path, "delete"):
        return refused
    target = resolve(path)
    if not target.exists():
        return Outcome(False, f"There is nothing at {target}")
    send2trash(str(target))
    ctx.memory.add_undo(ctx.job_id, "trashed", str(target))
    gone = not target.exists()
    return Outcome(gone, f"Sent {target} to the Recycle Bin" if gone else "It is still there", gone)


@tool("file_delete_forever", "Delete permanently, skipping the Recycle Bin. Only when the "
      "user clearly asked for permanent deletion.", {"path": PATH},
      label=lambda a: f"Deleting {_name(a)} for good",
      # no question when the tool will refuse anyway (an important folder, or no path)
      risk=lambda _c, a: None if _refuse(a.get("path"), "delete") else
      f"delete {resolve(a.get('path', ''))} permanently (this cannot be undone)")
def file_delete_forever(ctx: Ctx, path: str) -> Outcome:
    if refused := _refuse(path, "delete"):
        return refused
    target = resolve(path)
    if not target.exists():
        return Outcome(False, f"There is nothing at {target}")
    if target.is_dir():
        shutil.rmtree(target)
    else:
        target.unlink()
    gone = not target.exists()
    return Outcome(gone, f"Permanently deleted {target}" if gone else "It is still there", gone)


@tool("undo_last_changes", "Put back the file changes of the most recent earlier job "
      "(use when the user asks to undo something you did to files).", {},
      label=lambda a: "Undoing that")
def undo_last_changes(ctx: Ctx) -> Outcome:
    from deskbuddy.files.undo import undo_last

    result = undo_last(ctx.memory, ctx.job_id)
    if result.check.passed:
        return Outcome(True, result.summary, verified=True)
    return Outcome(False, result.check.reason)
