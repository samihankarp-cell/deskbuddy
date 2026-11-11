"""Connectors through Composio: reach Gmail, Drive, Calendar and others directly,
without loading their web pages. Active only when COMPOSIO_API_KEY is in .env."""
import json
import os
import re
import webbrowser

from deskbuddy.brain.tools import Ctx, Outcome, tool

USER = "deskbuddy"
RESULT_LIMIT = 6000
SENDS = re.compile(r"(SEND|REPLY|FORWARD|POST|PUBLISH|TWEET|INVITE|SHARE)", re.I)
DELETES = re.compile(r"(DELETE|REMOVE|TRASH|PURGE|EMPTY)", re.I)
BUYS = re.compile(r"(PAY|PURCHASE|CHARGE|CHECKOUT|ORDER)", re.I)
_client = None


def enabled() -> bool:
    return bool(os.environ.get("COMPOSIO_API_KEY", "").strip())


def client():
    global _client
    if _client is None:
        from composio import Composio

        _client = Composio(api_key=os.environ["COMPOSIO_API_KEY"].strip())
    return _client


def connected() -> list[str]:
    """Names of the services whose accounts are connected and working."""
    page = client().connected_accounts.list(user_ids=[USER], statuses=["ACTIVE"])
    names = []
    for item in getattr(page, "items", None) or []:
        kit = getattr(item, "toolkit", None)
        slug = getattr(kit, "slug", None) or (kit.get("slug") if isinstance(kit, dict) else None)
        if slug and slug.lower() not in names:
            names.append(slug.lower())
    return names


def _plain(value):
    """Turn an SDK reply into ordinary dicts and lists."""
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if isinstance(value, dict):
        return {k: _plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(v) for v in value]
    return value


def run(slug: str, arguments: dict) -> tuple[bool, object, str]:
    reply = _plain(client().tools.execute(
        slug, arguments or {}, user_id=USER, dangerously_skip_version_check=True))
    if not isinstance(reply, dict):
        return False, None, "the connector gave an answer I could not read"
    return bool(reply.get("successful")), reply.get("data"), str(reply.get("error") or "")


@tool("connector_status", "List which services (gmail, googledrive, googlecalendar, slack, "
      "notion, github ...) are connected through connectors.", {},
      label=lambda a: "Checking my connectors", reads_only=True)
def connector_status(ctx: Ctx) -> Outcome:
    names = connected()
    return Outcome(True, "Connected: " + (", ".join(names) or "nothing yet"), verified=True)


@tool("connector_connect", "Connect a service account (for example gmail or googledrive). "
      "Opens the sign-in page; the user signs in themselves.",
      {"app": "string: the service, lower case, no spaces, e.g. gmail, googledrive, slack"},
      label=lambda a: f"Connecting {a.get('app', 'the service')}",
      risk=lambda _c, a: f"start connecting your {a.get('app')} account (you sign in yourself in the browser)")
def connector_connect(ctx: Ctx, app: str) -> Outcome:
    app = app.lower().replace(" ", "")
    if app in connected():
        return Outcome(True, f"{app} is already connected.", verified=True)
    request = client().toolkits.authorize(user_id=USER, toolkit=app)
    url = getattr(request, "redirect_url", None)
    if not url:
        return Outcome(False, f"Composio gave no sign-in page for {app}.")
    webbrowser.open_new_tab(url)
    ctx.step(f"Waiting for you to sign in to {app}")
    try:
        request.wait_for_connection(timeout=240)
    except Exception as error:
        return Outcome(False, f"The sign-in for {app} was not completed ({str(error)[:100]}).")
    done = app in connected()
    return Outcome(done, f"{app} is connected." if done else f"{app} did not connect.", done)


@tool("connector_find", "Find the right connector action for a need inside one connected service. "
      "Returns action names with their arguments. Use before connector_run.",
      {"app": "string: the service, e.g. gmail", "need": "string: what you want to do, a few words"},
      label=lambda a: f"Finding how to do that in {a.get('app', 'the service')}", reads_only=True)
def connector_find(ctx: Ctx, app: str, need: str) -> Outcome:
    found = client().tools.get_raw_composio_tools(toolkits=[app.lower()], search=need, limit=8)
    lines = []
    for item in found:
        item = _plain(item)
        params = (item.get("input_parameters") or {})
        required = set(params.get("required") or [])
        args = ", ".join(
            f"{name}{'*' if name in required else ''}:{spec.get('type', 'any')}"
            for name, spec in list((params.get("properties") or {}).items())[:12])
        lines.append(f"{item.get('slug')}: {str(item.get('description', ''))[:140]}\n   args: {args}")
    if not lines:
        return Outcome(False, f"No connector action in {app} matches that.")
    return Outcome(True, "\n".join(lines) + "\n(* = required)", verified=True)


def _run_risk(_ctx: Ctx, args: dict) -> str | None:
    slug = str(args.get("action", ""))
    if BUYS.search(slug):
        return f"run {slug} (this looks like buying something)"
    if SENDS.search(slug):
        return f"run {slug} (this sends or shares something)"
    if DELETES.search(slug):
        return f"run {slug} (this deletes something)"
    return None


@tool("connector_run", "Run a connector action found with connector_find.",
      {"action": "string: the action name, e.g. GMAIL_FETCH_EMAILS",
       "arguments": "object: the action's arguments"},
      label=lambda a: f"Using {str(a.get('action', 'a connector')).split('_')[0].title()}",
      risk=_run_risk)
def connector_run(ctx: Ctx, action: str, arguments: dict | None = None) -> Outcome:
    ctx.places.add(action.split("_")[0].lower())
    ok, data, error = run(action, arguments or {})
    if not ok:
        return Outcome(False, f"{action} failed: {error or 'no reason given'}")
    return Outcome(True, json.dumps(data, default=str)[:RESULT_LIMIT], verified=True)


@tool("gmail_inbox", "Read the newest emails in the user's Gmail inbox through the connector "
      "(fast, no page loading). Use this for 'check my email'.",
      {"unread_only?": "boolean: only unread emails", "limit?": "integer: how many, default 15"},
      label=lambda a: "Checking your inbox", reads_only=True)
def gmail_inbox(ctx: Ctx, unread_only: bool = True, limit: int = 15) -> Outcome:
    ctx.places.add("gmail")
    if "gmail" not in connected():
        return Outcome(False, "Gmail is not connected. Use connector_connect with app 'gmail', "
                       "or read the inbox with the browser tools instead.")
    ok, data, error = run("GMAIL_FETCH_EMAILS", {
        "query": "in:inbox is:unread" if unread_only else "in:inbox",
        "max_results": max(1, min(int(limit), 30)), "include_payload": False, "verbose": False,
    })
    if not ok:
        return Outcome(False, f"Gmail did not answer: {error or 'no reason given'}")
    messages = (data or {}).get("messages") if isinstance(data, dict) else None
    if messages is None:
        return Outcome(True, json.dumps(data, default=str)[:RESULT_LIMIT], verified=True)
    if not messages:
        return Outcome(True, "No unread emails." if unread_only else "The inbox is empty.", True)
    lines = []
    for m in messages:
        preview = m.get("preview") if isinstance(m.get("preview"), dict) else {}
        snippet = preview.get("body") or m.get("snippet") or str(m.get("messageText", ""))[:160]
        lines.append(f"- From {m.get('sender') or m.get('from', '?')} | "
                     f"{m.get('subject') or preview.get('subject', '(no subject)')} | "
                     f"{' '.join(str(snippet).split())[:160]}")
    kind = "unread emails" if unread_only else "emails"
    return Outcome(True, f"{len(lines)} newest {kind}:\n" + "\n".join(lines), verified=True)
