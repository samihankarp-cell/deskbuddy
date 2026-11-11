"""First contact with an order: a short acknowledgement and a split into jobs."""
import re
from dataclasses import dataclass

from langchain_core.messages import HumanMessage, SystemMessage

from deskbuddy.brain.llm import fast_model, parse_json, text_of

REPEAT = re.compile(r"^\s*(please\s+)?(do|run|play|try)?\s*(that|it|this)?\s*(once\s+)?(again|one more time)[\s.!]*$|^\s*repeat( that| it)?[\s.!]*$", re.I)
UNDO = re.compile(r"^\s*(please\s+)?undo(\s+(that|it|this|the last (thing|one|job)))?[\s.!]*$", re.I)

PROMPT = """You are the ears of Desk Buddy, a desktop robot that does jobs on the user's PC.
Split the user's order into separate jobs and write a very short acknowledgement.
Reply with JSON only: {"ack": "...", "jobs": ["...", "..."]}
- ack: at most 8 words, specific, in the voice of a calm, capable personal assistant,
  like "On it: Gmail and your song" or "Right away, opening Notepad". Never say it is done.
- jobs: one entry per independent job, each a full sentence that stands on its own
  (replace words like "it" or "that" using the recent conversation). Keep every detail
  the user gave. Most orders are ONE job.
- Split ONLY when the parts are unrelated and could be done at the same time
  ("check Gmail" and "play a song"). Steps that build on each other are ONE job:
  "make a folder and put a file in it" is one job, "open Notepad and type hello" is one job.
- If the user is only chatting or asking a question, that is one job too."""


@dataclass
class AckPlan:
    ack: str
    jobs: list[str]


def is_repeat(text: str) -> bool:
    return bool(REPEAT.match(text))


def is_undo(text: str) -> bool:
    return bool(UNDO.match(text))


def split_order(settings, order: str, history: list[tuple[str, str]]) -> AckPlan:
    """Ask the fast model. Any failure falls back to treating the order as one job."""
    fallback = AckPlan("On it.", [order])
    try:
        talk = "\n".join(f"{role}: {text}" for role, text in history[-6:])
        reply = fast_model(settings).invoke([
            SystemMessage(PROMPT),
            HumanMessage(f"Recent conversation:\n{talk or '(none)'}\n\nOrder: {order}"),
        ])
        data = parse_json(text_of(reply))
        jobs = [j.strip() for j in (data or {}).get("jobs", []) if isinstance(j, str) and j.strip()]
        if not jobs:
            return fallback
        ack = str(data.get("ack") or "On it.").strip()
        return AckPlan(ack[:80], jobs[:5])
    except Exception:
        return fallback
