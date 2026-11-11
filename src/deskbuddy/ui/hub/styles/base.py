"""The contract of a dashboard look ("style").

A look is one `Style` subclass in hub/styles/<name>.py, registered in hub/styles/__init__.py.
The layout (three columns, the same sections, rows, widgets, positions) never changes between
looks. A look only supplies:

  1. TOKENS      plain attributes: fonts, colours, window geometry.
  2. QSS         `stylesheet()` for the stock widgets (labels, inputs, buttons, scroll bars, menus).
  3. PAINT HOOKS `paint_*` methods. Every custom-painted piece of the dashboard calls one of them at
                 paint time, so a look change is just "update() everything" (no rebuild, no restart).

Painting rules for hook authors
  * Hooks run inside paintEvent, often many times a second (Kettle animates at 30 fps and repaints
    its neighbours). Never build a texture, blur or gradient pixmap there unless it is cached:
    use `self.cached(name, size_key, make)` (one entry per name; replaced when the size changes).
  * Do not use QGraphicsEffect on repeated items; paint shadows yourself, inside the widget rect.
  * Draw inside `widget.rect()`. A shadow that needs room must be drawn within the rect (inset the
    body), because a child cannot paint outside its own rectangle.
  * Text colours for painted text come from the tokens below, never from literals.

Surfaces. Every card-like frame is a `Surface` (hub/surface.py) with a `role`; its paintEvent calls
`paint_surface(p, widget, role)`. Roles (also the widget's objectName):
  columns:   "sidebar", "centre", "right"                 full-height panes of the window
  chrome:    "header" (title strip above the page), "composer" (message pill at the page foot)
  tiles:     "tile" (84px Kettle tile, sidebar), "preview" (Kettle display, right pane)
  cards:     "card" (job / fact / settings group), "form" (inline input strip), "note" (system note)
  bubbles:   "bubbleBot" (Desk Buddy), "bubbleMe" (the user's orders)
  routines:  "notepad" (holds the routine list), "rule" (one routine row)

A surface paints on top of whatever its parent painted, so a look that wants a texture behind the
cards paints it in the column ("centre"/"right"/"sidebar") and the cards float above it. Scroll
areas, pages and list holders are transparent; the column shows through.

Modes. Every look comes in a light and a dark variant. A variant is one Style INSTANCE built with
`dark=True/False` (hub/styles/__init__.py keeps one of each, so every variant owns its own caches and
switching never rebuilds a texture). The variant's colours live in a token dict returned by
`tokens()` (one LIGHT and one DARK dict per look, in hub/styles/*_tokens.py); the paint hooks and the
QSS read `self.t.<name>`, never a literal, so a mode is just another set of numbers. The layout and
the geometry do not change with the mode.

Floating panes (a Spatial-type look): set `window_margins` and `pane_gap` and the three columns
sit apart with the window showing between them. Paint the window backdrop in `paint_window`, and
paint each column as a rounded pane in `paint_surface` for the roles sidebar/centre/right (use
`widget.mapTo(widget.window(), QPoint(0, 0))` to know where the pane is inside the backdrop, e.g.
to draw a pre-blurred slice of it; cache the blurred backdrop with `self.cached`). Columns are
plain rectangles to the layout; the look decides how much of the rectangle to paint (rounded rect,
inset for a shadow, ...). `pane_radius(role)` is the corner radius your own painting uses (kept as a token for helpers).
"""
from types import SimpleNamespace

from PySide6.QtCore import QRectF
from PySide6.QtGui import QColor, QPainter, QPixmap

ROLES = ("sidebar", "centre", "right", "header", "composer", "tile", "preview", "card", "form",
         "note", "bubbleBot", "bubbleMe", "notepad", "rule")
PILL_GROUPS = ("good", "bad", "warn", "quiet", "idea")   # colour groups behind theme.PILLS
FILLS = ("", "soft", "strong")                           # round-button fills, see paint_round_button


# tokens every look must define; the widgets read them straight off the style (style.side_ink ...)
BASE_TOKENS = ("ink", "body", "meta", "side_ink", "side_meta", "accent", "green", "strong_glyph",
               "error_ink", "ok_ink")


# the stock widgets styled as a text input. "keyCapture" is the hold-to-talk key box in Settings:
# it looks like a field, and like a focused field while it is waiting for a key.
FIELD = ("QLineEdit#field, QDateTimeEdit#field, QLineEdit#keyCapture, QAbstractButton#keyCapture")
FIELD_FOCUS = ("QLineEdit#field:focus, QDateTimeEdit#field:focus, QLineEdit#keyCapture:focus, "
               "QAbstractButton#keyCapture:focus, QLineEdit#keyCapture[recording=\"true\"], "
               "QAbstractButton#keyCapture[recording=\"true\"]")


def ratio(p: QPainter) -> float:
    """Device pixel ratio of whatever the painter draws on (use it for cached pixmaps)."""
    return max(1.0, p.device().devicePixelRatioF())


def make_pixmap(width: float, height: float, dpr: float = 1.0) -> QPixmap:
    """A transparent pixmap of width x height logical pixels at the given pixel ratio."""
    pixmap = QPixmap(max(1, int(width * dpr)), max(1, int(height * dpr)))
    pixmap.setDevicePixelRatio(dpr)
    pixmap.fill(QColor(0, 0, 0, 0))
    return pixmap


class Style:
    # ---- identity ------------------------------------------------------------------------
    key = ""        # stored in memory as "hub_style"
    label = ""      # shown on the Look chip
    blurb = ""      # one line under the chip

    # ---- tokens: fonts and geometry -------------------------------------------------------
    families = ("Segoe UI Variable Text", "Segoe UI", "Helvetica Neue", "Arial")
    window_margins = (0, 0, 0, 0)   # (left, top, right, bottom) between window edge and the columns
    pane_gap = 0                    # px between the columns
    press_shift = 0                 # px a pressed round button's glyph moves down

    # ---- tokens: colours (hex strings). Painted widgets read exactly these ---------------
    # The real values come from tokens() (per mode); these defaults only document the meaning.
    ink = "#111111"          # strong text in the centre and right columns
    body = "#3a3a3f"         # normal text
    meta = "#6e6e73"         # secondary text, time stamps, hints
    side_ink = "#111111"     # strong text on the sidebar (a dark sidebar needs light text)
    side_meta = "#6e6e73"    # secondary text on the sidebar
    accent = "#2d8cff"       # keyboard focus rings and the unread dot
    green = "#22c55e"        # check circles, "on" toggles
    strong_glyph = "#ffffff"  # glyph colour on a "strong" round button (the composer's mic/send)
    error_ink = "#b3261e"    # error text
    ok_ink = "#15803d"       # "Saved." text

    def __init__(self, dark: bool = False):
        self._cache: dict[str, tuple] = {}
        self.dark = dark
        self.t = SimpleNamespace(**self.tokens())
        for name in BASE_TOKENS:
            setattr(self, name, getattr(self.t, name))

    def tokens(self) -> dict:
        """The colour tokens of this variant (self.dark picks light or dark): BASE_TOKENS plus
        whatever the look's own painters and QSS read from `self.t`."""
        raise NotImplementedError

    @property
    def mode(self) -> str:
        return "dark" if self.dark else "light"

    # ---- helpers for subclasses -----------------------------------------------------------
    def cached(self, name: str, size_key, make):
        """Return make() once per (name, size_key); a new size_key replaces the old entry."""
        hit = self._cache.get(name)
        if hit is None or hit[0] != size_key:
            hit = (size_key, make())
            self._cache[name] = hit
        return hit[1]

    def tone(self, name: str) -> str:
        """Colour for a GlyphButton/Glyph `tone`: ink, meta, side, side_meta, green."""
        return {"ink": self.ink, "meta": self.meta, "side": self.side_ink,
                "side_meta": self.side_meta, "green": self.green}[name]

    # ---- geometry hooks ---------------------------------------------------------------------
    def pane_radius(self, role: str) -> float:
        """Corner radius of a surface, for looks that round their panes. 0 = square."""
        return 0.0

    def surface_insets(self, role: str) -> tuple[int, int, int, int]:
        """Widget contents margins (l, t, r, b) of a surface: space the layout keeps clear inside
        it, e.g. the 1px divider Classic draws on a column's edge. Default none."""
        return (0, 0, 0, 0)

    def surface_margins(self, role: str):
        """Inner layout margins (l, t, r, b) for a surface whose padding depends on the look,
        or None to keep what the widget set. Only "notepad" asks: it holds the routine list."""
        return None

    # ---- QSS ---------------------------------------------------------------------------------
    def stylesheet(self) -> str:
        """The application stylesheet. Painted surfaces need NO background rules here; the stock
        widgets do: QLabel colours per column, QLineEdit#search/#field/#composerEdit,
        QDateTimeEdit#field, QPushButton#primary/#quiet, QScrollBar, QMenu, QToolTip, and the
        transparent QScrollArea / QWidget#holder / QWidget#page that let the column show through."""
        raise NotImplementedError

    # ---- window and surface hooks -----------------------------------------------------------
    def paint_window(self, p: QPainter, window) -> None:
        """Paint the whole window behind the columns (Dashboard.paintEvent). Classic fills white;
        a floating-pane look paints its backdrop here and caches it per window size."""
        raise NotImplementedError

    def paint_surface(self, p: QPainter, widget, role: str) -> None:
        """Paint a Surface. `widget.rect()` is the area; `widget.property("focused")` is True for
        a focused composer; `widget.underMouse()` is available for hover-aware looks."""
        raise NotImplementedError

    # ---- icon and control hooks -------------------------------------------------------------
    def paint_tile(self, p: QPainter, rect: QRectF, color: str, glyph: str = "", letter: str = "",
                   circle: bool = False) -> None:
        """A section / app icon: `color` is its identity colour, `glyph` a key of glyphs.SHAPES or
        `letter` a single character; `circle` for the profile avatar. Called from several rows per
        paint: cache the finished tile (`self.cached` keyed by everything that varies)."""
        raise NotImplementedError

    def paint_check(self, p: QPainter, rect: QRectF) -> None:
        """The check circle before a routine (a done / scheduled mark), `self.green` themed."""
        raise NotImplementedError

    def paint_round_button(self, p: QPainter, rect: QRectF, fill: str, hot: bool, down: bool,
                           focused: bool) -> None:
        """The disc behind a GlyphButton. fill: "" (bare: show something only when `hot`),
        "soft" (a quiet disc, the composer's +) or "strong" (the main disc, mic/send)."""
        raise NotImplementedError

    def paint_row(self, p: QPainter, box: QRectF, checked: bool, hot: bool, focused: bool) -> None:
        """The background of a sidebar row inside `box` (the selected one is `checked`)."""
        raise NotImplementedError

    def paint_unread(self, p: QPainter, rect: QRectF) -> None:
        """The unread dot on the Updates row (rect is 9x9)."""
        raise NotImplementedError

    def paint_toggle(self, p: QPainter, rect: QRectF, on: bool, focused: bool) -> None:
        """An on/off switch filling `rect` (40x24). The knob's side tells on from off."""
        raise NotImplementedError

    def pill_colors(self, group: str) -> tuple[str, str]:
        """(text colour, tint) for a verdict-pill group of PILL_GROUPS. Colour only backs the word."""
        raise NotImplementedError

    def paint_pill(self, p: QPainter, rect: QRectF, group: str) -> str:
        """Paint the pill's background inside `rect`; return the colour to draw its word in."""
        raise NotImplementedError

    def text_shadow(self, name: str):
        """None, or (dx, dy, "#rrggbb"/"#aarrggbb") drawn behind single-line text of a ShadowLabel
        or sidebar row (letterpress / embossed type). Names: headerTitle, panelTitle, tileName,
        rowTitle."""
        return None

    def paint_preview(self, p: QPainter, rect: QRectF) -> None:
        """A miniature of this look (three columns, a bubble or two) for the Look picker chip."""
        raise NotImplementedError

    # ---- the Light | Dark | System control ------------------------------------------------------
    def paint_segment_track(self, p: QPainter, rect: QRectF) -> None:
        """The trough of the segmented control in Settings -> Look (the Mode picker)."""
        raise NotImplementedError

    def paint_segment(self, p: QPainter, rect: QRectF, on: bool, hot: bool, focused: bool) -> None:
        """One segment inside the trough: `on` is the chosen one. The word is drawn by the
        widget in `segment_ink(on)`."""
        raise NotImplementedError

    def segment_ink(self, on: bool) -> str:
        return self.ink if on else self.body
