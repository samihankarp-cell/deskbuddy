"""Classic's colours, one dict per mode. LIGHT is the look exactly as it shipped; DARK is the
Grok-style night version (near-black window, a slightly lighter sidebar, hairlines, grey bubbles, a
white order bubble with black type). Same layout, same blob colours."""

LIGHT = dict(
    ink="#111111", body="#3a3a3f", meta="#6e6e73", side_ink="#111111", side_meta="#6e6e73",
    accent="#2d8cff", green="#22c55e", strong_glyph="#ffffff", error_ink="#b3261e", ok_ink="#15803d",
    bg="#ffffff", side_bg="#f6f6f7", line="#ebebeb", bubble="#f1f1f2", hover="#ececee",
    select="#e6e6e9", edge="#dcdce0", row_hot="#ededef", card="#f6f6f7", composer="#ffffff",
    field="#ffffff", quiet="#ffffff", menu="#ffffff", tile="#ececee", preview="#f1f1f2",
    me_fill="#111111", me_ink="#ffffff", on_ink="#ffffff", primary_hot="#33333a",
    primary_down="#000000", tip_bg="#111111", tip_ink="#ffffff", sb="#d4d4d8", sb_hot="#b9b9bf",
    toggle_off="#cfcfd4", knob_on="#ffffff", knob_off="#ffffff", seg_track="#ececee", seg_on="#ffffff",
    seg_edge="#dcdce0",
    pills={"good": ("#15803d", "#e6f6ec"), "bad": ("#b3261e", "#fdecea"), "warn": ("#8a5a00", "#fff1cf"),
           "quiet": ("#6e6e73", "#ececee"), "idea": ("#5b3f99", "#efeafd")},
)

DARK = dict(
    LIGHT,
    ink="#f2f2f4", body="#d2d2d8", meta="#9a9aa2", side_ink="#f2f2f4", side_meta="#9a9aa2",
    accent="#5aa2ff", strong_glyph="#0e0e10", error_ink="#ff8a80", ok_ink="#4ade80",
    bg="#0e0e10", side_bg="#151517", line="#26262a", bubble="#1f1f23", hover="#222226",
    select="#2a2a2f", edge="#33333a", row_hot="#1d1d21", card="#151517", composer="#151517",
    field="#151517", quiet="#1f1f23", menu="#1a1a1d", tile="#1f1f23", preview="#1f1f23",
    me_fill="#ffffff", me_ink="#0e0e10", on_ink="#0e0e10", primary_hot="#d9d9dd", primary_down="#c4c4c9",
    tip_bg="#2a2a30", tip_ink="#f2f2f4", sb="#3a3a40", sb_hot="#55555d", toggle_off="#3c3c43",
    knob_on="#0e0e10", knob_off="#e9e9ee", seg_track="#1f1f23", seg_on="#3a3a41", seg_edge="#33333a",
    pills={"good": ("#6ee7a0", "#12301f"), "bad": ("#ff9d94", "#3a1714"), "warn": ("#f5c868", "#33280d"),
           "quiet": ("#a8a8b0", "#26262b"), "idea": ("#c4b0ff", "#2a2145")},
)
