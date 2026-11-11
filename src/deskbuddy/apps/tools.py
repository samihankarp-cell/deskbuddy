"""Desktop app tools: open any installed app and work it with real mouse and keyboard."""
import base64
import difflib
import io
import re
import subprocess
import time

from langchain_core.messages import HumanMessage

from deskbuddy.apps import win
from deskbuddy.brain.tools import Ctx, Outcome, tool

SETTINGS_LIKE = re.compile(r"\b(settings|control panel|registry|regedit|group policy|device manager|services)\b", re.I)
USEFUL = {"Button", "Edit", "MenuItem", "ListItem", "TabItem", "CheckBox", "RadioButton",
          "ComboBox", "Hyperlink", "TreeItem", "Document", "SplitButton", "MenuBar"}
SCREEN_WIDTH = 1280  # screenshots are shrunk to this width before the model sees them


def _com() -> None:
    """Each thread must switch Windows' COM on before using accessibility."""
    import comtypes

    try:
        comtypes.CoInitialize()
    except OSError:
        pass


def find_app(name: str) -> tuple[dict | None, list[str]]:
    apps = win.installed_apps()
    wanted = name.strip().lower()
    by_name = {a["Name"].lower(): a for a in apps}
    if wanted in by_name:
        return by_name[wanted], []
    starts = [a for a in apps if a["Name"].lower().startswith(wanted)]
    inside = [a for a in apps if wanted in a["Name"].lower()]
    for group in (starts, inside):
        if group:
            return min(group, key=lambda a: len(a["Name"])), []
    close = difflib.get_close_matches(wanted, by_name, n=3, cutoff=0.6)
    if close and difflib.SequenceMatcher(None, wanted, close[0]).ratio() >= 0.85:
        return by_name[close[0]], []
    return None, [by_name[c]["Name"] for c in close]


def _target(ctx: Ctx):
    """The window this job is working in."""
    _com()
    from pywinauto import Desktop

    hwnd = getattr(ctx, "app_hwnd", None)
    if not hwnd or hwnd not in win.windows():
        hwnd = win.foreground()
        if hwnd not in win.windows():
            raise RuntimeError("no app window is in front; use app_open first")
        ctx.app_hwnd = hwnd
    return Desktop(backend="uia").window(handle=hwnd)


def window_text(ctx: Ctx, limit: int = 1500) -> str:
    """What the job's window shows now (used as fresh evidence by the checker)."""
    try:
        window = _target(ctx)
        parts = [window.window_text()]
        for item in window.descendants()[:400]:
            kind = item.element_info.control_type
            if kind in ("Edit", "Document", "Text"):
                value = ""
                try:
                    value = item.get_value() if kind != "Text" else ""
                except Exception:
                    pass
                text = (value or item.window_text() or "").strip()
                if text:
                    parts.append(text[:300])
        return " | ".join(parts)[:limit]
    except Exception as error:
        return f"(could not read the window: {error})"


@tool("app_open", "Open an app installed on this PC by its name. Says so if it is not installed.",
      {"name": "string: the app's name, e.g. Notepad, Spotify, Calculator"},
      label=lambda a: f"Opening {a.get('name', 'the app')}",
      risk=lambda _c, a: (f"open {a.get('name')} (this is where Windows settings are changed)"
                          if SETTINGS_LIKE.search(a.get("name", "")) else None))
def app_open(ctx: Ctx, name: str) -> Outcome:
    app, close = find_app(name)
    if app is None:
        hint = f" The closest names I have are: {', '.join(close)}." if close else ""
        return Outcome(False, f"{name} is not installed on this PC.{hint}",
                       stop_reason=f"{name} isn't installed on this PC")
    ctx.places.add(app["Name"].lower())
    ctx.used_app = True
    before = win.windows()
    subprocess.Popen(["explorer.exe", f"shell:AppsFolder\\{app['AppID']}"])
    words = [w for w in re.split(r"\W+", app["Name"].lower()) if len(w) > 2]
    for _ in range(24):
        time.sleep(0.5)
        now = win.windows()
        fresh = [h for h in now if h not in before]
        named = [h for h, t in now.items() if any(w in t.lower() for w in words)]
        hit = next((h for h in fresh if h in named), None) or (fresh[0] if fresh else None) \
            or (win.foreground() if win.foreground() in named else None)
        if hit:
            ctx.app_hwnd = hit
            return Outcome(True, f"{app['Name']} is open. Its window is titled \"{now[hit]}\".", True)
    return Outcome(True, f"I started {app['Name']} but I cannot see a window for it yet.")


@tool("app_look", "List the buttons, boxes and menus of the app window being worked on, numbered.",
      {}, label=lambda a: "Looking at the app", reads_only=True)
def app_look(ctx: Ctx) -> Outcome:
    window = _target(ctx)
    ctx.used_app = True
    ctx.controls = {}
    lines = []
    for item in window.descendants():
        info = item.element_info
        kind = info.control_type
        if kind not in USEFUL:
            continue
        name = (info.name or "").strip()
        if not name and kind not in ("Edit", "Document"):
            continue
        try:
            if not item.is_visible() or not item.is_enabled():
                continue
        except Exception:
            continue
        number = len(ctx.controls)
        ctx.controls[number] = item
        lines.append(f"[{number}] {kind} \"{name[:70]}\"")
        if number >= 119:
            break
    title = window.window_text()
    if not lines:
        return Outcome(True, f"Window \"{title}\" exposes no controls. Use screen_look and "
                       "screen_click instead.", verified=True)
    return Outcome(True, f"Window \"{title}\":\n" + "\n".join(lines), verified=True)


@tool("app_click", "Click a control by its number from app_look, with the real mouse.",
      {"id": "integer: the control number"}, label=lambda a: "Clicking", physical=True)
def app_click(ctx: Ctx, id: int) -> Outcome:
    _com()
    control = ctx.controls.get(id)
    if control is None:
        return Outcome(False, "Unknown control number. Call app_look first.")
    name = (control.element_info.name or control.element_info.control_type)[:40]
    ctx.step(f"Clicking {name}")
    control.click_input()
    time.sleep(0.6)
    return Outcome(True, f"Clicked \"{name}\". The window in front is now "
                   f"\"{win.foreground_title()}\". Call app_look to see the result.")


def _focus(ctx: Ctx) -> None:
    try:
        _target(ctx).set_focus()
        time.sleep(0.25)
    except Exception:
        pass


@tool("app_type", "Type text with the real keyboard into the app (into whatever has focus; "
      "click a box first if needed).", {"text": "string: what to type"},
      label=lambda a: f"Typing {a.get('text', '')[:30]}", physical=True)
def app_type(ctx: Ctx, text: str) -> Outcome:
    import keyboard

    ctx.used_app = True
    _focus(ctx)
    keyboard.write(text, delay=0.012)
    time.sleep(0.3)
    shown = text.strip()[:40].lower() in window_text(ctx, 4000).lower()
    return Outcome(True, "Typed it, and the window now shows that text." if shown
                   else "Typed it, but I cannot see that text in the window.", verified=shown)


@tool("app_keys", "Press a key or shortcut in the app, e.g. enter, ctrl+s, alt+f4, tab.",
      {"keys": "string: the key or shortcut"},
      label=lambda a: f"Pressing {a.get('keys', '')}", physical=True)
def app_keys(ctx: Ctx, keys: str) -> Outcome:
    import keyboard

    ctx.used_app = True
    _focus(ctx)
    keyboard.send(keys.lower().replace(" ", ""))
    time.sleep(0.5)
    return Outcome(True, f"Pressed {keys}. The window in front is now \"{win.foreground_title()}\".")


def _screenshot(ctx: Ctx):
    import pyautogui

    image = pyautogui.screenshot()
    ctx.screen_scale = image.width / SCREEN_WIDTH
    return image.resize((SCREEN_WIDTH, int(image.height / ctx.screen_scale)))


@tool("screen_look", "Look at the whole screen with vision and answer a question about it, "
      "for apps that app_look cannot see into. Ask for the x,y of things you need to click.",
      {"question": "string: what you want to know or find on screen"},
      label=lambda a: "Looking at the screen", reads_only=True)
def screen_look(ctx: Ctx, question: str) -> Outcome:
    from deskbuddy.brain.llm import agent_model, text_of

    ctx.used_app = True
    image = _screenshot(ctx)
    buffer = io.BytesIO()
    image.convert("RGB").save(buffer, format="JPEG", quality=80)
    data = base64.b64encode(buffer.getvalue()).decode()
    reply = agent_model(ctx.settings).invoke([HumanMessage(content=[
        {"type": "text", "text": f"This is a screenshot, {image.width}x{image.height} pixels. "
         f"{question} When you name something clickable, give its centre as x,y in pixels of "
         "this image. Describe only what you can actually see."},
        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{data}"}},
    ])])
    return Outcome(True, text_of(reply), verified=True)


@tool("screen_click", "Click a point on the screen, using x,y from screen_look.",
      {"x": "integer: x in the screen_look image", "y": "integer: y in the screen_look image"},
      label=lambda a: "Clicking on screen", physical=True)
def screen_click(ctx: Ctx, x: int, y: int) -> Outcome:
    import pyautogui

    scale = getattr(ctx, "screen_scale", None)
    if scale is None:
        return Outcome(False, "Call screen_look first so I know where things are.")
    pyautogui.click(int(x * scale), int(y * scale))
    time.sleep(0.6)
    return Outcome(True, f"Clicked at {x},{y}. The window in front is now "
                   f"\"{win.foreground_title()}\". Use screen_look to see the result.")
