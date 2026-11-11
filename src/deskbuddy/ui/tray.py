"""The small icon near the clock: show, hide or quit Desk Buddy."""
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from deskbuddy.ui.kettle import KettleWidget
from deskbuddy.ui.window import BuddyWindow


def kettle_icon() -> QIcon:
    """Render the robot once into a square picture for the tray."""
    kettle = KettleWidget(width=128)
    kettle._timer.stop()
    pixmap = QPixmap(140, 140)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    kettle.render(painter, kettle.rect().translated(6, 3).topLeft())
    painter.end()
    kettle.deleteLater()
    return QIcon(pixmap)


def make_tray(app: QApplication, window: BuddyWindow, on_dashboard=None) -> QSystemTrayIcon:
    tray = QSystemTrayIcon(kettle_icon(), app)
    tray.setToolTip("Desk Buddy")
    menu = QMenu()
    if on_dashboard is not None:
        menu.addAction("Open dashboard").triggered.connect(on_dashboard)
    toggle = menu.addAction("Hide Desk Buddy")

    def flip() -> None:
        window.setVisible(not window.isVisible())
        toggle.setText("Hide Desk Buddy" if window.isVisible() else "Show Desk Buddy")

    toggle.triggered.connect(flip)
    menu.addAction("Type an order").triggered.connect(
        lambda: (window.show(), window.show_input())
    )
    menu.addSeparator()
    menu.addAction("Quit").triggered.connect(app.quit)
    tray.setContextMenu(menu)
    tray.activated.connect(
        lambda why: flip() if why == QSystemTrayIcon.ActivationReason.Trigger else None
    )
    tray._menu = menu  # keep the menu alive as long as the tray icon
    tray.show()
    return tray
