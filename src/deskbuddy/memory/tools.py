"""Lets the agent keep a short list of lasting facts about the user."""
from deskbuddy.brain.tools import Ctx, Outcome, tool


@tool("remember", "Save one lasting fact or preference about the user (what they count as "
      "important email, their usual song, names of people, how they like things done). "
      "Only things that will matter on other days. Never one-off details.",
      {"fact": "string: one short sentence"}, label=lambda a: "Noting that")
def remember(ctx: Ctx, fact: str) -> Outcome:
    ctx.memory.add_pref(fact.strip())
    saved = any(text == fact.strip() for _id, text in ctx.memory.prefs())
    return Outcome(saved, "Saved." if saved else "It was not saved.", verified=saved)


@tool("forget", "Remove a saved fact by its number (the numbers are shown in 'What you know "
      "about the user').", {"number": "integer: the fact's number"},
      label=lambda a: "Forgetting that")
def forget(ctx: Ctx, number: int) -> Outcome:
    ctx.memory.remove_pref(int(number))
    gone = all(pref_id != int(number) for pref_id, _text in ctx.memory.prefs())
    return Outcome(gone, "Forgotten." if gone else "It is still saved.", verified=gone)


@tool("reminder_add", "Set a reminder. It is shown on the desktop and in the dashboard when due.",
      {"text": "string: what to remind the user of, short",
       "when": "string: the date and time as YYYY-MM-DD HH:MM (24 hour, local time)"},
      label=lambda a: "Setting a reminder")
def reminder_add(ctx: Ctx, text: str, when: str) -> Outcome:
    from datetime import datetime

    try:
        due = datetime.fromisoformat(when.strip().replace("T", " "))
    except ValueError:
        return Outcome(False, "The time must look like 2026-11-10 17:00.")
    if due <= datetime.now():
        return Outcome(False, f"{when} is already in the past. It is now {datetime.now():%Y-%m-%d %H:%M}.")
    reminder_id = ctx.memory.add_reminder(text.strip(), due.timestamp())
    saved = any(row[0] == reminder_id for row in ctx.memory.reminders())
    return Outcome(saved, f"Reminder set for {due:%A %b %d at %H:%M}: {text}", verified=saved)


@tool("reminder_list", "List the reminders, with their numbers.", {},
      label=lambda a: "Checking your reminders", reads_only=True)
def reminder_list(ctx: Ctx) -> Outcome:
    from datetime import datetime

    rows = ctx.memory.reminders()
    lines = [f"[{rid}] {datetime.fromtimestamp(due):%b %d %H:%M} {'(shown) ' if fired else ''}{text}"
             for rid, due, text, fired in rows]
    return Outcome(True, "\n".join(lines) or "There are no reminders.", verified=True)


@tool("reminder_remove", "Remove a reminder by its number from reminder_list.",
      {"number": "integer: the reminder's number"}, label=lambda a: "Removing that reminder")
def reminder_remove(ctx: Ctx, number: int) -> Outcome:
    ctx.memory.remove_reminder(int(number))
    gone = all(row[0] != int(number) for row in ctx.memory.reminders())
    return Outcome(gone, "Removed." if gone else "It is still there.", verified=gone)
