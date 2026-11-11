from PySide6.QtCore import QPoint, QRect, QSettings, QSize, Qt
from PySide6.QtGui import QColor, QImage

from deskbuddy.state import STATE_COLORS, BuddyState
from deskbuddy.ui.kettle import KettleWidget
from deskbuddy.ui.window import BuddyWindow, clamp_to_screen, default_position

SCREEN = QRect(0, 0, 1920, 1040)
SIZE = QSize(450, 250)


def test_every_state_has_a_colour():
    assert set(STATE_COLORS) == set(BuddyState)


def test_kettle_draws_something_in_every_state(qtbot):
    kettle = KettleWidget()
    qtbot.addWidget(kettle)
    for state in BuddyState:
        kettle.set_state(state)
        image = kettle.grab().toImage().convertToFormat(QImage.Format.Format_ARGB32)
        face = image.pixelColor(image.width() // 2, int(image.height() * 0.42))
        assert face.alpha() == 255, state  # the dark face is painted
        assert image.pixelColor(1, 1).alpha() == 0, state  # corners stay see-through


def test_clamp_pulls_window_back_on_screen():
    assert clamp_to_screen(QPoint(5000, 5000), SIZE, SCREEN) == QPoint(1470, 790)
    assert clamp_to_screen(QPoint(-300, -50), SIZE, SCREEN) == QPoint(0, 0)
    assert clamp_to_screen(QPoint(100, 200), SIZE, SCREEN) == QPoint(100, 200)


def test_default_position_is_bottom_right_and_on_screen():
    pos = default_position(SIZE, SCREEN)
    assert pos == clamp_to_screen(pos, SIZE, SCREEN)
    assert pos.x() > SCREEN.width() / 2 and pos.y() > SCREEN.height() / 2


def make_window(qtbot, tmp_path):
    settings = QSettings(str(tmp_path / "s.ini"), QSettings.Format.IniFormat)
    window = BuddyWindow(settings)
    qtbot.addWidget(window)
    return window, settings


def test_typed_order_is_emitted_once_and_blank_is_ignored(qtbot, tmp_path):
    window, _ = make_window(qtbot, tmp_path)
    window.show()
    got = []
    window.order_submitted.connect(got.append)
    window.show_input()
    window.input.setText("   ")
    qtbot.keyClick(window.input, Qt.Key.Key_Return)
    window.show_input()
    window.input.setText("  open youtube ")
    qtbot.keyClick(window.input, Qt.Key.Key_Return)
    assert got == ["open youtube"]
    assert not window.input.isVisible()


def test_bubble_shows_text_and_hides_when_empty(qtbot, tmp_path):
    window, _ = make_window(qtbot, tmp_path)
    window.show()
    window.say("Opening YouTube")
    assert window.bubble.isVisible() and window.bubble.text() == "Opening YouTube"
    window.say("")
    assert not window.bubble.isVisible()


def test_saved_position_off_screen_is_brought_back(qtbot, tmp_path):
    settings = QSettings(str(tmp_path / "s.ini"), QSettings.Format.IniFormat)
    settings.setValue("window/pos", QPoint(99999, 99999))
    window = BuddyWindow(settings)
    qtbot.addWidget(window)
    screen = window.screen().availableGeometry()
    assert screen.contains(window.geometry())
