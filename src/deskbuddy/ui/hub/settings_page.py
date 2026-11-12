"""Settings as a page: AI provider, keys and models (saved to .env and applied at once when Save is
pressed), MCP servers (added and removed live) and alert switches (saved in memory, applied at once)."""
import os
from pathlib import Path

from PySide6.QtCore import QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (QFrame, QGridLayout, QHBoxLayout, QLabel, QMenu, QPushButton,
                               QVBoxLayout)

from deskbuddy import alerts, log, providers
from deskbuddy.ui.hub import styles
from deskbuddy.ui.hub.key_capture import KeyCapture
from deskbuddy.ui.hub.look_picker import LookPicker
from deskbuddy.ui.hub.mode_picker import ModePicker
from deskbuddy.ui.hub.styles import modes
from deskbuddy.ui.hub.page import Page, line_edit
from deskbuddy.ui.hub.surface import Surface
from deskbuddy.mcpclient import hub as mcp_hub
from deskbuddy.mcpclient import servers as mcp_servers
from deskbuddy.ui.hub.widgets import Toggle, button, clear, matches, text
from deskbuddy.ui.settings import save_env
from deskbuddy.voice import hotkey as keys

HOTKEY_ENV = "DESKBUDDY_HOTKEY"   # chosen by pressing the key, saved and applied at once
PROVIDER_ENV = "DESKBUDDY_PROVIDER"
PRESET_FIELDS = {"DESKBUDDY_BASE_URL": "base_url", "DESKBUDDY_FAST_MODEL": "fast_model",
                 "DESKBUDDY_AGENT_MODEL": "agent_model"}   # field -> the Provider attribute it follows

# group title -> (env name, label, secret)
GROUPS = {
    "AI": [("DESKBUDDY_API_KEY", "AI key", True), ("DESKBUDDY_BASE_URL", "AI address", False),
           ("DESKBUDDY_FAST_MODEL", "Fast model", False), ("DESKBUDDY_AGENT_MODEL", "Agent model", False)],
    "Voice": [("DESKBUDDY_HOTKEY", "Hold-to-talk key", False)],
    "Connectors": [("COMPOSIO_API_KEY", "Composio key", True)],
}
ALERTS = [
    (alerts.SUGGESTIONS, "Unasked suggestions",
     "Now and then I may offer something that fits what you are working on."),
    (alerts.REMINDER_TOASTS, "Desktop notifications for reminders",
     "Show a Windows notification when a reminder is due."),
]


def _group_card(title: str, search_text: str) -> tuple[Surface, QVBoxLayout]:
    frame = Surface("card")
    frame.setProperty("searchText", f"{title} {search_text}")
    box = QVBoxLayout(frame)
    box.setContentsMargins(16, 14, 16, 16)
    box.setSpacing(10)
    box.addWidget(text(title, "cardTitle", select=False))
    return frame, box


class SettingsPage(Page):
    hotkey_changed = Signal(str)   # a new hold-to-talk key was chosen and saved (keyboard name)
    settings_saved = Signal()      # Save was pressed and the .env file is written: apply it now

    def __init__(self, memory, env_file: Path | None = None, on_look=None, on_mode=None):
        """`on_look(key)` is called when a Look chip is chosen, `on_mode(mode)` when Light / Dark /
        System is (the window applies and stores both)."""
        super().__init__()
        self.memory, self.env_file = memory, env_file
        self.boxes = {}
        self.toggles: dict[str, Toggle] = {}
        self.cards: list[QFrame] = []
        frame, box = _group_card("Look", "Classic Skeuomorphic Spatial style theme appearance "
                                         "mode light dark system night day")
        self.look = LookPicker()
        if on_look:
            self.look.chosen.connect(on_look)
        box.addWidget(self.look)
        mode_row = QHBoxLayout()
        mode_row.setSpacing(14)
        mode_label = text("Mode", "fieldLabel", select=False)
        mode_label.setMinimumWidth(120)   # lines up with the labels of the groups below
        self.mode = ModePicker()
        if on_mode:
            self.mode.chosen.connect(on_mode)
        mode_row.addWidget(mode_label)
        mode_row.addWidget(self.mode)
        mode_row.addStretch(1)
        box.addLayout(mode_row)
        box.addWidget(text("Changes the look at once. Nothing else moves. System follows Windows.",
                           "hint", select=False))
        self.body.addWidget(frame)
        self.cards.append(frame)
        for title, fields in GROUPS.items():
            frame, box = _group_card(title, " ".join(label for _n, label, _s in fields))
            grid = QGridLayout()
            grid.setHorizontalSpacing(14)
            grid.setVerticalSpacing(8)
            grid.setColumnMinimumWidth(0, 120)
            grid.setColumnStretch(1, 1)
            if title == "AI":
                self._provider = (os.environ.get(PROVIDER_ENV, "").strip().lower()
                                  or providers.guess(os.environ.get("DESKBUDDY_BASE_URL", "")))
                grid.addWidget(text("Provider", "fieldLabel", select=False), 0, 0)
                grid.addWidget(self._provider_button(), 0, 1)
            first = 1 if title == "AI" else 0
            for row, (name, label, secret) in enumerate(fields, first):
                grid.addWidget(text(label, "fieldLabel", select=False), row, 0)
                if name == HOTKEY_ENV:
                    grid.addLayout(self._hotkey_row(), row, 1)
                    continue
                preset = (getattr(providers.get(self._provider), PRESET_FIELDS[name], "")
                          if title == "AI" and name in PRESET_FIELDS else "")
                edit = line_edit(secret=secret, value=os.environ.get(name, "") or preset)
                edit.setAccessibleName(label)
                edit.textEdited.connect(self._unsaved)
                self.boxes[name] = edit
                grid.addWidget(edit, row, 1)
            box.addLayout(grid)
            if title == "AI":
                self.provider_hint = text("", "hint", select=False)
                box.addWidget(self.provider_hint)
                self._show_provider_hint()
            self.body.addWidget(frame)
            self.cards.append(frame)
        self._mcp_card()
        frame, box = _group_card("Alerts & updates", " ".join(f"{t} {d}" for _k, t, d in ALERTS))
        for key, title, detail in ALERTS:
            row = QHBoxLayout()
            labels = QVBoxLayout()
            labels.setSpacing(2)
            labels.addWidget(text(title, "fieldLabel", select=False))
            labels.addWidget(text(detail, "hint", select=False))
            toggle = Toggle(title, alerts.alert_on(memory, key))
            toggle.changed.connect(lambda on, k=key: alerts.set_alert(self.memory, k, on))
            self.toggles[key] = toggle
            row.addLayout(labels, 1)
            row.addSpacing(12)
            row.addWidget(toggle)
            box.addLayout(row)
        self.body.addWidget(frame)
        self.cards.append(frame)

        bar = QHBoxLayout()
        self.logs_button = button("Open logs folder", "quiet", self.open_logs)
        bar.addWidget(self.logs_button)
        self.saved = QLabel("")
        self.saved.setObjectName("saved")
        bar.addWidget(self.saved, 1)
        self.save_button = button("Save", "primary", self.save)
        bar.addWidget(self.save_button)
        self.foot.addLayout(bar)

    # ---- AI provider ---------------------------------------------------------------
    def _provider_button(self) -> QPushButton:
        self.provider_button = QPushButton()
        self.provider_button.setObjectName("keyCapture")   # styled like a text field by every look
        self.provider_button.setStyleSheet("text-align: left;")
        self.provider_button.setAccessibleName("Provider")
        self.provider_button.clicked.connect(self._provider_menu)
        self._set_provider_caption()
        return self.provider_button

    def _set_provider_caption(self) -> None:
        self.provider_button.setText(f"{providers.get(self._provider).name}      (click to change)")

    def _provider_menu(self) -> None:
        menu = QMenu(self)
        for item in providers.PROVIDERS:
            menu.addAction(item.name).triggered.connect(lambda _=False, k=item.key: self.choose_provider(k))
        menu.exec(self.provider_button.mapToGlobal(self.provider_button.rect().bottomLeft()))

    def choose_provider(self, key: str) -> None:
        """Pick a provider: its address and model names are filled in (and can still be edited)."""
        self._provider = key
        self._set_provider_caption()
        chosen = providers.get(key)
        if key != providers.CUSTOM:
            for name, attribute in PRESET_FIELDS.items():
                self.boxes[name].setText(getattr(chosen, attribute))
        self._show_provider_hint()
        self._unsaved()

    def _show_provider_hint(self) -> None:
        chosen = providers.get(self._provider)
        if not chosen.needs_key:
            note = "Runs on this PC, so no key is needed. Make sure it is running and the model is installed."
        elif chosen.key_help:
            note = f"Paste your {chosen.name} key. You can make one at {chosen.key_help}."
        else:
            note = "Paste the key and the address your provider gave you."
        self.provider_hint.setText(note + " Model names are suggestions; change them if your account uses others.")

    # ---- MCP servers ---------------------------------------------------------------
    def _mcp_card(self) -> None:
        frame, box = _group_card("MCP servers", "MCP servers Composio tools connect model context protocol "
                                                 "web address command")
        box.addWidget(text("Give Desk Buddy more tools. A server can be a web address (for example your "
                           "Composio MCP address) or a program on this PC. Changes apply at once.",
                           "hint", select=False))
        self.mcp_list = QVBoxLayout()
        self.mcp_list.setSpacing(6)
        box.addLayout(self.mcp_list)
        grid = QGridLayout()
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(8)
        grid.setColumnMinimumWidth(0, 120)
        grid.setColumnStretch(1, 1)
        self.mcp_name = line_edit("composio")
        self.mcp_target = line_edit("https://...  or  npx -y some-server  (or paste the JSON from its docs)")
        self.mcp_extra = line_edit("your key (paste it as is), or  Header: value  /  KEY=value")
        for row, (label, edit) in enumerate([("Name", self.mcp_name), ("Address or command", self.mcp_target),
                                             ("Header or variable", self.mcp_extra)]):
            edit.setAccessibleName(label)
            grid.addWidget(text(label, "fieldLabel", select=False), row, 0)
            grid.addWidget(edit, row, 1)
        box.addLayout(grid)
        bar = QHBoxLayout()
        self.mcp_note = QLabel("")
        self.mcp_note.setObjectName("saved")
        bar.addWidget(self.mcp_note, 1)
        bar.addWidget(button("Add server", "primary", self.add_mcp_server))
        box.addLayout(bar)
        self.body.addWidget(frame)
        self.cards.append(frame)
        self._mcp_shown = None
        self.refresh_mcp()

    def _mcp_say(self, message: str, ok: bool = True) -> None:
        self.mcp_note.setProperty("ok", ok)
        self.mcp_note.style().unpolish(self.mcp_note)
        self.mcp_note.style().polish(self.mcp_note)
        self.mcp_note.setText(message)

    def add_mcp_server(self) -> None:
        try:
            new = mcp_servers.parse(self.mcp_name.text(), self.mcp_target.text(), self.mcp_extra.text())
            current = mcp_servers.add(mcp_servers.load(), new)
            mcp_servers.save(current)
        except mcp_servers.ServerError as error:
            self._mcp_say(f"I can't add that: {error}.", False)
            return
        except OSError as error:
            self._mcp_say(f"I couldn't save: {error.strerror or error}", False)
            return
        mcp_hub.get().apply(current)
        for edit in (self.mcp_name, self.mcp_target, self.mcp_extra):
            edit.clear()
        self._mcp_say("Added " + ", ".join(s.name for s in new) + ". Connecting...")
        self.refresh_mcp()

    def _change_mcp(self, name: str, how: str) -> None:
        current = mcp_servers.load()
        if how == "remove":
            current = [s for s in current if s.name != name]
        else:
            for server in current:
                if server.name == name:
                    server.enabled = not server.enabled
        try:
            mcp_servers.save(current)
        except OSError as error:
            self._mcp_say(f"I couldn't save: {error.strerror or error}", False)
            return
        mcp_hub.get().apply(current)
        self.refresh_mcp()

    def refresh_mcp(self) -> None:
        """Redraw the server list when a name, a status or a tool count differs from what is shown."""
        hub = mcp_hub.get()
        if not hub.configured:        # nothing applied yet in this run: show what the file says
            hub.configured = mcp_servers.load()
        rows = hub.status()
        key = [(s.name, s.target, status, error, count) for s, status, error, count in rows]
        if key == self._mcp_shown:
            return
        self._mcp_shown = key
        clear(self.mcp_list)
        if not rows:
            self.mcp_list.addWidget(text("No servers yet.", "hint", select=False))
        for server, status, error, count in rows:
            row = QHBoxLayout()
            row.setSpacing(8)
            words = {"connected": f"Connected, {count} tool{'s' if count != 1 else ''}",
                     "connecting": "Connecting...", "off": "Off",
                     "failed": f"Couldn't connect: {error}"}[status]
            labels = QVBoxLayout()
            labels.setSpacing(2)
            labels.addWidget(text(server.name, "fieldLabel", select=False))
            labels.addWidget(text(f"{words}  \u00B7  {server.target[:70]}", "hint"))
            row.addLayout(labels, 1)
            if status == "failed":
                row.addWidget(button("Try again", "quiet", lambda n=server.name: hub.retry(n)))
            row.addWidget(button("Turn on" if status == "off" else "Turn off", "quiet",
                                 lambda n=server.name: self._change_mcp(n, "toggle")))
            row.addWidget(button("Remove", "quiet", lambda n=server.name: self._change_mcp(n, "remove")))
            self.mcp_list.addLayout(row)

    def _hotkey_row(self) -> QHBoxLayout:
        """Press-the-key box plus a small Reset. Not in `boxes`: it saves itself when a key is pressed."""
        row = QHBoxLayout()
        row.setSpacing(8)
        self.hotkey = KeyCapture(os.environ.get(HOTKEY_ENV, "") or keys.DEFAULT)
        self.hotkey.picked.connect(self._hotkey_picked)
        self.hotkey.rejected.connect(lambda hint: self._say(hint, False))
        row.addWidget(self.hotkey, 1)
        row.addWidget(button("Reset", "quiet", lambda: self._hotkey_picked(keys.DEFAULT, True)))
        return row

    def _hotkey_picked(self, name: str, reset: bool = False) -> None:
        """Save the key to .env, tell the running Desk Buddy, and say how to use it."""
        if reset:
            self.hotkey.set_key(name)
        try:
            save_env({HOTKEY_ENV: name}, self.env_file)
        except OSError as error:
            self._say(f"I couldn't save: {error.strerror or error}", False)
            return
        os.environ[HOTKEY_ENV] = name   # later screens (and a restart-free reload) read the same key
        self._say(f"Saved. Hold {keys.friendly(name)} to talk.", True)
        self.hotkey_changed.emit(name)

    def open_logs(self) -> None:
        """Show the folder holding deskbuddy.log in Explorer (handy when sending a bug report)."""
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(log.folder())))

    def _unsaved(self, _value: str = "") -> None:
        self.saved.setText("")

    def _say(self, message: str, ok: bool) -> None:
        self.saved.setProperty("ok", ok)   # the look's stylesheet colours it
        self.saved.style().unpolish(self.saved)
        self.saved.style().polish(self.saved)
        self.saved.setText(message)

    def save(self) -> None:
        values = {name: box.text().strip() for name, box in self.boxes.items()}
        values[PROVIDER_ENV] = self._provider
        try:
            save_env(values, self.env_file)
        except OSError as error:
            self._say(f"I couldn't save: {error.strerror or error}", False)
            return
        for name, value in values.items():   # the running app reads the same values at once
            os.environ[name] = value
        self._say("Saved.", True)
        self.settings_saved.emit()           # the app applies them and replaces this line

    def say_applied(self, message: str, ok: bool = True) -> None:
        """What the app did with the saved settings (it may say more than 'Saved.')."""
        self._say(message, ok)

    def fill(self, snap, query: str) -> None:
        self.look.set_current(styles.active().key)
        self.mode.set_current(modes.clean(self.memory.get(modes.MODE_KEY, modes.DEFAULT_MODE)))
        for key, toggle in self.toggles.items():  # follow changes made elsewhere
            toggle.set_quietly(alerts.alert_on(self.memory, key))
        self.refresh_mcp()
        for frame in self.cards:
            frame.setVisible(matches(query, frame.property("searchText")))

    def focus_input(self) -> None:
        next(iter(self.boxes.values())).setFocus()
