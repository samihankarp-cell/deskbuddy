# Product

<!-- impeccable:product-schema 1 -->

> Written without an interview: the owner asked for no questions. Facts marked *(inferred)* come from the conversation and the code, not from a confirmation round.

## Platform

desktop (Windows 10/11, native Qt window via PySide6). Not a web surface.

## Stack

Python 3.12, PySide6 (Qt Widgets), LangGraph agent, SQLite memory. Existing codebase.

## Users

- The owner: a student building Desk Buddy as an internship / resume project, who also uses it daily on their own Windows PC, mostly alongside Comet browser, Gmail, YouTube and job searching.
- Secondary *(inferred)*: tech enthusiasts on LinkedIn and GitHub who clone the repo, add their own AI key and try it.

## Product Purpose

Desk Buddy is a small white hovering robot on the desktop that does jobs on the PC the way a person at the desk would: in the user's own open browser, in any installed app, and in the file system. Orders are spoken (hold Right Ctrl) or typed. Success is a job actually done, reported honestly.

The dashboard is the place to manage it: give an order, see what it did and whether each job really worked, manage reminders, see and correct what it remembers, and connect services.

## Positioning

It acts on the user's real, signed-in desktop rather than a sandboxed browser, and it only says "Done" after a separate check of the real result. Every failure is stated with its real reason.

## Operating Context

- Runs all day beside a browser and other apps. The robot lives in a screen corner; the dashboard is opened on demand (double-click the robot or the tray icon) and then closed or left behind other windows.
- The dashboard is glanced at between tasks: did that work, what's waiting, what does it know about me.
- Reminders and unasked suggestions surface on the robot's bubble and are logged in the dashboard.

## Capabilities and Constraints

- Jobs: browser control through a local add-on, app control (accessibility tree, screenshot fallback), files with Recycle Bin and undo, reminders, web lookup, Composio connectors (optional, needs a key).
- Memory: conversation, jobs with pass/fail and reason, undo journal, lessons per site/app, up to 40 lasting facts, routines inferred from history.
- Safety: Yes/No only before buying, sending, signing in, permanent delete, Windows settings. Never types passwords. No confirmations for harmless actions.
- Interrupting: a new order stops the current job.
- Replies are text only (voice output is a later idea).

## Brand Commitments

- Name: Desk Buddy.
- Mascot: "Kettle", an original white tapered robot with a round dark face, coral arc eyes, floating hands and an antenna. The owner chose it from three mockups. It must stay original.
- Voice: a calm, capable personal assistant ("like Jarvis", owner's words). Brief, never lecturing.
- Honesty wording is fixed: "Done: ..." and "I couldn't: ... because ...".
- The owner referenced "a dashboard like Grok's desktop app" as the bar for how managing it should feel.

## Evidence on Hand

- Real usage data lives in the local SQLite memory (jobs, messages). No screenshots, testimonials or metrics exist for publication.

## Product Principles

1. Honest over impressive: a verdict is never softened.
2. Do, don't explain.
3. Quiet until needed: one short line per step, interruptions only for risk, reminders, or a well-earned suggestion.
4. Memory the user can see and correct.

## Accessibility & Inclusion

No specific requirement established. Keyboard use and readable contrast are expected.
