"""Spatial's light and colours, one dict per mode.

DARK is the look exactly as it shipped: frosted glass over a dusk. LIGHT is the same room by day:
a bright airy backdrop (pastel sky, cream, soft peach and mint glows), white frosted panes at about
60% tint, dark type, rim light and softer, bluer shadows. `gain` multiplies the alpha of every white
wash (white on white shows nothing, so the light variant uses stronger washes plus a faint hairline);
tuples are (r, g, b, a), everything else a hex string.
"""

DARK = dict(
    # type and accents
    ink="#ffffff", body="#f3f0fd", meta="#d6d2ea", side_ink="#ffffff", side_meta="#e2dff2",
    accent="#8bb0ff", green="#5fe58c", strong_glyph="#ffffff", error_ink="#ffaaa3", ok_ink="#8ff2b4",
    # the environment
    sky=((0.0, "#150f40"), (0.5, "#2b1c6a"), (1.0, "#5a2a72")),
    glows=((0.84, 1.02, 0.78, (255, 140, 98), 215), (0.06, 0.98, 0.60, (30, 205, 190), 175),
           (0.52, -0.06, 0.70, (116, 84, 240), 125), (0.98, 0.10, 0.46, (255, 104, 186), 125),
           (0.44, 0.62, 0.50, (214, 96, 200), 95), (0.02, 0.16, 0.44, (70, 170, 255), 105)),
    bokeh=("#ffb38a", "#9ad7ff", "#c9a8ff", "#ff9fd0", "#8fffe0"), bokeh_gain=1.0,
    vignette=(8, 4, 28, 105), grain=("#ffffff", 9),
    # glass
    gain=1.0, hair=(0, 0, 0, 0), shade=(6, 2, 22), shadow_gain=1.0,
    pane_tint=(14, 8, 38, 134), pane_sheen=22, pane_lamp=18, pane_rim=150, pane_rim2=26,
    head_wash=(14, 4), head_line=(255, 255, 255, 40),
    halo=(204, 192, 255), halo_gain=1.0, bed=(17, 5),
    # controls
    tog_base=None, tog_on=205, tog_wash=((54, 24), (70, 20)), row_tint=None,   # wash: (off, on) x (top, bottom)
    pill_base=(10, 6, 30, 150), pill_wash=52, orb_dark=205,
    pills={"good": ("#8ff2b4", "#2fc46e"), "bad": ("#ffb0aa", "#ff5a50"), "warn": ("#ffd98a", "#f5b02e"),
           "quiet": ("#d9d5ee", "#b4aedc"), "idea": ("#cdbdff", "#9a7bff")},
    me_tint=("#3d56d4", 160),
    text_shadows={"headerTitle": (0, 1, "#59000000"), "panelTitle": (0, 1, "#59000000"),
                  "tileName": (0, 1, "#66000000"), "rowTitle": (0, 1, "#59000000")},
    # stylesheet
    me_ink="#ffffff", tip_bg="#261e55", tip_ink="#ffffff", tip_edge="rgba(255, 255, 255, 80)",
    search=("rgba(255, 255, 255, 32)", "rgba(255, 255, 255, 80)", "rgba(255, 255, 255, 130)",
            "rgba(255, 255, 255, 52)"),
    field=("rgba(14, 8, 40, 92)", "rgba(255, 255, 255, 70)", "rgba(255, 255, 255, 36)",
           "rgba(255, 255, 255, 110)", "rgba(14, 8, 40, 128)"),
    quiet=("rgba(255, 255, 255, 34)", "rgba(255, 255, 255, 85)", "rgba(255, 255, 255, 150)",
           "rgba(255, 255, 255, 56)", "rgba(255, 255, 255, 20)"),
    sb=("rgba(255, 255, 255, 70)", "rgba(255, 255, 255, 120)"),
    menu=("#2a2160", "rgba(255, 255, 255, 90)", "rgba(255, 255, 255, 46)"),
    # the Mode control
    # the look chip's miniature
    pv_pane=(22, 14, 52, 120), pv_me=("#4d6cf0", 170),
)

LIGHT = dict(
    DARK,
    ink="#1c1c22", body="#32323c", meta="#545462", side_ink="#1c1c22", side_meta="#4e4e5e",
    accent="#3558dc", green="#1fa55a", error_ink="#b3261e", ok_ink="#146c38",
    sky=((0.0, "#cfe4ff"), (0.5, "#f1ecff"), (1.0, "#ffe5d6")),
    glows=((0.86, 1.00, 0.80, (255, 190, 150), 190), (0.04, 0.98, 0.62, (140, 232, 205), 170),
           (0.52, -0.08, 0.72, (150, 190, 255), 150), (0.98, 0.08, 0.48, (255, 182, 214), 150),
           (0.44, 0.62, 0.50, (226, 190, 255), 100), (0.02, 0.14, 0.46, (160, 215, 255), 140)),
    bokeh=("#ffd2b4", "#bfe6ff", "#e2d2ff", "#ffc9e2", "#c4fff0"), bokeh_gain=1.3,
    vignette=(150, 140, 205, 46), grain=("#7a70a8", 7),
    gain=2.6, hair=(76, 66, 150, 46), shade=(78, 66, 150), shadow_gain=0.55,
    pane_tint=(255, 255, 255, 150), pane_sheen=70, pane_lamp=60, pane_rim=235, pane_rim2=90,
    head_wash=(70, 22), head_line=(80, 70, 150, 40),
    halo=(150, 130, 255), halo_gain=0.8, bed=(110, 50),
    tog_base=(104, 104, 158, 128), tog_on=232, tog_wash=((40, 10), (56, 14)), row_tint=(62, 90, 230, 44),
    pill_base=(255, 255, 255, 200), pill_wash=64, orb_dark=165,
    pills={"good": ("#0b6a3a", "#2fc46e"), "bad": ("#a8231b", "#ff5a50"), "warn": ("#7f4b00", "#f5b02e"),
           "quiet": ("#46465a", "#8e88c0"), "idea": ("#5230b5", "#9a7bff")},
    me_tint=("#3249c8", 240),
    text_shadows={},
    tip_bg="#2b2a4a", tip_edge="rgba(255, 255, 255, 60)",
    search=("rgba(255, 255, 255, 150)", "rgba(76, 66, 150, 60)", "rgba(255, 255, 255, 230)",
            "rgba(255, 255, 255, 235)"),
    field=("rgba(255, 255, 255, 175)", "rgba(76, 66, 150, 80)", "rgba(76, 66, 150, 100)",
           "rgba(76, 66, 150, 60)", "rgba(255, 255, 255, 235)"),
    quiet=("rgba(255, 255, 255, 150)", "rgba(76, 66, 150, 70)", "rgba(255, 255, 255, 230)",
           "rgba(255, 255, 255, 215)", "rgba(255, 255, 255, 100)"),
    sb=("rgba(60, 50, 130, 80)", "rgba(60, 50, 130, 130)"),
    menu=("#fbfaff", "rgba(76, 66, 150, 90)", "rgba(62, 90, 230, 30)"),
    pv_pane=(255, 255, 255, 140), pv_me=("#3249c8", 240),
)
