# Desk Buddy: Design

Date: 2026-11-09
Status: approved and built (this is the original design; the code has moved on since)

Items marked **(owner)** were decided by the owner. Items marked **(my call)** are the
designer's defaults and can be overruled.

## 1. Intent

Desk Buddy is a small white hovering robot that lives on the Windows desktop. The owner
tells it what they want, by speaking or typing, and it does the job on the PC the way a
person at the desk would: in the browser that is already open, in any installed app, and
in the file system.

It is a resume project aimed at an internship. It will be posted on LinkedIn and published
on GitHub so that tech enthusiasts can download it, add their own AI key and try it. The
product comes first; a demo video is made later and is not part of this work.

The example the owner gave of a normal request:

> "Hey, open Gmail and check if I have any new emails, and on another window play Suna
> Suna by Shreya Ghoshal for me."

Expected result: YouTube opens in a separate window and the song plays; Gmail is read in
the owner's already-signed-in browser; the robot reports with judgment, for example "One
email about the status of your application. The rest is newsletters, nothing that needs
you right now."

## 2. Goals

1. **Browser** (owner). Use the browser the person already has open: Comet, Chrome, Edge,
   Brave or Firefox. Open sites in a new tab or new window, search, click links and
   buttons, type into boxes, scroll, go back, close tabs, read a page and say what it
   says, play videos on YouTube. Comet is the first browser built and proven; the same
   code must detect and work with the others.
2. **Any app** (owner). Open any installed app and operate it with mouse and keyboard.
   If the app is not installed, say so straight away.
3. **Files** (owner). Create, edit, rename, move, copy and delete files and folders.
   Deletes go to the Recycle Bin. "Undo that" puts things back.
4. **Several jobs in one sentence** (owner). One order may contain more than one job, and
   jobs that do not fight over the mouse run at the same time.
5. **Instant reply** (owner). Within one second of an order the robot shows it heard.
6. **Step-by-step bubble** (owner). One short line per step: "Opening YouTube",
   "Clicking Sign up".
7. **Honest results** (owner, top priority). "Done" appears only after a real check
   passed. Otherwise "I couldn't" plus the real reason.
8. **No lectures** (owner). It does the job. It never explains how to do it yourself
   unless asked.
9. **Memory** (owner). It remembers what was said and done across restarts. "Do that
   again" works.
10. **No repeated mistakes** (owner). It does not keep failing the same way.
11. **Judgment when reporting** (owner). Lead with what needs attention, sum up the rest.
12. **Speaking from day one** (owner). Hold a hotkey, speak, release. Typing also works.
13. **Runs for other people** (owner). A stranger can clone the repo, add their own key,
    and run it on their own browser.

## 3. Non-goals (for now)

- Spoken replies. Replies are text only; a voice may be added later (owner).
- A wake word. Listening starts with the hotkey only.
- macOS or Linux.
- Publishing the browser add-on to the Chrome Web Store or Firefox Add-ons.
- A one-click installer. Running from source with a short setup is enough.
- The demo video and LinkedIn post.

## 4. Anti-goals (these make it a failure even if it "works")

- Saying "Done" when the job did not happen. This is the owner's most hated outcome.
- Repeating the same failed action over and over, in one job or across days.
- Asking for confirmation on harmless actions such as opening a tab (owner).
- Giving instructions instead of doing the job.
- Launching a separate, clean browser instead of using the owner's open one.
- Deleting anything permanently without asking.
- The owner's API key appearing in the repo, the logs, or any published file.
- A robot that resembles an existing character.

## 5. Safety

Desk Buddy asks first, with Yes / No buttons in the bubble, before exactly these (owner):

1. buying something
2. sending a message or email
3. signing in
4. entering a password
5. deleting something permanently
6. changing Windows settings

Everything else it just does.

How the gate works (my call): the decision to ask is made by code, not left to the AI's
mood. Each tool call is classified before it runs. Hard signals always trigger the gate:
a password field, a permanent-delete call, a Windows Settings / Control Panel / registry
target. Soft signals (a button or page whose text reads like pay, place order, send, sign
in, log in) trigger the gate too. The AI may additionally raise the gate itself. The AI
cannot lower it. A "No" ends that job with "I couldn't: you said no". Desk Buddy never
types a password itself in this version; on Yes it stops at the field and hands over to
the owner.

## 6. The robot and its window

- Look: "Kettle" (owner picked from three mockups). White tapered body, round dark face,
  two coral arc eyes, two floating round hands, antenna with a coral ball, soft coral
  glow beneath. Original artwork, drawn as vector shapes in code.
- A frameless, transparent, always-on-top window in a screen corner. Draggable. It bobs
  gently. Position is remembered.
- States shown by eyes and the bubble's status dot: idle, listening, thinking, working,
  asking, done, couldn't.
- Speech bubble beside the robot: the current step as one short line. The final report
  may be a few lines.
- Clicking the robot opens a small text box for typing an order. Enter sends it.
- Tray icon: show/hide, settings, quit.
- Settings (a small window): hotkey, AI key and model names, microphone.

Built with PySide6 (my call).

## 7. Talking to it

- Hold-to-talk hotkey, default Right Ctrl, changeable in settings (owner asked for a
  chosen hotkey; default is my call, because Left Ctrl alone collides with copy/paste).
- While held, the robot shows "listening". On release the audio is turned into text on
  the PC with faster-whisper, model size "small" so that non-English song and people
  names survive (my call). No audio leaves the PC.
- The heard text appears briefly in the bubble so a mishearing is visible.

## 8. The brain

- Python, agent built with LangGraph (owner).
- AI provider: any OpenAI-compatible endpoint, set in a private `.env` file. The owner
  uses NVIDIA's endpoint with two models; both were tested on 2026-11-09 and work:
  - fast model `nvidia/nemotron-3.5-bolt-e4b` (replied in about 0.3 s)
  - agent model `nvidia/nemotron-3.5-super-vl-120b-a12b` (tool calling confirmed, about
    0.9 s; has vision)
- `.env` is git-ignored. The repo ships `.env.example` with blank values.

Flow of one order (my call):

1. **Acknowledge.** The window shows a listening/got-it state immediately, without
   waiting on the network. The fast model then writes a short specific line ("On it:
   Gmail and your song") and splits the order into jobs. The one-second promise must hold
   even when the network is slow, so the local acknowledgement is the guarantee and the
   AI line is the upgrade.
2. **Recall.** Load recent conversation, the last jobs (for "do that again" and "undo
   that"), and any notebook entries about the sites or apps involved.
3. **Run the jobs.** Each job is a loop: the agent model looks at the current state,
   picks one tool, the tool runs, the bubble shows that tool's label. Browser jobs and
   file jobs can run side by side. Jobs that need the real mouse and keyboard take turns.
4. **Gate.** Before a risky tool call, pause and ask (section 5).
5. **Check.** After the agent believes a job is finished, a separate check decides
   (section 9).
6. **Report.** Code assembles the final message from the check results. The fast model
   may only phrase it, never change a verdict.

Limits: a step budget per job, and the same action with the same target may fail at most
twice in one job before the agent must change approach or stop.

## 9. Honesty: how "Done" is earned

The agent model is never allowed to declare success. Every job ends in a check that looks
at the real world again:

| Job type | What the check looks at |
|---|---|
| Open site / tab | The tab exists and its address matches |
| Play a video | The page's player reports it is playing and time is advancing |
| Click / type | The page changed as expected (new address, field holds the text) |
| Read / summarise | The text really came from the page, and the page was the right one |
| Open an app | A window of that app exists |
| App actions | Fresh look at the window's controls, or a fresh screenshot judged against the goal |
| File actions | The file system shows the expected result |

Where a check can be done by code it is done by code. Where it needs judgment (was this
the right song?), the agent model is shown fresh evidence and must answer in a fixed form:
passed or failed, with the evidence. Unclear counts as failed.

Wording is fixed by code: a pass gives "Done: …", a fail gives "I couldn't: … because …".
A mixed order reports each job separately.

## 10. Not repeating mistakes

- Inside a job: the repeat limit in section 8.
- Across days: a notebook stored on disk. Each entry records a site or app, what was
  tried, whether it worked, and what worked instead. Relevant entries are given to the
  agent before it starts a job in the same place. Entries that later prove wrong are
  replaced.

## 11. Browser control

A small Desk Buddy browser add-on, installed once per browser, talks to the desktop app
over a local-only connection protected by a pairing code (my call). This is the only
dependable way to click and read inside tabs the person already has open and signed in.

- One add-on codebase for the Chromium family (Comet, Chrome, Edge, Brave), plus a
  Firefox build of the same code.
- What it can do: list / open / close / switch tabs, open a new window, go to an address,
  go back, list the clickable and typable things on the page, click, type, scroll, return
  the page's text, report whether a video is playing.
- Which browser gets used: the one that is open with the add-on connected; if several,
  the one used most recently.
- If the open browser has no add-on, Desk Buddy says so plainly once and offers to open
  the install page. It does not silently start another browser.
- Known limit, stated honestly in the README: without store publishing, Chromium browsers
  need "developer mode" to load the add-on, and Firefox forgets an unsigned add-on on
  restart.

## 12. App control

- Finding apps: the Start Menu list of installed apps. A fuzzy match picks the app. No
  match means an immediate "I couldn't: X isn't installed", with the nearest names if
  any are close.
- Operating apps: first through Windows' own accessibility information (the names and
  positions of buttons and boxes), which is exact. For apps that expose none, a
  screenshot is sent to the vision model to locate the target. Real mouse and keyboard
  input is then sent.
- Risk (my call to flag): how precisely the vision model can point at things on a
  screenshot is unproven. It is tested early in the app-control step; if it is weak,
  app control leans on accessibility information and says "I couldn't" for apps it
  cannot see into, rather than clicking blindly.

## 13. Files and undo

- Every file action is written to an undo journal with what is needed to reverse it:
  the old name, the old place, a saved copy of the old contents for edits.
- Delete sends to the Recycle Bin. Undo restores from it.
- "Undo that" reverses every action of the most recent job, newest first, then checks
  the result like any other job.
- Permanent delete exists only behind the safety gate.

## 14. Memory

One local database file holds: the conversation, every job with its steps and outcome,
the undo journal, and the notebook. "Do that again" re-runs the most recent order through
the normal flow, including checks and gates. Nothing is stored online.

## 15. Privacy note

To do its work Desk Buddy sends page text and, for some apps, screenshots to the AI
provider chosen in `.env`. That includes whatever is on screen, such as email subjects.
The README says this clearly. Audio never leaves the PC.

## 16. Build order

Each piece is shown working to the owner before the next begins (owner).

1. The robot on the desktop: Kettle hovering, bubble, typing box, tray icon.
2. The brain: instant reply, LangGraph flow, a first trivial tool, honest report wording.
3. Speaking: hold-to-talk and on-PC transcription.
4. Files: all file actions, Recycle Bin, undo, checks.
5. Browser on Comet: add-on, tabs, search, click, type, scroll, read, YouTube play, checks.
6. The owner's example in one sentence: Gmail summary plus a song in another window, at
   the same time.
7. Apps: find, open, "not installed", operate with mouse and keyboard, checks.
8. Safety gates across everything, then memory: "do that again", the notebook.
9. Other browsers (Chrome, Edge, Brave, Firefox) and the README for strangers.

## 17. Smaller calls settled during review (all my call)

- **Unclear orders.** If an order cannot be understood at all, or names something that
  could be two different things with different consequences, Desk Buddy asks one short
  question. This is not a confirmation and is never used for clear orders.
- **Undo covers files only.** Browser and app actions are not undoable; asked to undo
  one, it says "I couldn't: that can't be undone" and does not pretend.
- **Where files may be touched.** Anywhere the owner's Windows account can write, except
  Windows' own folders and Program Files, which count as "changing Windows settings" and
  go through the safety gate.
- **Starting with Windows.** Off by default, switchable in settings.
- **Stopping a job.** Pressing Esc while the robot is working, or clicking a stop mark
  on the bubble, halts the job at once. The report then says what was and was not done.
- **Mouse in use.** While Desk Buddy is driving the real mouse and keyboard, the bubble
  says so. If the owner moves the mouse sharply during it, the job pauses.
- **Add-on missing.** Opening a site in a new tab still works without the add-on (it is
  a plain "open this address" request to the browser). Everything deeper needs the add-on.
- **Repo.** A git repository in the project folder, MIT licence, `.env` and the local
  database git-ignored.

## 18. Left to the builder

- Internal file layout, names and test approach.
- Python version (3.11 and 3.14 are both on the owner's PC; choose whichever every
  dependency supports) and packaging tool.
- The exact libraries for hotkeys, audio capture, mouse/keyboard, accessibility and
  Recycle Bin restore.
- The exact shape of the LangGraph graph, provided sections 8 to 10 hold.
- Step budgets and timeouts.
- Bubble wording, animation details and colours for each state, within the Kettle look.
