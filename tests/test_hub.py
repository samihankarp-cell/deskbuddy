"""The dashboard (hub): sections, reminders, memory, settings, composer, unread dot, search."""
import time

import pytest
from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QGuiApplication, QPainter, QPixmap, QShortcut
from PySide6.QtWidgets import QFrame, QLabel, QPushButton

from deskbuddy import alerts
from deskbuddy.memory.db import Memory
from deskbuddy.state import BuddyState
from deskbuddy.ui.hub import manage_pages, styles, theme
from deskbuddy.ui.hub.styles import base
from deskbuddy.ui.hub.window import SEEN_KEY, Dashboard, unread_count


@pytest.fixture
def memory(tmp_path):
    mem = Memory(tmp_path / "memory.db")
    yield mem
    mem._db.close()


@pytest.fixture(autouse=True)
def classic_again():
    """The active look is process-wide; leave it as it was found. Windows' own light / dark choice
    must not change what these tests see (the mode defaults to System), so the colour scheme is
    pinned to light for each test and handed back to the system afterwards."""
    hints = QGuiApplication.styleHints()
    if hasattr(hints, "setColorScheme"):
        hints.setColorScheme(Qt.ColorScheme.Light)
    yield
    styles.set_active("classic")
    if hasattr(hints, "setColorScheme"):
        hints.setColorScheme(Qt.ColorScheme.Unknown)


@pytest.fixture
def dash(qtbot, memory, tmp_path, monkeypatch):
    monkeypatch.delenv("COMPOSIO_API_KEY", raising=False)
    orders: list[str] = []
    window = Dashboard(memory, orders.append, env_file=tmp_path / ".env")
    qtbot.addWidget(window)
    window.orders = orders
    window.show()
    window.refresh()
    return window


def labels(widget) -> list[str]:
    return [label.text() for label in widget.findChildren(QLabel)]


def card_titles(page) -> list[str]:
    return [label.text() for label in page.findChildren(QLabel)
            if label.objectName() in ("cardTitle", "cardTitleFaded")]


def click(qtbot, page, caption: str) -> None:
    button = next(b for b in page.findChildren(QPushButton) if b.text() == caption)
    qtbot.mouseClick(button, Qt.MouseButton.LeftButton)


def later(memory, role, text):
    """Add a message with a clearly newer timestamp than the last one."""
    time.sleep(0.03)
    memory.add_message(role, text)


def add_job(memory, ts, order, passed=1):
    memory._run("INSERT INTO jobs(ts,order_text,title,passed,reason,answer) VALUES(?,?,?,?,?,?)",
                (ts, order, order, passed, "", ""))


# ---- sections --------------------------------------------------------------------
def test_every_section_opens_and_is_marked(dash):
    assert theme.NAMES == ["Updates", "Activity", "Reminders", "Memory", "Connectors", "Settings"]
    for name in theme.NAMES:
        dash.show_section(name)
        assert dash.stack.currentWidget() is dash.pages[name]
        assert dash.header_title.text() == name
        assert dash.sidebar.rows[name].isChecked()
    assert dash.open_section("settings") and dash.current == "Settings"
    assert not dash.open_section("nonsense")


def test_old_import_path_still_works():
    from deskbuddy.ui.dashboard import Dashboard as Old

    assert Old is Dashboard


def test_keyboard_shortcuts_switch_sections_and_focus_search(dash):
    shortcuts = {s.key().toString(): s for s in dash.findChildren(QShortcut)}
    shortcuts["Ctrl+4"].activated.emit()
    assert dash.current == "Memory"
    shortcuts["Ctrl+6"].activated.emit()
    assert dash.current == "Settings"
    shortcuts["Ctrl+K"].activated.emit()
    assert dash.focusWidget() is dash.sidebar.search


def test_escape_clears_the_search_box(qtbot, dash):
    dash.sidebar.search.setText("gmail")
    qtbot.keyClick(dash.sidebar.search, Qt.Key.Key_Escape)
    assert dash.sidebar.search.text() == ""


def test_status_and_state_reach_the_right_panel(dash):
    dash.set_status("Opening YouTube\nsecond line")
    dash.set_state(BuddyState.WORKING)
    assert dash.right.status.text() == "Opening YouTube"
    assert dash.right.kettle.state is BuddyState.WORKING


# ---- reminders -------------------------------------------------------------------
def test_reminder_needs_text_and_a_future_time(dash, memory):
    dash.show_section("Reminders")
    page = dash.reminders
    page.add()  # no text
    assert not page.error.isHidden() and "Write what" in page.error.text()
    page.what.setText("Call mom")
    page.when.setDateTime(page.when.dateTime().addDays(-2))
    page.add()  # time already passed
    assert "already passed" in page.error.text()
    assert memory.reminders() == []


def test_add_and_remove_a_reminder(qtbot, dash, memory):
    dash.show_section("Reminders")
    dash.reminders.what.setText("  Call mom  ")
    dash.reminders.add()
    assert [r[2] for r in memory.reminders()] == ["Call mom"]
    assert dash.reminders.what.text() == ""
    assert "Call mom" in card_titles(dash.reminders)
    assert "Call mom" in labels(dash.right)  # also listed under Routines
    click(qtbot, dash.reminders, "Remove")
    assert memory.reminders() == []
    assert "Call mom" not in card_titles(dash.reminders)


def test_shown_reminders_stay_listed_faded_and_marked(dash, memory):
    memory.add_reminder("Stretch", time.time() - 5)
    assert memory.take_due_reminders() == ["Stretch"]
    dash.show_section("Reminders")
    faded = [l for l in dash.reminders.findChildren(QLabel) if l.objectName() == "cardTitleFaded"]
    assert [l.text() for l in faded] == ["Stretch"]
    assert "Shown" in labels(dash.reminders)
    assert "Already shown" in labels(dash.reminders)


# ---- memory ----------------------------------------------------------------------
def test_add_and_forget_a_fact(qtbot, dash, memory):
    dash.show_section("Memory")
    page = dash.memory_page
    page.remember()  # empty
    assert not page.error.isHidden()
    page.fact.setText("I like green tea")
    page.remember()
    assert [t for _i, t in memory.prefs()] == ["I like green tea"]
    assert "I like green tea" in card_titles(page)
    click(qtbot, page, "Forget")
    assert memory.prefs() == []
    assert "I like green tea" not in card_titles(page)


def test_lessons_can_be_forgotten_and_habits_are_listed(qtbot, dash, memory):
    memory.add_note("youtube", "Click the box before typing")
    midnight = time.mktime(time.localtime()[:3] + (0, 0, 0, 0, 0, -1))
    for back in (1, 2, 3):  # the same order at 8 PM on three days
        add_job(memory, midnight - back * 86400 + 20 * 3600, "play suna suna on youtube")
    dash.show_section("Memory")
    dash.refresh()
    assert "Click the box before typing" in card_titles(dash.memory_page)
    assert any("Around 8:00 PM" in text and "seen on 3 days" in text for text in labels(dash.memory_page))
    assert any("seen on 3 days" in text for text in labels(dash.right))
    click(qtbot, dash.memory_page, "Forget")
    assert memory.notes_all() == []


# ---- settings --------------------------------------------------------------------
def test_alert_toggles_apply_instantly(dash, memory):
    dash.show_section("Settings")
    toggle = dash.settings.toggles[alerts.SUGGESTIONS]
    assert toggle.isChecked() and alerts.alert_on(memory, alerts.SUGGESTIONS)  # default on
    toggle.click()
    assert memory.get("alert_suggestions") == "0" and not alerts.alert_on(memory, alerts.SUGGESTIONS)
    dash.settings.toggles[alerts.REMINDER_TOASTS].click()
    assert memory.get("alert_reminder_toasts") == "0"
    toggle.click()
    assert memory.get("alert_suggestions") == "1"


def test_toggles_follow_changes_made_elsewhere(dash, memory):
    dash.show_section("Settings")
    memory.set("alert_reminder_toasts", "0")
    dash.refresh()
    assert not dash.settings.toggles[alerts.REMINDER_TOASTS].isChecked()


def test_save_writes_env_and_applies_without_restart(dash, tmp_path):
    dash.show_section("Settings")
    page = dash.settings
    page.boxes["COMPOSIO_API_KEY"].setText("abc123")
    assert page.boxes["DESKBUDDY_API_KEY"].echoMode().name == "Password"
    assert page.boxes["COMPOSIO_API_KEY"].echoMode().name == "Password"
    page.save()
    env = (tmp_path / ".env").read_text()
    assert "COMPOSIO_API_KEY=abc123" in env and "DESKBUDDY_HOTKEY" not in env  # the key saves itself
    assert page.saved.text() == "Saved."   # the app replaces this with what it applied
    assert "DESKBUDDY_PROVIDER=nvidia" in env
    page.boxes["COMPOSIO_API_KEY"].textEdited.emit("abc1234")  # editing again clears the notice
    assert page.saved.text() == ""


def test_settings_search_hides_other_groups(dash):
    dash.show_section("Settings")
    dash.sidebar.search.setText("composio")
    visible = [c for c in dash.settings.cards if not c.isHidden()]
    titles = {c.property("searchText").split()[0] for c in visible}
    assert titles == {"Connectors", "MCP"}   # the Composio key group and the MCP servers group


# ---- connectors ------------------------------------------------------------------
def test_connectors_off_card_opens_settings(qtbot, dash):
    dash.show_section("Connectors")
    assert "Connectors are off" in card_titles(dash.connectors)
    click(qtbot, dash.connectors, "Open Settings")
    assert dash.current == "Settings"


def test_connectors_show_connected_and_connect_button(qtbot, dash, monkeypatch):
    monkeypatch.setenv("COMPOSIO_API_KEY", "key")
    monkeypatch.setattr(manage_pages, "fetch_connected", lambda: ["gmail"])
    dash.show_section("Connectors")
    qtbot.waitUntil(lambda: dash.connectors.result == ["gmail"])
    assert "Connected" in labels(dash.connectors)
    click(qtbot, dash.connectors, "Connect")  # first not-connected app: Google Drive
    assert dash.orders == ["Connect my Google Drive account"]


def test_connectors_error_offers_try_again(qtbot, dash, monkeypatch):
    monkeypatch.setenv("COMPOSIO_API_KEY", "key")

    def boom():
        raise RuntimeError("no network")

    monkeypatch.setattr(manage_pages, "fetch_connected", boom)
    dash.show_section("Connectors")
    qtbot.waitUntil(lambda: dash.connectors.result == "no network")
    assert "I couldn't reach Composio" in card_titles(dash.connectors)
    monkeypatch.setattr(manage_pages, "fetch_connected", lambda: ["slack"])
    click(qtbot, dash.connectors, "Try again")
    qtbot.waitUntil(lambda: dash.connectors.result == ["slack"])


# ---- updates feed and composer ------------------------------------------------------
def test_composer_submits_orders_and_ignores_blank(qtbot, dash):
    composer = dash.updates.composer
    composer.edit.setText("   ")
    qtbot.keyClick(composer.edit, Qt.Key.Key_Return)
    composer.edit.setText("  remember that I like tea ")
    qtbot.keyClick(composer.edit, Qt.Key.Key_Return)
    assert dash.orders == ["remember that I like tea"]
    assert composer.edit.text() == ""
    composer.edit.setText("open notepad")
    assert composer.action.kind == "send"
    qtbot.mouseClick(composer.action, Qt.MouseButton.LeftButton)
    assert dash.orders[-1] == "open notepad"
    assert composer.action.kind == "mic"


def test_feed_shows_verdicts_as_words_and_orders_on_the_right(dash, memory):
    memory.add_message("user", "play a song")
    memory.add_message("buddy", "I couldn't: play a song, because it needs a sign-in.")
    memory.add_message("buddy", "Done: opened Notepad.")
    memory.add_message("reminder", "Call mom")
    memory.add_message("offer", "A new job was posted. Shall I open it?")
    dash.refresh()
    text = labels(dash.updates)
    assert "I couldn't" in text and "Done" in text and "Suggestion" in text
    assert "Reminder: Call mom" in " ".join(text)
    assert any(f.objectName() == "bubbleMe" for f in dash.updates.findChildren(QFrame))


def test_sidebar_previews_come_from_real_data(dash, memory):
    memory.add_message("buddy", "Done: opened Notepad.")
    memory.start_job("order", "do a thing")
    memory.add_reminder("Call mom", time.time() + 3600)
    memory.add_pref("I like tea")
    dash.refresh()
    rows = dash.sidebar.rows
    assert rows["Updates"].preview == "Done: opened Notepad."
    assert rows["Activity"].preview == "Working: do a thing"
    assert rows["Reminders"].preview == "Call mom"
    assert rows["Memory"].preview.startswith("1 fact")
    assert rows["Connectors"].preview.startswith("Off")


def test_unread_dot_follows_what_you_have_seen():
    feed = [(100.0, "user", "an order"), (120.0, "buddy", "Done: x"), (140.0, "reminder", "Call")]
    assert unread_count(feed, 0) == 2          # your own orders are not news
    assert unread_count(feed, 120) == 1
    assert unread_count(feed, 140) == 0


def test_unread_dot_on_the_updates_row(dash, memory):
    row = dash.sidebar.rows["Updates"]
    memory.set(SEEN_KEY, str(time.time() - 10))
    dash.show_section("Activity")
    later(memory, "user", "my own order")
    dash.refresh()
    assert not row.unread
    later(memory, "buddy", "Done: something.")
    dash.refresh()
    assert row.unread  # new news while you are elsewhere
    dash.show_section("Updates")
    assert not row.unread  # opening Updates reads them
    assert float(memory.get(SEEN_KEY)) >= time.time() - 5
    later(memory, "reminder", "Call mom")
    dash.refresh()
    assert not row.unread  # you are looking at Updates, so it arrives read
    dash.show_section("Memory")
    later(memory, "reminder", "Another")
    dash.refresh()
    assert row.unread


# ---- search, panel, navigation ---------------------------------------------------------
def test_search_filters_rows_and_cards(dash, memory):
    memory.add_message("user", "check gmail")
    memory.add_message("user", "play music")
    memory.add_pref("I like tea")
    memory.add_pref("Work in Pune")
    dash.refresh()
    dash.sidebar.search.setText("gmail")
    texts = labels(dash.updates)
    assert "check gmail" in texts and "play music" not in texts
    assert dash.sidebar.rows["Settings"].isHidden()  # no match in its title or preview
    dash.sidebar.search.setText("memory")
    assert not dash.sidebar.rows["Memory"].isHidden() and dash.sidebar.rows["Activity"].isHidden()
    dash.sidebar.search.setText("")
    assert not dash.sidebar.rows["Settings"].isHidden()
    dash.show_section("Memory")
    dash.sidebar.search.setText("PUNE")
    assert card_titles(dash.memory_page) == ["Work in Pune"]


def test_plus_buttons_jump_and_focus(dash):
    dash.right.add_routine.emit()
    assert dash.current == "Reminders" and dash.focusWidget() is dash.reminders.what
    dash.sidebar.new_order.emit()
    assert dash.current == "Updates" and dash.focusWidget() is dash.updates.composer.edit
    dash.sidebar.plugins.emit()
    assert dash.current == "Connectors"
    dash.sidebar.profile.emit()
    assert dash.current == "Settings"


def test_right_panel_can_fold_away_and_remembers(dash, memory):
    dash.right.collapse.emit()
    assert dash.right.isHidden() and not dash.expand.isHidden()
    assert memory.get("hub_right_open") == "0"
    dash.expand.click()
    assert not dash.right.isHidden() and memory.get("hub_right_open") == "1"


def test_unchanged_data_does_not_rebuild_widgets(dash, memory):
    memory.add_pref("I like tea")
    dash.show_section("Memory")
    first = dash.memory_page.body.itemAt(1).widget()
    dash.refresh()
    dash.refresh()
    assert dash.memory_page.body.itemAt(1).widget() is first
    memory.add_pref("Another fact")
    dash.refresh()
    assert dash.memory_page.body.itemAt(1).widget() is not first


# ---- looks (styles) -----------------------------------------------------------------------
def seeded(memory):
    memory.add_message("user", "play a song")
    memory.add_message("buddy", "I couldn't: play a song, because it needs a sign-in.")
    memory.add_message("buddy", "Done: opened Notepad.")
    memory.add_message("reminder", "Call mom")
    memory.add_message("offer", "A new job was posted. Shall I open it?")
    memory.add_reminder("Pay the bill", time.time() + 3600)
    memory.add_pref("I like tea")
    memory.add_note("youtube", "Click the box first")
    memory.start_job("order", "do a thing")


def test_three_looks_are_registered_in_order():
    assert styles.ORDER == ["classic", "skeuo", "spatial"]
    assert [styles.STYLES[k].label for k in styles.ORDER] == ["Classic", "Skeuomorphic", "Spatial"]


def test_look_group_sits_first_in_settings_with_one_chip_per_look(dash):
    dash.show_section("Settings")
    assert dash.settings.cards[0].property("searchText").startswith("Look")
    assert list(dash.settings.look.chips) == styles.ORDER
    assert dash.settings.look.chips["classic"].isChecked()


def test_choosing_a_look_applies_stores_and_survives_a_new_window(qtbot, dash, memory, tmp_path):
    dash.show_section("Settings")
    qtbot.mouseClick(dash.settings.look.chips["skeuo"], Qt.MouseButton.LeftButton)
    assert styles.active().key == "skeuo" and memory.get("hub_style") == "skeuo"
    assert dash.settings.look.chips["skeuo"].isChecked()
    assert dash.styleSheet() == styles.active().stylesheet()
    again = Dashboard(memory, lambda text: None, env_file=tmp_path / ".env")
    qtbot.addWidget(again)
    assert styles.active().key == "skeuo"
    assert again.settings.look.chips["skeuo"].isChecked()
    dash.set_style("classic")
    assert memory.get("hub_style") == "classic" and styles.active().key == "classic"


def test_unknown_stored_look_falls_back_to_classic(qtbot, memory, tmp_path):
    memory.set("hub_style", "neon")
    window = Dashboard(memory, lambda text: None, env_file=tmp_path / ".env")
    qtbot.addWidget(window)
    assert styles.active().key == "classic"
    window.set_style("neon")  # ignored
    assert memory.get("hub_style") == "neon" and styles.active().key == "classic"


@pytest.mark.parametrize("look", styles.ORDER)
def test_every_section_builds_and_paints_under_each_look(qtbot, dash, memory, look):
    seeded(memory)
    dash.set_style(look)
    dash.refresh()
    for name in theme.NAMES:
        dash.show_section(name)
        assert dash.stack.currentWidget() is dash.pages[name]
        assert dash.sidebar.rows[name].isChecked()
        assert not dash.grab().isNull()  # forces every painted widget through the look
    assert dash.header_title.text() == "Settings"
    dash.set_right_open(False)
    assert not dash.grab().isNull()


@pytest.mark.parametrize("look", styles.ORDER)
def test_each_look_implements_every_hook(qtbot, look):
    style = styles.STYLES[look]
    pixmap = QPixmap(120, 80)
    p = QPainter(pixmap)
    rect = QRectF(0, 0, 100, 60)
    style.paint_tile(p, rect, "#2d8cff", "gear")
    style.paint_tile(p, rect, "#2d8cff", letter="G", circle=True)
    style.paint_check(p, rect)
    for fill in base.FILLS:
        style.paint_round_button(p, rect, fill, True, False, True)
        style.paint_round_button(p, rect, fill, False, True, False)
    style.paint_row(p, rect, True, False, True)
    style.paint_row(p, rect, False, True, False)
    style.paint_unread(p, QRectF(0, 0, 9, 9))
    style.paint_toggle(p, QRectF(0, 0, 40, 24), True, True)
    style.paint_toggle(p, QRectF(0, 0, 40, 24), False, False)
    for group in base.PILL_GROUPS:
        assert style.pill_colors(group) and isinstance(style.paint_pill(p, rect, group), str)
    style.paint_preview(p, rect)
    p.end()
    assert style.stylesheet() and style.tone("ink") and style.window_margins and style.pane_gap >= 0
    assert style.surface_insets("sidebar") and set(base.ROLES) >= {"sidebar", "centre", "right"}


def test_column_textures_are_cached_not_rebuilt_on_refresh(qtbot, dash, memory):
    dash.set_style("skeuo")
    dash.grab()
    look = styles.active()
    sidebar, centre = look._cache["sidebar"][1], look._cache["centre"][1]
    memory.add_message("buddy", "Done: something new.")
    dash.refresh()
    dash.refresh()
    dash.grab()
    assert look._cache["sidebar"][1] is sidebar and look._cache["centre"][1] is centre


def test_switching_look_rebuilds_no_widgets(dash, memory):
    memory.add_pref("I like tea")
    dash.show_section("Memory")
    first = dash.memory_page.body.itemAt(1).widget()
    dash.set_style("skeuo")
    dash.set_style("spatial")
    dash.refresh()
    assert dash.memory_page.body.itemAt(1).widget() is first
