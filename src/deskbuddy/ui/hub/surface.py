"""Widgets whose look comes from the active style at paint time: Surface and ShadowLabel."""
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QFrame, QLabel

from deskbuddy.ui.hub import styles


class Surface(QFrame):
    """A frame that paints itself through Style.paint_surface(role). `name` is the objectName
    (QSS selectors and tests use it); it defaults to the role."""

    def __init__(self, role: str, name: str = ""):
        super().__init__()
        self.role = role
        self.setObjectName(name or role)
        self.setContentsMargins(*styles.active().surface_insets(role))

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        styles.active().paint_surface(p, self, self.role)
        p.end()

    def restyle(self) -> None:
        """Apply the look's inner padding, for surfaces that ask for one (Style.surface_margins)."""
        look = styles.active()
        self.setContentsMargins(*look.surface_insets(self.role))
        margins = look.surface_margins(self.role)
        if margins and self.layout():
            self.layout().setContentsMargins(*margins)


class ShadowLabel(QLabel):
    """A single-line label with the look's text shadow (letterpress) drawn behind it."""

    def paintEvent(self, event) -> None:
        shadow = styles.active().text_shadow(self.objectName())
        if shadow:
            dx, dy, colour = shadow
            p = QPainter(self)
            p.setFont(self.font())
            p.setPen(QColor(colour))
            p.drawText(self.contentsRect().translated(dx, dy), int(self.alignment()), self.text())
            p.end()
        super().paintEvent(event)
