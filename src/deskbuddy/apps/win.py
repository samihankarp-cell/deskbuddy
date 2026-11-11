"""Small helpers for looking at the windows on screen and the installed apps."""
import ctypes
import json
import subprocess
import threading
from ctypes import wintypes

user32 = ctypes.windll.user32
_apps: list[dict] | None = None
_apps_lock = threading.Lock()


def _title(hwnd: int) -> str:
    buffer = ctypes.create_unicode_buffer(512)
    user32.GetWindowTextW(hwnd, buffer, 512)
    return buffer.value


def windows() -> dict[int, str]:
    """Visible top-level windows that have a title: handle -> title."""
    found: dict[int, str] = {}

    @ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    def visit(hwnd, _lparam):
        if user32.IsWindowVisible(hwnd):
            title = _title(hwnd)
            if title and title != "Desk Buddy":
                found[hwnd] = title
        return True

    user32.EnumWindows(visit, 0)
    return found


def foreground() -> int:
    return user32.GetForegroundWindow()


def foreground_title() -> str:
    return _title(foreground())


def installed_apps(refresh: bool = False) -> list[dict]:
    """Every app in the Start menu: [{'Name': ..., 'AppID': ...}]."""
    global _apps
    with _apps_lock:
        if _apps is None or refresh:
            out = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "[Console]::OutputEncoding=[Text.Encoding]::UTF8; "
                 "Get-StartApps | Select-Object Name,AppID | ConvertTo-Json -Compress"],
                capture_output=True, text=True, encoding="utf-8", timeout=30,
                creationflags=subprocess.CREATE_NO_WINDOW,
            ).stdout.strip()
            data = json.loads(out) if out else []
            _apps = data if isinstance(data, list) else [data]
        return _apps
