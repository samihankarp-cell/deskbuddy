"""Light / Dark / System: which variant of a look is in force.

The choice is stored in memory as "hub_mode". "system" follows Windows through Qt's colour scheme
(Qt 6.5+); anything Qt cannot tell (an older Qt, a platform that does not say) counts as light."""
from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication

MODE_KEY = "hub_mode"
MODES = ("light", "dark", "system")
DEFAULT_MODE = "system"
LABELS = {"light": "Light", "dark": "Dark", "system": "System"}


def clean(value) -> str:
    """A stored value as a valid mode; anything unknown falls back to System."""
    return value if value in MODES else DEFAULT_MODE


def system_dark() -> bool:
    """Is Windows (the platform) in dark mode right now?"""
    hints = QGuiApplication.styleHints()
    scheme = getattr(hints, "colorScheme", None)
    return bool(scheme and scheme() == Qt.ColorScheme.Dark)


def is_dark(mode: str) -> bool:
    """Whether `mode` means the dark variant right now."""
    mode = clean(mode)
    return system_dark() if mode == "system" else mode == "dark"
