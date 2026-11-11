"""The dashboard looks. `active()` is the one the widgets paint with right now.

Every look has a light and a dark variant: one Style instance each, so each variant keeps its own
caches (textures, tiles, orbs) and switching between them never rebuilds anything that was drawn."""
from deskbuddy.ui.hub.styles.base import Style
from deskbuddy.ui.hub.styles.classic import ClassicStyle
from deskbuddy.ui.hub.styles.skeuo import SkeuoStyle
from deskbuddy.ui.hub.styles.spatial import SpatialStyle

DEFAULT = "classic"
CLASSES = {c.key: c for c in (ClassicStyle, SkeuoStyle, SpatialStyle)}
VARIANTS: dict[tuple[str, bool], Style] = {(key, dark): cls(dark) for key, cls in CLASSES.items()
                                           for dark in (False, True)}
STYLES: dict[str, Style] = {key: VARIANTS[(key, False)] for key in CLASSES}   # the light variants
ORDER = list(STYLES)   # the order of the chips in Settings
_active: Style = STYLES[DEFAULT]


def active() -> Style:
    return _active


def variant(key: str, dark: bool = False) -> Style:
    """The variant of look `key`; an unknown key gives Classic."""
    return VARIANTS.get((key, bool(dark))) or VARIANTS[(DEFAULT, bool(dark))]


def set_active(key: str, dark: bool = False) -> Style:
    """Make look `key` (light, or dark when `dark`) the one every widget paints with; an unknown
    key falls back to Classic."""
    global _active
    _active = variant(key, dark)
    return _active
