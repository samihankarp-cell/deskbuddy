# Desk Buddy

A small white robot that hovers on your Windows desktop and does what you tell it, by voice or by typing, the way a person at your desk would: in your own open browser, in any installed app, and in your files.

Built in Python with LangGraph.

## What it does

- **Your browser.** Works in the browser you already have open and signed in (Comet, Chrome, Edge, Brave, Firefox). Opens sites, searches, clicks, types, scrolls, reads pages, plays YouTube.
- **Any app.** Opens any installed app and works it with the real mouse and keyboard. If the app is not installed it says so.
- **Your files.** Create, edit, rename, move, copy, delete. Deletes go to the Recycle Bin. "Undo that" puts things back.
- **Connectors (optional).** With a Composio key it reaches Gmail, Drive, Calendar and others directly, without loading their pages.
- **MCP servers (optional).** Add any MCP server in Settings, a web address (Composio's MCP address, for example) or a program on your PC, and its tools join the others. No restart.
- **Any AI provider.** NVIDIA, OpenAI, Claude, Gemini, OpenRouter, Groq, Together, Mistral, DeepSeek, Ollama or LM Studio on your PC, or any OpenAI-compatible address.
- **Remembers you.** It keeps a short list of lasting facts, notices routines ("you usually play this around 8"), and now and then offers something that fits what you are working on, such as a fresh job posting.

## How it behaves

- It answers within a second so you know it heard you.
- A speech bubble shows each step: "Opening YouTube", "Clicking Sign up".
- It says **Done** only after a separate check confirmed the result. Otherwise it says **I couldn't** and gives the real reason.
- It asks Yes / No first only before buying, sending, signing in, deleting permanently, or changing Windows settings. It never types passwords.
- It does not repeat a failed action more than twice, and it keeps a notebook of what failed on each site or app.

## Setup

You need Windows 10 or 11 and [uv](https://docs.astral.sh/uv/).

1. Get the code and install:

   ```bash
   uv sync
   ```

2. Start it (next step), open the dashboard's **Settings**, pick your AI provider, paste your key and press **Save**. It applies at once, no restart. (You can also copy `.env.example` to `.env` and fill it in by hand.) The default provider is NVIDIA.

3. Start it:

   ```bash
   uv run deskbuddy
   ```

4. Install the browser add-on once per browser:
   - **Comet, Chrome, Edge, Brave:** open the extensions page, turn on Developer mode, choose "Load unpacked", pick the `addon` folder.
   - **Firefox:** open `about:debugging`, "This Firefox", "Load Temporary Add-on", pick `addon/manifest.json`. Firefox forgets it on restart.
   - The first time the add-on connects, Desk Buddy asks you to allow it.

5. Optional connectors: make a key at [composio.dev](https://app.composio.dev), put it in Settings and press Save, then say "connect my Gmail". Or add Composio as an MCP server instead (Settings, MCP servers, paste its address). Other tools work the same way.

## Using it

- **Talk:** hold Right Ctrl, speak, let go. Change the key in Settings by pressing the one you want (it works at once, no restart). The first run downloads the speech model. Speech is turned into text on your PC.
- **Type:** click the robot.
- **Stop:** press Esc.
- **Dashboard:** double-click the robot or use the tray icon. One window for updates, activity, reminders, memory, connectors and settings (Ctrl+K searches, Ctrl+1 to 6 switch sections).
- **Settings, hide, quit:** the tray icon near the clock.

Things to try:

- "Open Gmail and tell me if anything needs me, and play Suna Suna by Shreya Ghoshal in another window"
- "Make a folder called Old on my desktop and move notes.txt into it", then "undo that"
- "Open Notepad and type hello"
- "Do that again"

## Privacy

To do its work Desk Buddy sends page text, and for some apps screenshots, to the AI service in your `.env`. That includes whatever is on screen, such as email subjects. Unasked suggestions run a web search for topics you have been working on. Audio never leaves your PC. Memory is one local file in `%APPDATA%\DeskBuddy`. MCP servers you add are saved there too (`mcp_servers.json`), including any header or key you gave them, like the `.env` file.

## How it is built

```
src/deskbuddy/
  app.py            wires the window, brain, browser link, ears and routines
  ui/               the robot, its bubble, tray icon
  ui/hub/           the dashboard window (sections, routines, settings page)
  brain/graph.py    LangGraph flow: intake -> jobs side by side -> report
  brain/agent.py    one job: tool loop, repeat limit, separate checker
  brain/intake.py   instant reply and splitting an order into jobs
  brain/report.py   the Done / I couldn't wording, decided by code
  brain/proactive.py unasked suggestions
  memory/           SQLite: conversation, jobs, undo journal, notebook, facts, routines
  files/            file tools, Recycle Bin restore, undo
  browser/          tools plus the local link to the add-on
  apps/             open and operate desktop apps
  connectors/       Composio tools (API key)
  mcpclient/        MCP servers: the saved list and the connection hub
  providers.py      the AI provider presets
  voice/            hold-to-talk
addon/              the browser add-on
```

## Licence

MIT
