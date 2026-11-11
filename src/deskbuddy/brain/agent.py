"""One job: the agent picks tools step by step, then a separate check decides the verdict."""
import json
from collections import Counter

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage

from deskbuddy.brain.llm import agent_model, fast_model, parse_json, text_of
from deskbuddy.brain.tools import MOUSE_LOCK, Ctx, Outcome, load_all
from deskbuddy.brain.types import CheckResult, JobResult

MAX_STEPS = 18
MAX_SAME_FAILURE = 2
OBSERVATION_LIMIT = 6000

SYSTEM = """You are Desk Buddy, a small robot that does jobs on the user's Windows PC by calling tools.
You are their personal assistant: calm, capable, brief, and you know their routines.

Rules:
- Do the job yourself with tools. Never tell the user how to do it themselves.
- Use the user's own open browser through the browser_* tools. Look before you click:
  browser_look and app_look give you numbered elements; click and type by number.
- To play a song or video, use youtube_play.
- To work in a desktop app: app_open, then app_look, then app_click / app_type / app_keys.
  If app_look shows nothing useful, use screen_look and screen_click.
- If the user states a lasting preference, interest or fact about themselves (a job
  search they are on, what email matters to them, their usual song), save it with remember.
  When they say "the usual" or "my morning song", use what you know and their routines.
- To just look something up, web_lookup is faster than opening a tab.
- Do not ask the user for confirmation. Risky actions are stopped by the system itself.
- Never type passwords.
- When the job is complete, call finish. Put a few plain words of what you did in
  "summary". Fill "answer" only if the user asked for information. The answer is shown
  in a tiny speech bubble: at most 2 short sentences, 35 words. Say the one thing that
  needs their attention first, then sum up everything else in a few words (for example
  "One email about your job application. The rest is newsletters and job alerts.").
  No lists, no counts of everything, no email addresses.
- If the user is only chatting, call finish and put a friendly one or two sentence reply in
  "answer", like a person talking. Never give_up on small talk.
- If the job cannot be done, call give_up with the real reason in plain words.
- Never claim something you did not observe in a tool result."""

CHECKER = """You are the strict checker for Desk Buddy. Decide whether the job was really done.
You get the goal, the log of every tool call with its real result, the agent's claimed
outcome, and fresh evidence gathered after it finished.
Reply with JSON only: {"passed": true or false, "reason": "..."}
- passed is true only if the log and evidence prove the goal was achieved.
- A claim with no supporting tool result is a fail. Unclear is a fail.
- If the goal was only a question or small talk that needs no action on the PC, pass
  when the answer is reasonable and, where it cites the PC or a page, supported by the log.
- reason: one short plain sentence, written to the user, saying what went wrong.
  Empty when passed."""

FINISH = {"type": "function", "function": {
    "name": "finish", "description": "The job is complete.",
    "parameters": {"type": "object", "properties": {
        "summary": {"type": "string", "description": "What was done, a few words, past tense."},
        "answer": {"type": "string", "description": "Only if the user asked for information."},
    }, "required": ["summary"]}}}
GIVE_UP = {"type": "function", "function": {
    "name": "give_up", "description": "The job cannot be done.",
    "parameters": {"type": "object", "properties": {
        "reason": {"type": "string", "description": "The real reason, plain words."},
    }, "required": ["reason"]}}}


def friendly_error(error: Exception) -> str:
    name = type(error).__name__
    if "Connection" in name or "Timeout" in name:
        return "I can't reach the AI right now"
    if "Authentication" in name or "PermissionDenied" in name:
        return "the AI key was rejected"
    if "RateLimit" in name:
        return "the AI service says I am sending too many requests"
    return f"something broke inside me ({name}: {str(error)[:120]})"


def run_job(deps, order: str, goal: str) -> JobResult:
    memory = deps.memory
    job_id = memory.start_job(order, goal)
    ctx = Ctx(job_id=job_id, goal=goal, settings=deps.settings, memory=memory,
              bridge=deps.bridge, step=deps.step, confirm=deps.confirm, stopped=deps.stopped)
    log: list[dict] = []
    try:
        result = _work(ctx, goal, log)
    except Exception as error:  # never crash the app because one job broke
        result = JobResult(goal, CheckResult(False, friendly_error(error)))
    memory.finish_job(job_id, result.check.passed, result.check.reason, result.answer)
    _write_notebook(ctx, goal, log, result)
    return result


def _work(ctx: Ctx, goal: str, log: list[dict]) -> JobResult:
    tools = load_all()
    model = agent_model(ctx.settings).bind_tools(
        [t.schema() for t in tools.values()] + [FINISH, GIVE_UP]
    )
    history = "\n".join(f"{r}: {t}" for r, t in ctx.memory.recent_messages(6))
    notes = "\n".join(ctx.memory.notes_for(goal))
    system = SYSTEM
    if notes:
        system += f"\n\nLessons from earlier attempts, do not repeat these mistakes:\n{notes}"
    system += _about_user(ctx)
    messages = [
        SystemMessage(system),
        HumanMessage(f"Recent conversation:\n{history or '(none)'}\n\nYour job now: {goal}"),
    ]
    failures: Counter = Counter()
    finished: dict | None = None
    gave_up: str | None = None
    denied = False
    idle_turns = 0

    for _ in range(MAX_STEPS):
        if ctx.stopped():
            return JobResult(goal, CheckResult(False, "you stopped me"))
        reply = model.invoke(messages)
        messages.append(reply)
        if not reply.tool_calls:
            idle_turns += 1
            if idle_turns > 2:
                gave_up = text_of(reply)[:200] or "I could not work out what to do next"
                break
            messages.append(HumanMessage(
                "Call a tool. If the job is complete call finish; if it is impossible call give_up."
            ))
            continue
        for call in reply.tool_calls:
            name, args = call["name"], call.get("args") or {}
            if name == "finish":
                finished, content = args, "ok"
            elif name == "give_up":
                gave_up, content = str(args.get("reason", "")), "ok"
            else:
                content, was_denied = _call_tool(ctx, tools, name, args, failures, log)
                denied = denied or was_denied
                if log and log[-1].get("stop_reason"):
                    gave_up = log[-1]["stop_reason"]
            messages.append(ToolMessage(content=content, tool_call_id=call["id"]))
        if finished is not None or gave_up is not None or denied:
            break
    else:
        gave_up = "I ran out of steps before finishing"

    if denied:
        return JobResult(goal, CheckResult(False, "you said no"))
    if gave_up is not None:
        return JobResult(goal, CheckResult(False, gave_up or "I could not do it"))
    summary = str(finished.get("summary", "")).strip()
    answer = _fit_bubble(ctx, str(finished.get("answer", "") or "").strip())
    check = _check(ctx, goal, log, summary, answer, tools)
    return JobResult(goal, check, answer=answer, summary=summary)


def _about_user(ctx: Ctx) -> str:
    """Saved facts, noticed routines, the time, and which connectors exist."""
    from datetime import datetime

    from deskbuddy.connectors import tools as connectors

    parts = [f"\n\nIt is {datetime.now():%A %Y-%m-%d %H:%M}."]
    prefs = ctx.memory.prefs()
    if prefs:
        parts.append("What you know about the user:\n" + "\n".join(f"{i}. {t}" for i, t in prefs))
    habits = ctx.memory.habits()
    if habits:
        parts.append("Routines you have noticed:\n" + "\n".join(
            f"- around {h.when()}: \"{h.order}\"" for h in habits))
    if connectors.enabled():
        parts.append("Connectors are available. For Gmail, Drive, Calendar and other online "
                     "services, prefer gmail_inbox / connector_* tools over loading web pages. "
                     "If a service is not connected, use the browser instead.")
    else:
        parts.append("Composio connectors are off (there is no COMPOSIO_API_KEY), so use the "
                     "browser for online services unless an mcp_ tool covers them.")
    if any(name.startswith("mcp_") for name in load_all()):
        parts.append("Tools named mcp_<server>_<tool> come from MCP servers the user connected "
                     "(for example Composio). Prefer them over the browser for what they cover.")
    return "\n\n".join(parts)


ANSWER_LIMIT = 220  # characters that fit comfortably in the speech bubble


def _fit_bubble(ctx: Ctx, answer: str) -> str:
    """Shorten an answer that is too long to read in the bubble. Facts stay the same."""
    if len(answer) <= ANSWER_LIMIT:
        return answer
    try:
        reply = fast_model(ctx.settings).invoke([
            SystemMessage(
                "Rewrite this for a tiny speech bubble: at most 2 short sentences, 35 words. "
                "First the one thing that needs the reader's attention, then the rest summed "
                "up in a few words. No lists. Do not add or change any fact. Reply with the "
                "rewritten text only."),
            HumanMessage(answer),
        ])
        short = text_of(reply).strip().strip('"')
        if 0 < len(short) <= ANSWER_LIMIT + 60:
            return short
    except Exception:
        pass
    cut = answer[:ANSWER_LIMIT]
    return (cut[:cut.rfind(".") + 1] or cut.rstrip() + "...")


def _call_tool(ctx, tools, name, args, failures, log) -> tuple[str, bool]:
    """Run one tool. Returns (what the agent is told, whether the user refused it)."""
    tool = tools.get(name)
    if tool is None:
        return f"FAILED: there is no tool called {name}.", False
    key = (name, json.dumps(args, sort_keys=True, default=str))
    if failures[key] >= MAX_SAME_FAILURE:
        return ("FAILED: you already tried this exact action twice and it failed. "
                "Try a different approach, or call give_up."), False
    try:
        risk = tool.risk(ctx, args) if tool.risk else None
    except Exception:
        risk = None
    if risk:
        if not ctx.confirm(f"Is it OK if I {risk}?"):
            log.append({"tool": name, "args": args, "ok": False, "verified": False,
                        "reads_only": tool.reads_only, "text": "the user said no"})
            return "FAILED: the user said no. Stop now.", True
    ctx.step(tool.label(args))
    try:
        if tool.physical:
            with MOUSE_LOCK:
                outcome = tool.fn(ctx, **args)
        else:
            outcome = tool.fn(ctx, **args)
    except TypeError as error:
        outcome = Outcome(False, f"wrong arguments: {error}")
    except Exception as error:
        outcome = Outcome(False, f"{type(error).__name__}: {str(error)[:300]}")
    if not outcome.ok:
        failures[key] += 1
    log.append({"tool": name, "args": args, "ok": outcome.ok, "verified": outcome.verified,
                "reads_only": tool.reads_only, "text": outcome.text[:400],
                "stop_reason": outcome.stop_reason})
    head = "OK" if outcome.ok else "FAILED"
    if outcome.ok and not outcome.verified and not tool.reads_only:
        head = "OK BUT NOT CONFIRMED"
    return f"{head}: {outcome.text[:OBSERVATION_LIMIT]}", False


def _fresh_evidence(ctx: Ctx) -> str:
    """Look at the world again, after the agent stopped."""
    lines = []
    if ctx.tab_id is not None and ctx.bridge is not None:
        try:
            info = ctx.bridge.call("info", tabId=ctx.tab_id)
            lines.append(f"Browser tab now: {info.get('title')} | {info.get('url')}")
            media = ctx.bridge.call("media", tabId=ctx.tab_id, sampleMs=1200)
            if media:
                lines.append(f"Video on that tab: playing={media.get('playing')} "
                             f"time={media.get('currentTime')} title={media.get('title')}")
        except Exception as error:
            lines.append(f"Browser tab could not be read: {error}")
    if ctx.used_app:
        try:
            from deskbuddy.apps.tools import window_text
            from deskbuddy.apps.win import foreground_title
            lines.append(f"Window in front now: {foreground_title()}")
            lines.append(f"The app window shows: {window_text(ctx)}")
        except Exception:
            pass
    return "\n".join(lines) or "(nothing more to look at)"


def _check(ctx, goal, log, summary, answer, tools) -> CheckResult:
    actions = [e for e in log if not e["reads_only"]]
    if actions and not any(e["ok"] for e in actions):
        return CheckResult(False, "none of the things I tried worked")
    lines = [
        f"{i + 1}. {e['tool']}({json.dumps(e['args'], default=str)[:200]}) -> "
        f"ok={e['ok']} confirmed={e['verified']}: {e['text']}"
        for i, e in enumerate(log)
    ]
    prompt = (
        f"Goal: {goal}\n\nTool log:\n" + ("\n".join(lines) or "(no tools were called)")
        + f"\n\nAgent's claim: {summary}\nAgent's answer to the user: {answer or '(none)'}"
        + f"\n\nFresh evidence:\n{_fresh_evidence(ctx)}"
    )
    try:
        reply = agent_model(ctx.settings).invoke([SystemMessage(CHECKER), HumanMessage(prompt)])
    except Exception as error:
        return CheckResult(False, f"I could not check my own work ({friendly_error(error)})")
    data = parse_json(text_of(reply))
    if not data or data.get("passed") is not True:
        reason = str((data or {}).get("reason") or "I could not confirm that it worked")
        return CheckResult(False, reason)
    return CheckResult(True)


def _write_notebook(ctx: Ctx, goal: str, log: list[dict], result: JobResult) -> None:
    """Remember what failed and what worked, per site or app, for next time."""
    failed = [e for e in log if not e["ok"]]
    if not ctx.places or not failed:
        return
    worked = [e["tool"] for e in log if e["ok"] and not e["reads_only"]]
    for place in ctx.places:
        for entry in failed[:3]:
            lesson = f"{entry['tool']} failed ({entry['text'][:120]})"
            if result.check.passed and worked:
                lesson += f"; what worked instead: {', '.join(dict.fromkeys(worked))}"
            ctx.memory.add_note(place, lesson)
        if not result.check.passed:
            ctx.memory.add_note(place, f"'{goal[:80]}' failed: {result.check.reason[:160]}")
