"""Saving settings to the private .env file. Changes apply on the next start.

The dashboard has a Settings page for normal use. SettingsDialog is only the way in when
Desk Buddy cannot start at all (no AI key yet), so there is no dashboard to open.
"""
import os
from pathlib import Path

from dotenv import set_key
from PySide6.QtWidgets import (QDialog, QDialogButtonBox, QFormLayout, QLabel, QLineEdit)

from deskbuddy.config import ROOT

FIELDS = [
    ("DESKBUDDY_HOTKEY", "Hold-to-talk key", False),
    ("DESKBUDDY_API_KEY", "AI key", True),
    ("DESKBUDDY_BASE_URL", "AI address", False),
    ("DESKBUDDY_FAST_MODEL", "Fast model", False),
    ("DESKBUDDY_AGENT_MODEL", "Agent model", False),
    ("COMPOSIO_API_KEY", "Composio key (connectors)", True),
]


def save_env(values: dict[str, str], env_file: Path | None = None) -> None:
    """Write each value into the .env file, creating it if needed."""
    env_file = env_file or ROOT / ".env"
    env_file.touch(exist_ok=True)
    for name, value in values.items():
        set_key(str(env_file), name, value.strip(), quote_mode="never")


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Desk Buddy settings")
        self.setMinimumWidth(460)
        form = QFormLayout(self)
        self._boxes: dict[str, QLineEdit] = {}
        for name, label, secret in FIELDS:
            box = QLineEdit(os.environ.get(name, ""))
            if secret:
                box.setEchoMode(QLineEdit.EchoMode.Password)
            self._boxes[name] = box
            form.addRow(label, box)
        form.addRow(QLabel("Changes take effect the next time Desk Buddy starts."))
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def _save(self) -> None:
        save_env({name: box.text() for name, box in self._boxes.items()})
        self.accept()
