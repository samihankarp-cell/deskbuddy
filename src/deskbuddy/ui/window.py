"""The hovering window: Kettle, its bubble and the typing box."""
from PySide6.QtCore import QPoint, QRect, QSettings, QSize, Qt, Signal
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QHBoxLayout, QLineEdit, QVBoxLayout, QWidget

from deskbuddy.state import BuddyState
from deskbuddy.ui.bubble import BubbleWidget
from deskbuddy.ui.kettle import KettleWidget

WINDOW_SIZE = QSize(450, 250)
KETTLE_WIDTH = round(150 / 1.75)  # the robot is drawn 1.75 times smaller than before
EDGE_GAP = 24
DRAG_THRESHOLD = 6  # pixels the mouse must move before a press counts as a drag


def clamp_to_screen(pos: QPoint, size: QSize, screen: QRect) -> QPoint:
    """Return pos moved so a window of this size sits fully inside the screen."""
    x = max(screen.left(), min(pos.x(), screen.right() - size.width() + 1))
    y = max(screen.top(), min(pos.y(), screen.bottom() - size.height() + 1))
    return QPoint(x, y)


def default_position(size: QSize, screen: QRect) -> QPoint:
    """Bottom-right corner, a little in from the edges."""
    return QPoint(
        screen.right() - size.width() - EDGE_GAP, screen.bottom() - size.height() - EDGE_GAP
    )


class BuddyWindow(QWidget):
    order_submitted = Signal(str)
    answered = Signal(bool)
    stop_requested = Signal()
    dashboard_requested = Signal()

    def __init__(self, settings: QSettings | None = None):
        super().__init__()
        self._settings = settings or QSettings("DeskBuddy", "DeskBuddy")
        self.setWindowTitle("Desk Buddy")
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool  # keeps it off the taskbar
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(WINDOW_SIZE)

        self.kettle = KettleWidget(self, width=KETTLE_WIDTH)
        self.bubble = BubbleWidget(self)
        self.bubble.answered.connect(self.answered)
        self.input = QLineEdit(self)
        self.input.setPlaceholderText("Tell me what to do, then press Enter")
        self.input.setStyleSheet(
            "QLineEdit{background:#ffffff;color:#1c2633;border:2px solid #ff7a59;"
            "border-radius:12px;padding:7px 11px;font:13px 'Segoe UI';}"
        )
        self.input.returnPressed.connect(self._submit)
        self.input.hide()

        left = QVBoxLayout()
        left.addStretch(1)
        left.addWidget(self.bubble, 0, Qt.AlignmentFlag.AlignRight)
        left.addWidget(self.input)
        left.addSpacing(8)
        left.addSpacing(52)  # lifts the bubble to the height of the robot's head
        row = QHBoxLayout(self)
        row.setContentsMargins(6, 6, 6, 6)
        row.addLayout(left, 1)
        row.addWidget(self.kettle, 0, Qt.AlignmentFlag.AlignBottom)

        self._press_global: QPoint | None = None
        self._press_window = QPoint()
        self._dragging = False
        self.restore_position()

    # ---- what the rest of the app calls --------------------------------
    def set_state(self, state: BuddyState) -> None:
        self.kettle.set_state(state)
        self.bubble.set_state(state)

    def say(self, text: str) -> None:
        self.bubble.say(text)

    def ask(self, question: str) -> None:
        self.bubble.ask(question)

    def show_input(self) -> None:
        self.input.show()
        self.activateWindow()
        self.input.setFocus()

    # ---- position ------------------------------------------------------
    def restore_position(self) -> None:
        saved = self._settings.value("window/pos")
        screen = self._screen_rect(saved if isinstance(saved, QPoint) else None)
        if isinstance(saved, QPoint):
            self.move(clamp_to_screen(saved, self.size(), screen))
        else:
            self.move(default_position(self.size(), screen))

    def _screen_rect(self, near: QPoint | None) -> QRect:
        screen = QGuiApplication.screenAt(near) if near is not None else None
        screen = screen or QGuiApplication.primaryScreen()
        return screen.availableGeometry()

    # ---- typing box ----------------------------------------------------
    def _submit(self) -> None:
        text = self.input.text().strip()
        self.input.clear()
        self.input.hide()
        if text:
            self.order_submitted.emit(text)

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.input.clear()
            self.input.hide()
            self.stop_requested.emit()
        else:
            super().keyPressEvent(event)

    # ---- drag the robot to move, click it to type -----------------------
    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self.kettle.geometry().contains(
            event.position().toPoint()
        ):
            self._press_global = event.globalPosition().toPoint()
            self._press_window = self.pos()
            self._dragging = False

    def mouseDoubleClickEvent(self, event) -> None:
        if self.kettle.geometry().contains(event.position().toPoint()):
            self._press_global = None
            self.input.hide()
            self.dashboard_requested.emit()

    def mouseMoveEvent(self, event) -> None:
        if self._press_global is None:
            return
        delta = event.globalPosition().toPoint() - self._press_global
        if self._dragging or delta.manhattanLength() > DRAG_THRESHOLD:
            self._dragging = True
            self.move(self._press_window + delta)

    def mouseReleaseEvent(self, event) -> None:
        if self._press_global is None:
            return
        self._press_global = None
        if self._dragging:
            self.move(clamp_to_screen(self.pos(), self.size(), self._screen_rect(self.pos())))
            self._settings.setValue("window/pos", self.pos())
        elif self.input.isVisible():
            self.input.hide()
        else:
            self.show_input()
