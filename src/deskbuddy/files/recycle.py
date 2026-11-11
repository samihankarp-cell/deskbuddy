"""Putting a deleted file back from the Windows Recycle Bin.

Each binned item is a pair: $I<id> holds the original path, $R<id> holds the data.
"""
import shutil
import struct
from pathlib import Path


def _original_path(info_file: Path) -> tuple[str, int] | None:
    try:
        data = info_file.read_bytes()
        version = struct.unpack_from("<q", data, 0)[0]
        deleted_at = struct.unpack_from("<q", data, 16)[0]
        if version == 2:
            length = struct.unpack_from("<i", data, 24)[0]
            raw = data[28:28 + length * 2]
        else:
            raw = data[24:24 + 520]
        return raw.decode("utf-16-le").split("\x00")[0], deleted_at
    except Exception:
        return None


def restore(original: Path) -> bool:
    """Move the newest binned copy of `original` back. True if it is back."""
    bin_root = Path(original.anchor) / "$Recycle.Bin"
    target = str(original).lower()
    best: tuple[int, Path] | None = None
    try:
        user_bins = list(bin_root.iterdir())
    except OSError:
        return False
    for user_bin in user_bins:
        try:
            infos = list(user_bin.glob("$I*"))
        except OSError:
            continue  # another user's bin
        for info in infos:
            found = _original_path(info)
            if found and found[0].lower() == target and (best is None or found[1] > best[0]):
                best = (found[1], info)
    if best is None or original.exists():
        return False
    info = best[1]
    data = info.with_name("$R" + info.name[2:])
    if not data.exists():
        return False
    original.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(data), str(original))
    info.unlink(missing_ok=True)
    return original.exists()
