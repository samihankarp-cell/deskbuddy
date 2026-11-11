"""Which key is the hold-to-talk key, and does a keyboard event belong to it?

The `keyboard` library finds a key by scan code. On Windows the left and right Ctrl (and Alt)
share one scan code, so binding "right ctrl" by scan code also fires for the left one. Here the
event's own NAME is compared instead: the library names the right-hand keys "right ctrl" and
"right alt", and the left-hand ones plain "ctrl" / "alt" (or "left ctrl" / "left alt").
"""
DEFAULT = "right ctrl"

# Names a physical key can show up as, per hotkey. Anything not listed matches by plain name.
_ALIASES = {
    "left ctrl": {"left ctrl", "ctrl"},
    "left alt": {"left alt", "alt", "left menu"},
    "left shift": {"left shift", "shift"},
    "right alt": {"right alt", "right menu", "alt gr"},   # AltGr keyboards report "alt gr"
    "ctrl": {"ctrl", "left ctrl", "right ctrl"},          # no side given: either one
    "alt": {"alt", "left alt", "right alt", "alt gr"},
    "shift": {"shift", "left shift", "right shift"},
    "windows": {"windows", "left windows", "right windows"},
}


def normalize(name: str) -> str:
    """The library's spelling of a key name ("Right Ctrl" -> "right ctrl"); the default if empty."""
    name = " ".join((name or "").lower().split())
    if not name:
        return DEFAULT
    try:
        from keyboard._canonical_names import normalize_name

        return normalize_name(name)
    except Exception:  # the library is only needed on the machine that listens
        return name


def friendly(name: str) -> str:
    """"right ctrl" -> "Right Ctrl", for showing to a person."""
    return normalize(name).title()


def matches(event, hotkey: str) -> bool:
    """True when this keyboard event is the (given) hotkey. Left and right never mix."""
    name = getattr(event, "name", None)
    if not name:
        return False
    hotkey = normalize(hotkey)
    return name in _ALIASES.get(hotkey, {hotkey})


def is_escape(event) -> bool:
    return getattr(event, "name", None) == "esc"
