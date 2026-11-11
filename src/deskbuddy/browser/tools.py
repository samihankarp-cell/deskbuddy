"""Browser tools. They work in the user's own open browser through the add-on."""
import re
import time
import webbrowser
from urllib.parse import quote_plus, urlparse

from deskbuddy.brain.tools import Ctx, Outcome, tool

BUY = re.compile(r"\b(buy|pay|purchase|place (your )?order|check ?out|complete (order|purchase)|subscribe now|order now)\b", re.I)
SEND = re.compile(r"^\s*(send|post|reply|publish|tweet|submit)\b", re.I)
SIGN_IN = re.compile(r"\b(sign in|log in|login|signin)\b", re.I)
NO_ADDON = ("The Desk Buddy add-on is not connected in the open browser, so I cannot work inside "
            "its pages. give_up and say the add-on needs to be installed (see the addon folder).")


def _host(url: str) -> str:
    return (urlparse(url).hostname or "").removeprefix("www.")


def _place(ctx: Ctx, url: str) -> None:
    host = _host(url)
    if not host:
        return
    ctx.places.add("gmail" if host.startswith("mail.google") else host.split(".")[-2] if "." in host else host)


def _tab(ctx: Ctx) -> int:
    if ctx.tab_id is None:
        ctx.tab_id = ctx.bridge.call("active")["tabId"]
    return ctx.tab_id


def _where(info: dict) -> str:
    return f"Now at {info.get('url')} (title: {info.get('title')})"


def _needs_addon(fn):
    def wrapped(ctx: Ctx, **args) -> Outcome:
        if not ctx.bridge.connected:
            return Outcome(False, NO_ADDON)
        return fn(ctx, **args)

    wrapped.__name__ = fn.__name__
    return wrapped


def _open(ctx: Ctx, url: str, new_window: bool) -> Outcome:
    blank = url.strip().lower() in ("", "about:blank", "newtab", "new tab", "blank", "chrome://newtab")
    if blank:
        if not ctx.bridge.connected:
            return Outcome(False, NO_ADDON)
        info = ctx.bridge.call("open", url="", newWindow=bool(new_window))
        ctx.tab_id = info["tabId"]
        return Outcome(True, f"Opened an empty new tab in {ctx.bridge.browser}.", verified=True)
    if not re.match(r"^[a-z]+:", url, re.I):
        url = "https://" + url
    _place(ctx, url)
    if not ctx.bridge.connected:
        webbrowser.open_new_tab(url)
        return Outcome(True, "I asked your default browser to open it, but the Desk Buddy add-on "
                       "is not connected, so I cannot confirm it opened or do anything on the page.")
    info = ctx.bridge.call("open", url=url, newWindow=bool(new_window))
    ctx.tab_id = info["tabId"]
    _place(ctx, info.get("url", ""))
    landed = bool(_host(info.get("url", "")))
    return Outcome(landed, f"Opened in {ctx.bridge.browser}. {_where(info)}", verified=landed)


@tool("browser_open", "Open a website in a new tab of the user's browser (or a new window). "
      "For just an empty new tab, pass an empty url.",
      {"url": "string: the address, or empty for an empty new tab", "new_window?": "boolean: true to use a separate window"},
      label=lambda a: f"Opening {_host(a.get('url', '')) or _host('https://' + a.get('url', '')) or 'the site'}")
def browser_open(ctx: Ctx, url: str, new_window: bool = False) -> Outcome:
    return _open(ctx, url, new_window)


@tool("browser_search", "Search the web in a new tab.",
      {"query": "string: what to search for", "new_window?": "boolean: true to use a separate window"},
      label=lambda a: f"Searching for {a.get('query', '')[:40]}")
def browser_search(ctx: Ctx, query: str, new_window: bool = False) -> Outcome:
    return _open(ctx, "https://www.google.com/search?q=" + quote_plus(query), new_window)


@tool("browser_look", "List the clickable and typable things on the current page, numbered. "
      "Always do this before browser_click or browser_type.", {},
      label=lambda a: "Looking at the page", reads_only=True)
@_needs_addon
def browser_look(ctx: Ctx) -> Outcome:
    page = ctx.bridge.call("look", tabId=_tab(ctx))
    ctx.elements = {e["id"]: e for e in page["elements"]}
    lines = []
    for e in page["elements"]:
        kind = e["tag"] + (f":{e['type']}" if e["type"] and e["type"] != e["tag"] else "")
        extra = f" ({e['label']})" if e["label"] and e["label"] != e["text"] else ""
        lines.append(f"[{e['id']}] {kind} \"{e['text']}\"{extra}{'' if e['inView'] else ' (off screen)'}")
    head = (f"{page['title']} | {page['url']} | scrolled {page['scrollY']} of "
            f"{page['pageHeight']}\n")
    return Outcome(True, head + ("\n".join(lines) or "(nothing clickable found)"), verified=True)


def _click_risk(ctx: Ctx, args: dict) -> str | None:
    element = ctx.elements.get(args.get("id"))
    if not element:
        return None
    text = f"{element['text']} {element['label']}".strip()
    if BUY.search(text):
        return f"press \"{element['text'] or element['label']}\" (this looks like buying something)"
    if SEND.search(element["text"]) or SEND.search(element["label"]):
        return f"press \"{element['text'] or element['label']}\" (this sends something)"
    if SIGN_IN.search(text):
        return f"press \"{element['text'] or element['label']}\" (this signs in)"
    return None


def _snapshot(ctx: Ctx) -> str:
    page = ctx.bridge.call("text", tabId=_tab(ctx), max=4000)
    return f"{page['url']}|{page['title']}|{page['text']}"


@tool("browser_click", "Click an element by its number from browser_look.",
      {"id": "integer: the element number"},
      label=lambda a: "Clicking", risk=_click_risk)
@_needs_addon
def browser_click(ctx: Ctx, id: int) -> Outcome:
    element = ctx.elements.get(id)
    if element is None:
        return Outcome(False, "Unknown element number. Call browser_look first.")
    name = element["text"] or element["label"] or "it"
    ctx.step(f"Clicking {name[:40]}")
    before = _snapshot(ctx)
    result = ctx.bridge.call("click", tabId=_tab(ctx), id=id)
    if result.get("newTab"):
        ctx.tab_id = result["tabId"]
    _place(ctx, result.get("url", ""))
    changed = _snapshot(ctx) != before
    note = "The page changed." if changed else "The page did not visibly change."
    return Outcome(True, f"Clicked \"{name}\". {_where(result)}. {note}", verified=changed)


@tool("browser_type", "Type text into a box by its number from browser_look. Replaces what "
      "was there. For a dropdown, gives the option to choose.",
      {"id": "integer: the element number", "text": "string: what to type",
       "press_enter?": "boolean: press Enter afterwards"},
      label=lambda a: f"Typing {a.get('text', '')[:30]}")
@_needs_addon
def browser_type(ctx: Ctx, id: int, text: str, press_enter: bool = False) -> Outcome:
    element = ctx.elements.get(id)
    if element is None:
        return Outcome(False, "Unknown element number. Call browser_look first.")
    if element["type"] == "password":
        return Outcome(False, "That is a password box. I never type passwords. give_up and "
                       "tell the user the page is waiting for their password.")
    result = ctx.bridge.call("type", tabId=_tab(ctx), id=id, text=text, enter=bool(press_enter))
    held = text.strip().lower() in str(result.get("value", "")).lower()
    tail = f" Pressed Enter. {_where(result)}." if press_enter else ""
    return Outcome(held, (f"The box now holds \"{result.get('value', '')[:80]}\"." if held
                          else "The box did not take the text.") + tail, verified=held)


@tool("browser_scroll", "Scroll the current page.",
      {"direction": "string: down, up, top or bottom"},
      label=lambda a: f"Scrolling {a.get('direction', 'down')}")
@_needs_addon
def browser_scroll(ctx: Ctx, direction: str = "down") -> Outcome:
    result = ctx.bridge.call("scroll", tabId=_tab(ctx), direction=direction)
    moved = result["after"] != result["before"]
    return Outcome(True, f"Scrolled from {result['before']} to {result['after']} of "
                   f"{result['pageHeight']}." + ("" if moved else " Already at the end."), verified=moved)


@tool("browser_back", "Go back one page in the current tab.", {}, label=lambda a: "Going back")
@_needs_addon
def browser_back(ctx: Ctx) -> Outcome:
    before = ctx.bridge.call("info", tabId=_tab(ctx))["url"]
    info = ctx.bridge.call("back", tabId=_tab(ctx))
    moved = info["url"] != before
    return Outcome(moved, _where(info) if moved else "There was no earlier page to go back to.", moved)


@tool("browser_close_tab", "Close the current tab.", {}, label=lambda a: "Closing the tab")
@_needs_addon
def browser_close_tab(ctx: Ctx) -> Outcome:
    tab = _tab(ctx)
    ctx.bridge.call("close", tabId=tab)
    ctx.tab_id = None
    gone = all(t["tabId"] != tab for t in ctx.bridge.call("list"))
    return Outcome(gone, "The tab is closed." if gone else "The tab is still open.", gone)


@tool("browser_tabs", "List the open tabs.", {}, label=lambda a: "Checking your tabs", reads_only=True)
@_needs_addon
def browser_tabs(ctx: Ctx) -> Outcome:
    tabs = ctx.bridge.call("list")
    lines = [f"[{t['tabId']}] {'(active) ' if t['active'] else ''}{t['title'][:70]} | {t['url'][:90]}" for t in tabs]
    return Outcome(True, "\n".join(lines) or "(no tabs)", verified=True)


@tool("browser_switch_tab", "Switch to an open tab by its number from browser_tabs.",
      {"tab_id": "integer: the tab number"}, label=lambda a: "Switching tab")
@_needs_addon
def browser_switch_tab(ctx: Ctx, tab_id: int) -> Outcome:
    info = ctx.bridge.call("activate", tabId=tab_id)
    ctx.tab_id = info["tabId"]
    _place(ctx, info.get("url", ""))
    return Outcome(True, _where(info), verified=True)


@tool("browser_read", "Read the text of the current page (for example to see what emails "
      "are in an inbox, or to answer a question about the page).", {},
      label=lambda a: "Reading the page", reads_only=True)
@_needs_addon
def browser_read(ctx: Ctx) -> Outcome:
    page = ctx.bridge.call("text", tabId=_tab(ctx), max=9000)
    _place(ctx, page["url"])
    if not page["text"].strip():
        return Outcome(False, f"The page at {page['url']} shows no text yet.")
    return Outcome(True, f"{page['title']} | {page['url']}\n{page['text']}", verified=True)


@tool("youtube_play", "Find a song or video on YouTube and play it.",
      {"query": "string: the song or video, with the artist if known",
       "new_window?": "boolean: true to play it in a separate window"},
      label=lambda a: f"Finding {a.get('query', '')[:40]} on YouTube")
@_needs_addon
def youtube_play(ctx: Ctx, query: str, new_window: bool = False) -> Outcome:
    ctx.places.add("youtube")
    info = ctx.bridge.call("open", newWindow=bool(new_window),
                           url="https://www.youtube.com/results?search_query=" + quote_plus(query))
    ctx.tab_id = info["tabId"]
    first = {"href": None}
    for _ in range(20):  # the results list fills in after the page loads
        first = ctx.bridge.call("ytfirst", tabId=ctx.tab_id)
        if first.get("href"):
            break
        time.sleep(0.5)
    if not first.get("href"):
        return Outcome(False, "YouTube showed no video results for that.")
    ctx.step(f"Playing {first.get('title', 'the video')[:50]}")
    ctx.bridge.call("navigate", tabId=ctx.tab_id, url=first["href"])
    media = None
    for attempt in range(4):
        time.sleep(1.5)
        media = ctx.bridge.call("media", tabId=ctx.tab_id, sampleMs=1500)
        if media and media.get("playing"):
            break
        if media and attempt < 3:
            ctx.bridge.call("play", tabId=ctx.tab_id)
    playing = bool(media and media.get("playing"))
    title = first.get("title") or (media or {}).get("title", "")
    if playing:
        muted = " (the player is muted)" if media.get("muted") else ""
        return Outcome(True, f"\"{title}\" is playing, at {media['currentTime']} seconds{muted}.", True)
    return Outcome(False, f"I opened \"{title}\" but the player is not playing. The browser "
                   "may be blocking autoplay until the page is clicked.")
