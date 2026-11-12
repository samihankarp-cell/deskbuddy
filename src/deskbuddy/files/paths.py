"""Turning what the user says ("my desktop", "notes.txt") into a real path."""
import os
from pathlib import Path

KNOWN = {
    "desktop": "Desktop", "documents": "Documents", "downloads": "Downloads",
    "pictures": "Pictures", "music": "Music", "videos": "Videos",
}


def known_folder(name: str) -> Path:
    """Desktop, Documents and so on, including when OneDrive has moved them."""
    home = Path.home()
    for base in (home / "OneDrive", home):
        candidate = base / KNOWN[name]
        if candidate.is_dir():
            return candidate
    return home / KNOWN[name]


def resolve(text: str) -> Path:
    raw = os.path.expandvars(os.path.expanduser(str(text).strip().strip('"').strip("'")))
    path = Path(raw)
    if path.is_absolute():
        return path
    parts = path.parts
    if parts and parts[0].lower() in KNOWN:
        return known_folder(parts[0].lower()).joinpath(*parts[1:])
    return known_folder("desktop") / path  # a bare name means "on my desktop"


def protected(path: Path) -> bool:
    """Windows' own folders. Touching them counts as changing Windows settings."""
    roots = [os.environ.get("SystemRoot", r"C:\Windows"), os.environ.get("ProgramFiles", ""),
             os.environ.get("ProgramFiles(x86)", ""), os.environ.get("ProgramData", "")]
    full = str(path.resolve()).lower().rstrip("\\/")
    for root in roots:
        root = root.lower().rstrip("\\/")
        if root and (full == root or full.startswith(root + os.sep)):
            return True
    return False


def important(path: Path) -> bool:
    """Whole places nobody means to delete or move: drive roots, home, Desktop and friends,
    OneDrive, and the folders above them."""
    full = path.resolve()
    if full.parent == full:  # a drive root such as C:\
        return True
    home = Path.home()
    places = [home, home / "OneDrive"]
    for name in KNOWN:
        places += [known_folder(name), home / KNOWN[name], home / "OneDrive" / KNOWN[name]]
    keep = set()
    for place in places:
        place = place.resolve()
        keep.add(str(place).lower())
        keep.update(str(parent).lower() for parent in place.parents)
    return str(full).lower() in keep
