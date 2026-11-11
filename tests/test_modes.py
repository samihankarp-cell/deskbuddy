"""Light / Dark / System for every look: the stored choice, following Windows, six variants that all
build and paint, caches that survive switching, an unchanged layout, text that stays readable, and
the three variants that must still look exactly as they did before modes existed."""
import pytest
from PySide6.QtCore import QPoint, QRect, Qt
from PySide6.QtGui import QColor, QGuiApplication, QImage, QPainter
from PySide6.QtWidgets import QLabel, QWidget
from test_hub import classic_again, dash, memory, seeded  # noqa: F401  (the hub's fixtures)

from deskbuddy.ui.hub import styles, theme
from deskbuddy.ui.hub.styles import classic_tokens, modes
from deskbuddy.ui.hub.window import Dashboard

VARIANTS = [(look, dark) for look in styles.ORDER for dark in (False, True)]
IDS = [f"{look}-{'dark' if dark else 'light'}" for look, dark in VARIANTS]


def set_variant(window, look: str, dark: bool) -> None:
    window.set_style(look)
    window.set_mode("dark" if dark else "light")


def contrast(a: QColor, b: QColor) -> float:
    def lum(c: QColor) -> float:
        def f(v):
            return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
        return 0.2126 * f(c.redF()) + 0.7152 * f(c.greenF()) + 0.0722 * f(c.blueF())
    hi, lo = sorted((lum(a), lum(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def snapshot(window) -> QImage:
    image = QImage(window.size(), QImage.Format.Format_RGB32)
    window.render(image)
    return image


# ---- the choice: stored, persisted, applied at once ---------------------------------------------
def test_modes_are_light_dark_system_and_the_default_is_system(dash, memory):
    assert modes.MODES == ("light", "dark", "system") and modes.DEFAULT_MODE == "system"
    assert dash.mode == "system" and not memory.get("hub_mode")
    dash.show_section("Settings")
    assert list(dash.settings.mode.segments) == ["light", "dark", "system"]
    assert dash.settings.mode.segments["system"].isChecked()


def test_choosing_a_mode_applies_stores_and_survives_a_new_window(qtbot, dash, memory, tmp_path):
    dash.show_section("Settings")
    qtbot.mouseClick(dash.settings.mode.segments["dark"], Qt.MouseButton.LeftButton)
    assert memory.get("hub_mode") == "dark" and styles.active().dark
    assert dash.styleSheet() == styles.active().stylesheet()
    again = Dashboard(memory, lambda text: None, env_file=tmp_path / ".env")
    qtbot.addWidget(again)
    assert again.mode == "dark" and styles.active().dark
    assert again.settings.mode.segments["dark"].isChecked()
    qtbot.mouseClick(dash.settings.mode.segments["light"], Qt.MouseButton.LeftButton)
    assert memory.get("hub_mode") == "light" and not styles.active().dark


def test_choosing_a_look_keeps_the_mode_and_the_mode_keeps_the_look(dash, memory):
    dash.set_mode("dark")
    dash.set_style("skeuo")
    assert (styles.active().key, styles.active().dark) == ("skeuo", True)
    dash.set_mode("light")
    assert (styles.active().key, styles.active().dark) == ("skeuo", False)
    assert memory.get("hub_style") == "skeuo" and memory.get("hub_mode") == "light"


def test_unknown_stored_or_chosen_mode_is_system_or_ignored(qtbot, memory, tmp_path):
    memory.set("hub_mode", "twilight")
    window = Dashboard(memory, lambda text: None, env_file=tmp_path / ".env")
    qtbot.addWidget(window)
    assert window.mode == "system"
    window.set_mode("dusk")   # ignored
    assert window.mode == "system" and memory.get("hub_mode") == "twilight"


def test_arrow_keys_move_between_the_modes(qtbot, dash, memory):
    dash.show_section("Settings")
    light = dash.settings.mode.segments["light"]
    light.setFocus()
    qtbot.keyClick(light, Qt.Key.Key_Right)
    assert memory.get("hub_mode") == "dark" and dash.settings.mode.segments["dark"].isChecked()


# ---- System follows Windows ----------------------------------------------------------------------
def test_system_mode_decides_from_the_color_scheme(monkeypatch):
    monkeypatch.setattr(modes, "system_dark", lambda: True)
    assert modes.is_dark("system") and modes.is_dark("dark") and not modes.is_dark("light")
    monkeypatch.setattr(modes, "system_dark", lambda: False)
    assert not modes.is_dark("system") and modes.is_dark("dark") and not modes.is_dark("light")


def test_system_mode_follows_a_faked_color_scheme_live(qtbot, dash, memory):
    hints = QGuiApplication.styleHints()
    if not hasattr(hints, "setColorScheme"):
        pytest.skip("this Qt cannot fake the colour scheme (needs 6.8)")
    assert dash.mode == "system" and not styles.active().dark
    hints.setColorScheme(Qt.ColorScheme.Dark)
    qtbot.waitUntil(lambda: styles.active().dark, timeout=3000)
    assert dash.styleSheet() == styles.active().stylesheet()
    hints.setColorScheme(Qt.ColorScheme.Light)
    qtbot.waitUntil(lambda: not styles.active().dark, timeout=3000)
    dash.set_mode("dark")   # an explicit choice ignores Windows
    hints.setColorScheme(Qt.ColorScheme.Light)
    assert styles.active().dark
    dash.set_mode("light")
    hints.setColorScheme(Qt.ColorScheme.Dark)
    qtbot.wait(150)
    assert not styles.active().dark and memory.get("hub_mode") == "light"


# ---- the look chips show the mode in force --------------------------------------------------------
@pytest.mark.parametrize("look", styles.ORDER)
def test_look_chip_previews_follow_the_effective_mode(dash, look):
    dash.show_section("Settings")
    chip = dash.settings.look.chips[look]

    def corner() -> QColor:   # a spot of the miniature that no bubble or row covers
        return QColor(chip.grab().toImage().pixel(chip.width() - 14, 14))

    dash.set_mode("light")
    light = corner()
    dash.set_mode("dark")
    assert contrast(light, corner()) > 1.5
    if look == "classic":
        assert corner().name() == classic_tokens.DARK["bg"]


# ---- 6 variants: all build, all paint ------------------------------------------------------------
@pytest.mark.parametrize(("look", "dark"), VARIANTS, ids=IDS)
def test_every_look_and_mode_builds_and_paints_every_section(qtbot, dash, memory, look, dark):
    seeded(memory)
    set_variant(dash, look, dark)
    assert styles.active() is styles.variant(look, dark) and styles.active().dark is dark
    dash.refresh()
    for name in theme.NAMES:
        dash.show_section(name)
        assert dash.stack.currentWidget() is dash.pages[name]
        assert not dash.grab().isNull()
    dash.set_right_open(False)
    assert not dash.grab().isNull()


@pytest.mark.parametrize(("look", "dark"), VARIANTS, ids=IDS)
def test_each_variant_defines_every_token_the_widgets_read(look, dark):
    style = styles.variant(look, dark)
    for name in ("ink", "body", "meta", "side_ink", "side_meta", "accent", "green", "strong_glyph",
                 "error_ink", "ok_ink"):
        assert QColor(getattr(style, name)).isValid()
        assert getattr(style, name) == getattr(style.t, name)
    for group in ("good", "bad", "warn", "quiet", "idea"):
        assert all(QColor(c).isValid() for c in style.pill_colors(group))
    assert "keyCapture" in style.stylesheet()   # the hold-to-talk key box is styled like an input


# ---- caches: per variant, never rebuilt by a switch or a refresh -----------------------------------
def test_each_variant_keeps_its_own_textures_across_switches(dash, memory):
    dash.set_style("skeuo")
    dash.set_mode("light")
    dash.grab()
    light = styles.active()
    side_light, centre_light = light._cache["sidebar"][1], light._cache["centre"][1]
    dash.set_mode("dark")
    dash.grab()
    night = styles.active()
    assert night is not light and night._cache["sidebar"][1] is not side_light
    side_dark = night._cache["sidebar"][1]
    memory.add_message("buddy", "Done: something new.")
    dash.refresh()
    dash.grab()
    assert night._cache["sidebar"][1] is side_dark   # a refresh rebuilds nothing
    dash.set_mode("light")
    dash.grab()
    assert styles.active() is light
    assert light._cache["sidebar"][1] is side_light and light._cache["centre"][1] is centre_light


def test_spatial_backdrops_are_cached_per_mode(dash):
    names = ("sp_back", "sp_frost", "sp_scene", "sp_pane_sidebar", "sp_pane_centre", "sp_pane_right")
    dash.set_style("spatial")
    seen = {}
    for dark in (False, True, False, True):
        dash.set_mode("dark" if dark else "light")
        dash.grab()
        cache = styles.active()._cache
        now = [cache[name][1] for name in names]
        if dark in seen:
            assert all(a is b for a, b in zip(seen[dark], now))   # coming back reuses, never rebuilds
        seen[dark] = now
    assert all(a is not b for a, b in zip(seen[False], seen[True]))


# ---- the layout never changes ----------------------------------------------------------------------
@pytest.mark.parametrize("look", styles.ORDER)
def test_layout_is_identical_in_light_and_dark(qtbot, dash, memory, look):
    seeded(memory)
    dash.set_style(look)

    def layout() -> list:
        qtbot.wait(30)   # let the layout settle after a switch
        dash.refresh()
        out = []
        for name in ("Updates", "Settings", "Reminders"):
            dash.show_section(name)
            qtbot.wait(30)
            out += [(w.objectName(), w.geometry().getRect()) for w in dash.findChildren(QWidget)
                    if w.isVisibleTo(dash)]
        m = dash.root.contentsMargins()
        return out + [(m.left(), m.top(), m.right(), m.bottom(), dash.root.spacing())]

    dash.set_mode("light")
    light = layout()
    dash.set_mode("dark")
    assert layout() == light


# ---- the three variants that must not have changed ------------------------------------------------
def test_classic_light_tokens_are_exactly_the_original_classic():
    t = styles.variant("classic").t
    assert styles.variant("classic").ink == "#111111" and t.meta == "#6e6e73" and t.body == "#3a3a3f"
    assert (t.bg, t.side_bg, t.line, t.bubble, t.hover, t.select, t.edge) == (
        "#ffffff", "#f6f6f7", "#ebebeb", "#f1f1f2", "#ececee", "#e6e6e9", "#dcdce0")
    assert (t.me_fill, t.me_ink, t.sb, t.sb_hot, t.toggle_off) == (
        "#111111", "#ffffff", "#d4d4d8", "#b9b9bf", "#cfcfd4")
    assert t.pills["good"] == ("#15803d", "#e6f6ec") and t.pills["idea"] == ("#5b3f99", "#efeafd")


def test_classic_dark_is_the_grok_night_look():
    t = styles.variant("classic", True).t
    assert (t.bg, t.side_bg, t.line, t.bubble, t.me_fill) == (
        "#0e0e10", "#151517", "#26262a", "#1f1f23", "#ffffff")
    assert QColor(t.me_ink).lightness() < 40   # black type on the white order bubble
    assert contrast(QColor("#9a9aa2"), QColor(t.meta)) < 1.2 and styles.variant("classic", True).dark
    assert classic_tokens.DARK["green"] == classic_tokens.LIGHT["green"]   # blob colours unchanged
    assert theme.COLORS["Updates"] == "#ff6b2c" and theme.COLORS["Settings"] == "#ff3fa4"


def test_skeuo_light_tokens_are_exactly_the_original_skeuo():
    t = styles.variant("skeuo").t
    assert (t.ink, t.body, t.meta, t.side_ink, t.side_meta) == (
        "#2a2017", "#463a2b", "#5a4c38", "#f8edd8", "#e4d2b0")
    assert (t.win, t.leather, t.linen, t.linen_r, t.felt) == (
        "#2b1a0e", "#5a3a24", "#eee5d1", "#e6d9bf", "#27493f")
    assert (t.card_top, t.card_bot, t.card_edge, t.head_top, t.head_bot) == (
        "#fffcf3", "#f4ecd9", "#d3c4a4", "#f7f3ea", "#d2c9b6")
    assert (t.me_top, t.me_mid, t.me_bot, t.weave, t.brush) == ("#665040", "#4a3727", "#2b1e15", 1.0, 1.0)
    assert t.pills["good"] == ("#1b6b35", "#e1efdf") and t.text_shadows["headerTitle"] == (0, 1, "#e6ffffff")


def test_spatial_dark_tokens_are_exactly_the_original_spatial():
    t = styles.variant("spatial", True).t
    assert (t.ink, t.body, t.meta, t.accent, t.green) == ("#ffffff", "#f3f0fd", "#d6d2ea", "#8bb0ff", "#5fe58c")
    assert t.sky == ((0.0, "#150f40"), (0.5, "#2b1c6a"), (1.0, "#5a2a72"))
    assert t.glows[0] == (0.84, 1.02, 0.78, (255, 140, 98), 215) and len(t.glows) == 6
    assert t.pane_tint == (14, 8, 38, 134) and t.gain == 1.0 and t.hair[3] == 0
    assert t.pills["good"] == ("#8ff2b4", "#2fc46e") and t.me_tint == ("#3d56d4", 160)


class Stub:
    """Just enough of a widget for Style.paint_surface / paint_window at a known place, so the
    pixels do not depend on this screen (its pixel ratio, its size, its fonts)."""

    def __init__(self, w, h, window=None, at=(0, 0)):
        self.w, self.h, self._window, self._at = w, h, window, at

    def rect(self):
        return QRect(0, 0, self.w, self.h)

    def width(self):
        return self.w

    def height(self):
        return self.h

    def window(self):
        return self._window or self

    def mapTo(self, _parent, _point):
        return QPoint(*self._at)

    def property(self, _name):
        return None

    def underMouse(self):
        return False

    def parentWidget(self):
        return None


def painted(look, dark, role, w, h, at=(0, 0)) -> QImage:
    """One surface of a variant as it paints inside the 1180x760 window; role "window" paints the backdrop."""
    image = QImage(w, h, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(QColor("#000000"))
    p = QPainter(image)
    style, window = styles.variant(look, dark), Stub(1180, 760)
    if role == "window":
        style.paint_window(p, window)
    else:
        style.paint_surface(p, Stub(w, h, window, at), role)
    p.end()
    return image


# Pixels of the three unchanged variants, read from screenshots taken of the code as it was before
# modes existed (1180x760: a blank bit of each column, the header, a corner of the window). The
# textures are seeded and deterministic, so the same pixels must come out. (look, dark, role, size,
# where the widget sits in the window) -> {point inside the widget: colour}
GOLDEN = [
    ("classic", False, "sidebar", (250, 760), (0, 0), {(100, 600): "#f6f6f7"}),
    ("classic", False, "centre", (660, 760), (250, 0), {(12, 400): "#ffffff"}),
    ("classic", False, "header", (660, 48), (250, 0), {(450, 24): "#ffffff"}),
    ("classic", False, "right", (270, 760), (910, 0), {(262, 500): "#ffffff"}),
    ("skeuo", False, "sidebar", (250, 760), (0, 0), {(100, 600): "#563825", (60, 300): "#5f402a"}),
    ("skeuo", False, "centre", (660, 760), (250, 0), {(12, 400): "#d9ceb9"}),
    ("skeuo", False, "header", (660, 48), (250, 0), {(450, 24): "#e2dccd"}),
    ("skeuo", False, "right", (270, 760), (910, 0), {(262, 500): "#e5d9c1"}),
    ("spatial", True, "window", (1180, 760), (0, 0), {(3, 3): "#273b74", (1177, 3): "#6f356f", (590, 3): "#503995"}),
    ("spatial", True, "sidebar", (250, 732), (14, 14), {(46, 606): "#233c5a"}),
    ("spatial", True, "centre", (608, 732), (276, 14), {(14, 386): "#322e60"}),
    ("spatial", True, "right", (270, 732), (896, 14), {(9, 586): "#5c334b"}),
]


@pytest.mark.parametrize(("look", "dark", "role", "size", "at", "want"), GOLDEN,
                         ids=[f"{g[0]}-{'dark' if g[1] else 'light'}-{g[2]}" for g in GOLDEN])
def test_unchanged_variants_still_paint_the_same_pixels(qapp, look, dark, role, size, at, want):
    image = painted(look, dark, role, *size, at=at)
    got = {point: QColor(image.pixel(*point)).name() for point in want}
    assert got == want


# ---- readable text in all six ---------------------------------------------------------------------
def background_of(image: QImage, rect: QRect) -> QColor:
    """What a label sits on: the median colour of its rectangle (text covers well under half of it)."""
    rect = rect.intersected(image.rect())
    pixels = [image.pixelColor(x, y) for y in range(rect.top(), rect.bottom() + 1)
              for x in range(rect.left(), rect.right() + 1)]
    pixels.sort(key=lambda c: contrast(c, QColor("#000000")))
    return pixels[len(pixels) // 2]


def ink_of(style, label: QLabel) -> str:
    """The colour the look's tokens give this label's text."""
    name = label.objectName()
    if name == "pill":
        return style.pill_colors(label.property("group") or label.group)[0]
    if name == "status":
        return "#f0e6cf" if style.key == "skeuo" else style.body
    return {"bubbleBotText": style.ink, "bubbleMeText": style.t.me_ink, "cardTitle": style.ink,
            "rowTitle": style.ink, "tileName": style.side_ink, "cardBody": style.body,
            "fieldLabel": style.body, "noteText": style.body}.get(name, style.meta)


BODY = ("bubbleBotText", "bubbleMeText", "cardTitle", "cardBody", "fieldLabel", "rowTitle", "noteText",
        "pill", "status", "tileName", "hint", "stamp", "cardMeta", "rowSub")
# Classic Light and Skeuomorphic Light are exactly what shipped; their small print (meta type on grey
# or paper, a verdict word on a tint) was already a little under 4.5 and stays as it was.
SHIPPED = {("classic", False): 4.0, ("skeuo", False): 4.3}


@pytest.mark.parametrize(("look", "dark"), VARIANTS, ids=IDS)
def test_body_text_is_readable_in_every_variant(qtbot, dash, memory, look, dark):
    seeded(memory)
    for n in range(4):
        memory.add_message("buddy" if n % 2 else "user", f"Done: sample line {n}, to give the page some text.")
    set_variant(dash, look, dark)
    dash.refresh()
    qtbot.wait(150)
    style, need, seen = styles.active(), SHIPPED.get((look, dark), 4.5), 0
    for page in ("Updates", "Settings", "Reminders", "Memory"):
        dash.show_section(page)
        qtbot.wait(150)   # a page lays itself out over a few events
        image = snapshot(dash)
        for label in dash.findChildren(QLabel):
            if (label.objectName() not in BODY or not label.text().strip() or not label.isVisibleTo(dash)
                    or label.visibleRegion().boundingRect() != label.rect()):
                continue
            where = QRect(label.mapTo(dash, label.rect().topLeft()), label.size())
            ratio = contrast(QColor(ink_of(style, label)), background_of(image, where))
            seen += 1
            assert ratio >= need, (page, label.objectName(), label.text()[:30], round(ratio, 2))
    assert seen > 20
