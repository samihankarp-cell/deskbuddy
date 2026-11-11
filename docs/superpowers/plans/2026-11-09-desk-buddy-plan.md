# Desk Buddy Implementation Plan

**Goal:** Build Desk Buddy piece by piece, showing each piece working before the next.

**Spec:** `docs/superpowers/specs/2026-11-09-desk-buddy-design.md`

**Tech stack:** Python 3.12 (uv), PySide6, LangGraph, langchain-openai (OpenAI-compatible endpoint), SQLite, pytest + pytest-qt. Later pieces add faster-whisper, send2trash, pywinauto, websockets, and a browser add-on.

**Execution:** native, in this session, one piece at a time. Each piece ends with a live check by the owner.

## Global constraints

- "Done" only from a passed check. Fail wording: "I couldn't: ... because ...". Wording is assembled by code.
- Same failing action at most twice per job.
- Confirmation only for the six risky actions in spec section 5.
- API key lives in `.env` only. `.env` and the database are git-ignored.
- No file over 500 lines.

## File map

```
src/deskbuddy/
  __main__.py        start the app
  app.py             wires window, tray, brain
  state.py           BuddyState enum
  config.py          Settings from .env
  ui/kettle.py       KettleWidget: draws the robot per state
  ui/bubble.py       BubbleWidget: status dot + text, optional Yes/No
  ui/window.py       BuddyWindow: frameless, topmost, drag, input box
  ui/tray.py         tray icon menu
  brain/types.py     CheckResult, JobResult
  brain/report.py    format_report(results) -> str
  brain/llm.py       fast_model(), agent_model()
  brain/intake.py    split_order(text) -> AckPlan(ack, jobs)
  brain/tools.py     tool registry: name, label, risk, run, check
  brain/graph.py     LangGraph flow: acknowledge, recall, run, gate, check, report
  brain/runner.py    background thread + order queue, emits Qt signals
  memory/db.py       SQLite: messages, jobs, steps, undo journal, notebook
  voice/             piece 3
  files/             piece 4
  browser/           piece 5 (plus addon/ at repo root)
  apps/              piece 7
tests/
```

## Pieces

1. **Robot on the desktop.** kettle, bubble, window, tray. Tests: every state renders; position is saved and clamped to the screen. Live check: robot hovers, drags, bubble shows typed text.
2. **Brain.** config, llm, intake, report, tools (one trivial tool), graph, runner, db basics. Tests: report wording; malformed model output falls back to one job; unknown job gives "I couldn't"; API down gives "I couldn't", never a crash; orders queue. Live check: type an order, instant reply, honest answer.
3. **Speaking.** hold-to-talk hotkey, faster-whisper "small".
4. **Files.** all actions, Recycle Bin, undo journal, checks.
5. **Browser on Comet.** add-on + local WebSocket bridge, tab and page tools, YouTube play check.
6. **Gmail summary plus song at once.** parallel jobs, new window.
7. **Apps.** Start Menu lookup, "not installed", accessibility first, vision fallback (test pointing accuracy first).
8. **Safety gates and memory.** gate by code, "do that again", notebook.
9. **Other browsers and README.**

## Review focus

- Empty or whitespace order: ignored, no model call.
- Network or API failure: "I couldn't: I can't reach the AI", app keeps running.
- Fast model returns junk: treat the whole order as one job.
- Second order while one runs: queued, acknowledged at once.
- Monitor unplugged or resolution changed: robot is moved back on screen at start.
