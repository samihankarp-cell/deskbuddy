"""The speech bubble: a status dot and one short line of text."""
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QSizePolicy

from deskbuddy.state import STATE_COLORS, BuddyState

MAX_TEXT_WIDTH = 250


class BubbleWidget(QFrame):
    answered = Signal(bool)  # the user pressed Yes or No

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("bubble")
        self.setStyleSheet(
            "#bubble{background:#ffffff;border-radius:14px;border-bottom-right-radius:3px;}"
            "QLabel{color:#1c2633;font:600 13px 'Segoe UI';background:transparent;}"
        )
        row = QHBoxLayout(self)
        row.setContentsMargins(12, 9, 13, 9)
        row.setSpacing(8)
        self._dot = QLabel()
        self._dot.setFixedSize(8, 8)
        self._text = QLabel()
        self._text.setWordWrap(True)
        self._text.setMaximumWidth(MAX_TEXT_WIDTH)
        self._text.setTextFormat(Qt.TextFormat.PlainText)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        row.addWidget(self._dot, 0, Qt.AlignmentFlag.AlignVCenter)
        row.addWidget(self._text, 1)
        self._buttons = []
        for word, value, colour in (("Yes", True, "#35c8a0"), ("No", False, "#8a94a6")):
            button = QPushButton(word)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setStyleSheet(
                f"QPushButton{{background:{colour};color:#ffffff;border:none;border-radius:9px;"
                "padding:4px 12px;font:600 12px 'Segoe UI';}"
            )
            button.clicked.connect(lambda _=False, v=value: self._answer(v))
            button.hide()
            row.addWidget(button, 0, Qt.AlignmentFlag.AlignVCenter)
            self._buttons.append(button)
        self.set_state(BuddyState.IDLE)
        self.hide()

    def text(self) -> str:
        return self._text.text()

    def set_state(self, state: BuddyState) -> None:
        self._dot.setStyleSheet(
            f"background:{STATE_COLORS[state]};border-radius:4px;"
        )

    def ask(self, question: str) -> None:
        self.say(question)
        for button in self._buttons:
            button.show()
        self.adjustSize()

    def _answer(self, yes: bool) -> None:
        for button in self._buttons:
            button.hide()
        self.answered.emit(yes)

    def say(self, text: str) -> None:
        for button in self._buttons:
            button.hide()
        self._text.setText(text)
        # short lines stay on one line; long ones wrap at MAX_TEXT_WIDTH
        natural = self._text.fontMetrics().horizontalAdvance(text) + 4
        self._text.setFixedWidth(min(MAX_TEXT_WIDTH, natural))
        self._text.setFixedHeight(self._text.heightForWidth(self._text.width()))
        self.setVisible(bool(text))
        self.adjustSize()
