"""Skeuomorphic's materials and colours, one dict per mode.

LIGHT is the look exactly as it shipped: walnut leather, linen, brushed steel, paper cards, brass.
DARK is the same room at night: charcoal-walnut leather, slate fabric with a faint weave, gunmetal
header, smoked-leather cards, cognac capsules for orders, a green-black felt case, a leather-bound
notepad. Brass stays brass. Tuples are (r, g, b, a); everything else is a hex string.
"""

LIGHT = dict(
    # text
    ink="#2a2017", body="#463a2b", meta="#5a4c38", side_ink="#f8edd8", side_meta="#e4d2b0",
    accent="#2f7fd6", green="#3da64a", strong_glyph="#fbf1de", error_ink="#a5231b", ok_ink="#1a6128",
    me_ink="#fbf1de", tip_bg="#2b2017", tip_ink="#f6ebd6", tip_edge="#120b05",
    # window and the three columns
    win="#2b1a0e", leather="#5a3a24", side_glow=(255, 226, 180, 34),
    linen="#eee5d1", linen_r="#e6d9bf", weave=1.0, vig_c=(90, 60, 20, 46), vig_r=(90, 60, 20, 50),
    r_shade=(60, 36, 10, 80), r_line=(70, 44, 14, 150), r_hi=(255, 255, 255, 70),
    # header (brushed metal), composer / form wells
    head_top="#f7f3ea", head_bot="#d2c9b6", head_hi=(255, 255, 255, 230), head_lo=(110, 92, 64, 210),
    head_shade=(60, 36, 10, 80), brush=1.0,
    well_top="#e2d6bb", well_bot="#f8f2e4", well_edge="#a99878", lip=(255, 255, 255, 200),
    form_top="#dcd0b5", form_bot="#e8dec6", form_edge="#bba98a", form_hi=(255, 255, 255, 190),
    # cards, notes and the user's capsules
    shadow=(60, 36, 12), card_top="#fffcf3", card_bot="#f4ecd9", card_edge="#d3c4a4",
    card_hi=(255, 255, 255, 215), note_top="#f8efd7", note_bot="#eadfc0", note_edge="#cbb991",
    me_top="#665040", me_mid="#4a3727", me_bot="#2b1e15", me_edge="#170d06", me_gloss=84,
    me_rim=(255, 235, 205, 60), me_shadow=60,
    # Kettle's case and the routines notepad
    felt="#27493f", pad_top="#fffcf1", pad_bot="#f6eedb", pad_edge="#cdbd9a",
    strip_top="#dcc99f", strip_bot="#bfa874", strip_lo=(110, 86, 46, 150), strip_hi=(255, 255, 255, 120),
    hole_hi=(255, 255, 255, 150), hole="#3b2a18", rule=(78, 118, 170, 85),
    # round buttons: "soft" (paper) and "strong" (the main disc)
    soft=("#fffaf0", "#dccfb3", "#a8977a"), soft_hot=("#ffffff", "#e5d9bf", "#a8977a"), soft_gloss=120,
    strong=("#6a503d", "#2c1f15", "#150c05"), strong_hot=("#7b604c", "#38271b", "#150c05"), strong_gloss=95,
    # toggle
    tog_off=("#b7a98c", "#dacfb6", "#8a7a5b"), tog_hi=(255, 255, 255, 190),
    # stamps (verdict pills) and the engraved text
    pills={"good": ("#1b6b35", "#e1efdf"), "bad": ("#a5231b", "#f5dfd6"), "warn": ("#7a4f00", "#f5e6bd"),
           "quiet": ("#5b4e3b", "#e6dcc5"), "idea": ("#54398f", "#e8e0f2")},
    stamp_hi=(255, 255, 255, 170),
    text_shadows={"headerTitle": (0, 1, "#e6ffffff"), "panelTitle": (0, 1, "#e6ffffff"),
                  "tileName": (0, 1, "#b3000000"), "rowTitle": (0, 1, "#99000000"),
                  "pill": (0, 1, "#cfffffff")},
    # stylesheet: inputs, buttons, scroll bars, menus. (a, b) are gradient top / bottom.
    field=("#d9ccb1", "#f3ecdb"), field_edge=("#b2a283", "#8f7f5f", "#d3c6a8"), field_sel=("#4a3524", "#fbf1de"),
    primary=("#7a5d49", "#3a281b"), primary_hot=("#8a6b55", "#46311f"), primary_down=("#2e2016", "#4a3524"),
    primary_edge=("#1c1007", "#a88a70", "#120a04"), primary_ink="#fbf1de",
    quiet=("#fffaf0", "#e6d9bf"), quiet_hot=("#ffffff", "#efe3ca"), quiet_down=("#d9ccb0", "#efe4cc"),
    quiet_edge=("#b3a182", "#fffdf6", "#8f7f60"),
    sb_track="rgba(90, 60, 30, 34)", sb=("#e3d9c3", "#b9aa8a", "#968665"), sb_edge="#7a6a4c",
    sb_hot=("#efe6d2", "#c9bb9c", "#a89877"),
    menu="#fbf5e8", menu_edge="#8f7f60", menu_pick=("#7a5d49", "#3a281b"), menu_pick_ink="#fbf1de",
    # the Mode control
    seg_track=("#d9ccb1", "#f3ecdb", "#b2a283"), seg_on=("#fffaf0", "#e6d9bf", "#a8977a"),
    # the look chip's miniature
    pv_linen="#eee5d1", pv_paper=("#fffcf3", "#f1e8d3", "#d3c4a4"), pv_side=("#6a4630", "#46291a"),
    pv_me=("#665040", "#2b1e15", "#170d06"), pv_well=("#e2d6bb", "#f8f2e4", "#a99878"),
    pv_rows=(255, 226, 180, 90),
)

DARK = dict(
    LIGHT,
    ink="#f3e8d3", body="#dccfb6", meta="#b9ab90", accent="#5aa0ee", error_ink="#ff9d8e", ok_ink="#86d99a",
    tip_bg="#3a2e22", tip_edge="#0c0805", tip_ink="#f6ebd6",
    win="#14100c", leather="#2d2019", side_glow=(255, 226, 180, 20),
    linen="#272b32", linen_r="#23262c", weave=0.5, vig_c=(0, 0, 0, 70), vig_r=(0, 0, 0, 70),
    r_shade=(0, 0, 0, 110), r_line=(0, 0, 0, 200), r_hi=(255, 255, 255, 20),
    head_top="#575c65", head_bot="#2d3137", head_hi=(255, 255, 255, 70), head_lo=(6, 7, 9, 235),
    head_shade=(0, 0, 0, 130), brush=0.55,
    well_top="#1a1c20", well_bot="#2a2d33", well_edge="#0b0c0e", lip=(255, 255, 255, 34),
    form_top="#1d1f24", form_bot="#272a31", form_edge="#0d0e10", form_hi=(255, 255, 255, 30),
    shadow=(0, 0, 0), card_top="#41352b", card_bot="#33291f", card_edge="#120c08", card_hi=(255, 226, 180, 62),
    note_top="#403a2c", note_bot="#332e22", note_edge="#14100a",
    me_top="#9c6034", me_mid="#7b4824", me_bot="#552f17", me_edge="#241206", me_gloss=52,
    me_rim=(255, 214, 170, 50), me_shadow=110,
    felt="#0e211b", pad_top="#3b2f26", pad_bot="#2e241d", pad_edge="#100a06",
    strip_top="#8d7138", strip_bot="#5f4a24", strip_lo=(0, 0, 0, 170), strip_hi=(255, 226, 150, 80),
    hole_hi=(255, 226, 150, 60), hole="#0b0704", rule=(220, 190, 140, 46),
    soft=("#50473c", "#2f2921", "#0e0a06"), soft_hot=("#5e5447", "#3a3228", "#0e0a06"), soft_gloss=60,
    strong=("#a6683a", "#693a1c", "#1a0d04"), strong_hot=("#b57a4a", "#764322", "#1a0d04"), strong_gloss=70,
    tog_off=("#1f1b16", "#3a342b", "#0b0907"), tog_hi=(255, 255, 255, 38),
    pills={"good": ("#94e6a8", "#2f6b3f"), "bad": ("#ffc0b3", "#7a2b22"), "warn": ("#f6d684", "#7a5a12"),
           "quiet": ("#e4dac4", "#6a5e4a"), "idea": ("#d9cdf8", "#5a4390")},
    stamp_hi=(255, 255, 255, 26),
    text_shadows={"headerTitle": (0, -1, "#cc000000"), "panelTitle": (0, -1, "#cc000000"),
                  "tileName": (0, 1, "#b3000000"), "rowTitle": (0, 1, "#99000000"),
                  "pill": (0, 1, "#80000000")},
    field=("#17191d", "#262930"), field_edge=("#0b0c0e", "#08090a", "#3c4048"), field_sel=("#8a5028", "#fbf1de"),
    primary=("#9c6034", "#5e3318"), primary_hot=("#ab6f42", "#6a3a1d"), primary_down=("#4f2b14", "#74441f"),
    primary_edge=("#2a1608", "#c9976a", "#1a0d04"),
    quiet=("#4c4338", "#332c24"), quiet_hot=("#5a5043", "#3d352b"), quiet_down=("#2a241d", "#40372d"),
    quiet_edge=("#16110c", "#6d6252", "#0d0a07"),
    sb_track="rgba(0, 0, 0, 70)", sb=("#6a6e76", "#4a4d54", "#383b41"), sb_edge="#14161a",
    sb_hot=("#7d818a", "#5a5e66", "#464950"),
    menu="#2a241e", menu_edge="#0e0a06", menu_pick=("#9c6034", "#5e3318"),
    seg_track=("#16181c", "#23262c", "#0b0c0e"), seg_on=("#5a5043", "#3a3228", "#0e0a06"),
    pv_linen="#272b32", pv_paper=("#41352b", "#33291f", "#120c08"), pv_side=("#3a2a20", "#221810"),
    pv_me=("#9c6034", "#552f17", "#241206"), pv_well=("#1a1c20", "#2a2d33", "#0b0c0e"),
    pv_rows=(255, 226, 180, 80),
)
