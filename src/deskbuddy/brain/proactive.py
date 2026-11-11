"""Now and then, Desk Buddy offers something unasked that fits what the user is working on,
for example a fresh job posting when they have been job hunting. It only ever offers;
nothing is opened or done until the user says Yes."""
import random
import time
from dataclasses import dataclass
from datetime import date, datetime

from langchain_core.messages import HumanMessage, SystemMessage

from deskbuddy.brain.llm import agent_model, parse_json, text_of
from deskbuddy.brain.web import search

MIN_GAP_HOURS = 3       # at least this long between unasked offers
MAX_PER_DAY = 2
QUIET_BEFORE, QUIET_AFTER = 9, 22   # only between 9:00 and 22:00
MAX_DECLINES = 3        # after this many "No" in a row, at most one offer a day

PICK_TOPIC = """You help a personal assistant decide whether to offer its user something unasked.
From what the user has been doing, pick ONE thing they are actively pursuing where a fresh
find from the web would be welcome: a job search, something they are shopping for or
researching, news about a topic they follow. Ignore music, files, apps and small chores.
Reply with JSON only: {"query": "a web search that would find something new and specific"}
or {"query": null} if nothing qualifies. Prefer null over a weak guess."""

PICK_RESULT = """Pick the single search result the user would most want to see, given what they
are pursuing. It must be specific (one posting, one article, one product), not a generic
listing or home page. Reply with JSON only:
{"index": the result's number, "say": "at most 18 words offering it, like a personal
assistant would, ending with a question such as 'Shall I open it?'"}
or {"index": null} if none is worth interrupting them for."""


@dataclass
class Offer:
    say: str
    url: str


def allowed_now(memory) -> bool:
    now = datetime.now()
    if not QUIET_BEFORE <= now.hour < QUIET_AFTER:
        return False
    if time.time() - float(memory.get("offer_last", "0")) < MIN_GAP_HOURS * 3600:
        return False
    day, _, count = memory.get("offer_day", "|0").partition("|")
    used = int(count or 0) if day == date.today().isoformat() else 0
    limit = 1 if int(memory.get("offer_declines", "0")) >= MAX_DECLINES else MAX_PER_DAY
    return used < limit and random.random() < 0.5  # the coin flip keeps the timing unplanned


def note_offer_made(memory) -> None:
    today = date.today().isoformat()
    day, _, count = memory.get("offer_day", "|0").partition("|")
    memory.set("offer_day", f"{today}|{(int(count or 0) if day == today else 0) + 1}")
    memory.set("offer_last", str(time.time()))


def note_answer(memory, accepted: bool) -> None:
    memory.set("offer_declines", "0" if accepted else str(int(memory.get("offer_declines", "0")) + 1))


def think_of_offer(settings, memory) -> Offer | None:
    """Returns something worth offering, or None. Never raises."""
    try:
        known = "\n".join(text for _id, text in memory.prefs()) or "(nothing saved)"
        orders = "\n".join(f"- {o}" for o in memory.recent_orders()) or "(none)"
        model = agent_model(settings)
        context = f"What is known about the user:\n{known}\n\nTheir recent requests:\n{orders}"
        topic = parse_json(text_of(model.invoke([SystemMessage(PICK_TOPIC), HumanMessage(context)])))
        query = (topic or {}).get("query")
        if not query:
            return None
        results = [r for r in search(str(query)) if not memory.was_offered(r["url"])]
        if not results:
            return None
        listing = "\n".join(f"{i}. {r['title']} | {r['url']} | {r['snippet'][:160]}"
                            for i, r in enumerate(results))
        choice = parse_json(text_of(model.invoke([
            SystemMessage(PICK_RESULT), HumanMessage(f"{context}\n\nSearch results:\n{listing}")])))
        index = (choice or {}).get("index")
        if not isinstance(index, int) or not 0 <= index < len(results) or not choice.get("say"):
            return None
        memory.mark_url_offered(results[index]["url"])
        return Offer(str(choice["say"])[:160], results[index]["url"])
    except Exception:
        return None
