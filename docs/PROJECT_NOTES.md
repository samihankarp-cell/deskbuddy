# Desk Buddy: project notes

Working notes on the project as it stands, and on the changes made in the latest round of work. The product description is in [README.md](../README.md) and [PRODUCT.md](../PRODUCT.md). The original design and plan are in [docs/superpowers](superpowers/).

## What it is

Desk Buddy is a small robot that lives on the Windows desktop. You talk to it (hold a key) or type to it, and it does the job in your own browser, in installed apps, or with your files. Built in Python 3.12 with PySide6 (Qt), LangGraph, SQLite memory, and the `keyboard` library for the talk key.

## How to run it

**From source** (the project folder):

```bash
uv sync
copy .env.example .env      # then put your AI key in .env
uv run deskbuddy
```

**Packaged exe** (`dist\DeskBuddy\DeskBuddy.exe`):

```bash
uv run python scripts/build_exe.py
```

The build script does not copy `.env.example` into the output folder. Copy it there by hand if you want the template next to the exe. Never copy your real `.env` into the packaged folder or commit it.

The browser add-on in `addon/` is loaded once per browser (see the README).

## Where things live

| Thing | Where |
|---|---|
| Settings (AI key, models, talk key) | `.env` in the folder that holds the exe (or the project root when running from source), plus `%APPDATA%\DeskBuddy\.env` |
| Memory, reminders, job history | `%APPDATA%\DeskBuddy\memory.db` (SQLite) |
| Browser pairing | `%APPDATA%\DeskBuddy\paired.json` |
| Window position | QSettings (Windows registry, `DeskBuddy/DeskBuddy`) |

## Folder map

```
src/deskbuddy/
  app.py              starts everything: window, tray, brain, dashboard, ears, timers
  config.py           reads .env, data_dir() helper, ROOT for source vs exe
  alerts.py           the two alert switches (suggestions, reminder pop-ups)
  state.py            the robot's states and colours
  brain/              LangGraph agent: intake, agent loop, runner, report, web, proactive offers
  browser/            local link to the browser add-on (websocket bridge) and browser tools
  apps/               open and drive installed Windows apps
  files/              file tools, Recycle Bin, undo journal
  connectors/         Composio connectors (Gmail, Drive, etc.), optional
  memory/             SQLite store, habits (routines), tools
  voice/              hold-to-talk: listen.py (hook, recording, Whisper), hotkey.py (key matching)
  ui/
    window.py         the floating robot window (Kettle, bubble, typing box)
    kettle.py         the robot drawing
    bubble.py         speech bubble
    tray.py           tray icon menu
    settings.py       old small settings dialog (kept only as a class; no longer used)
    dashboard.py      re-exports the dashboard (kept so old imports work)
    hub/              the dashboard (the Grok Bot-style control centre), see below
addon/                browser add-on (background.js, manifest.json)
scripts/
  build_exe.py        builds dist\DeskBuddy\DeskBuddy.exe
  deskbuddy_launcher.py  entry point used by the build
  hub_screens.py      renders dashboard screenshots for every look and mode
tests/                pytest + pytest-qt tests
docs/                 this file, plus the original design spec and plan
build/, dist/         PyInstaller output (generated)
```

### The dashboard (`ui/hub/`)

Opened from the robot (double-click) or the tray icon's **Open dashboard**. Same three-column layout throughout; only the look changes.

- **Left sidebar:** search, the Desk Buddy tile, then six sections: Updates, Activity, Reminders, Memory, Connectors, Settings. Plugins and the profile row sit at the bottom.
- **Middle:** the selected section. Updates is the feed of orders and results, with a "Tell Desk Buddy…" composer.
- **Right panel:** Kettle preview with the live status line, and a Routines list (upcoming reminders and noticed habits).

Files:

| File | Role |
|---|---|
| `window.py` | `Dashboard` widget: builds the layout, owns the sections, refresh timer, hotkey and look signals |
| `sidebar.py`, `rightpanel.py` | the two side columns |
| `feed_pages.py` | Updates and Activity pages |
| `manage_pages.py` | Reminders, Memory and Connectors pages |
| `settings_page.py` | Settings: Look card, Mode control, AI keys, Voice (talk key), Connectors key, alert switches |
| `look_picker.py`, `mode_picker.py` | the Look cards and the Light / Dark / System control |
| `key_capture.py` | the "press a key" box used for the talk key |
| `page.py`, `widgets.py`, `icons.py`, `glyphs.py`, `surface.py`, `theme.py` | shared building blocks (cards, bubbles, toggles, composer, icons, fonts) |
| `styles/` | the looks. `base.py` is the contract every look follows. |

**Looks and modes.** Three looks, each with Light and Dark (or System, which follows Windows):

| Look | Light | Dark |
|---|---|---|
| Classic | the original Grok Bot-like light look | near-black version |
| Skeuomorphic | leather sidebar, linen centre, paper cards | charcoal and walnut night version |
| Spatial | bright frosted glass over a pastel sky | frosted glass over a dusk backdrop |

Each look's colours are in `styles/<look>_tokens.py`. Painting hooks are in `styles/<look>_paint.py` and `styles/<look>_surfaces.py`. The stylesheet pieces are in `styles/<look>_qss.py` (Skeuomorphic and Spatial) and in `classic.py` for Classic. `styles/modes.py` decides light or dark. Choices are stored in memory under `hub_style` and `hub_mode`.

## Changes made in this round

Listed roughly in the order they were made.

1. **Dashboard rebuilt in a Grok Bot-style layout.** The old card-file dashboard was replaced with the three-column control centre described above. Every section keeps its old behaviour (orders, Done / I couldn't verdicts, reminders, memory forget, connectors, alert switches). Old `filecards.py` was removed.
2. **Settings moved into the dashboard.** The separate settings window is only used if the dashboard cannot be created; in practice it is now unused (see Known gaps).
3. **Alert switches added.** `alert_suggestions` (unasked web suggestions) and `alert_reminder_toasts` (Windows pop-up for reminders), both on by default, stored in memory. Implemented in `alerts.py`, used in `app.py`.
4. **Unread dot and "updates seen" marker** on the Updates row, stored as `updates_seen`.
5. **Three looks built**: Classic (kept as it was), Skeuomorphic, and Spatial. A Look card in Settings switches them live and remembers the choice.
6. **Light and dark modes for each look.** A Light / Dark / System control under the Look cards. Six variants in total. Layout is identical in each. Body-text contrast was checked for each variant (above 4.5:1 in all of them except the small placeholder and pill labels listed under Known gaps).
7. **Talk key fixed and made configurable.**
   - Cause of the left Ctrl bug: the `keyboard` library treats "right ctrl" as also covering left Ctrl's scan code, and Right Alt had the same problem with left Alt. Listening now matches the exact key name the Windows hook reports (`voice/hotkey.py`).
   - The talk key is now set by pressing it (`ui/hub/key_capture.py`). Esc cancels. Letters, digits, Space, Enter, Tab, Backspace, Delete and left Ctrl / Shift / Alt / Win are refused with a hint.
   - Changing the key applies straight away (`Listener.set_hotkey`) and is saved to `.env`.
   - Default is still Right Ctrl.
8. **Floating robot made smaller.** Width 150px is now `KETTLE_WIDTH = round(150 / 1.75)` = 86px in `ui/window.py`. The window size is unchanged.
9. **Tray menu cleaned up.** The Settings item was removed. Menu is now Open dashboard, Hide Desk Buddy, Type an order, Quit.
10. **Dashboard opens without an AI key.** Previously, with no key, the dashboard was never created, so "Open dashboard" did nothing. Now the app creates the dashboard with memory from `%APPDATA%` (no brain), and the robot's bubble tells the user to add the key on the Settings page and restart. `config.data_dir()` was added so memory can open without loading settings.
11. **Packaged build rebuilt** several times with `scripts/build_exe.py` and launched from `dist\DeskBuddy`.

Tests: 136 pass (`uv run pytest -q`). New test files: `tests/test_hotkey.py`, `tests/test_modes.py`, `tests/test_spatial.py`. `tests/test_hub.py` covers the dashboard.

## Round 2: providers, live settings, MCP

- **Providers** (`providers.py`): presets for NVIDIA, OpenAI, Claude, Gemini, OpenRouter, Groq, Together, Mistral, DeepSeek, Ollama, LM Studio and Custom. All use the OpenAI-style chat API through `langchain-openai`, so only address, key and model names change. Picking one on the Settings page fills address and models; they stay editable. Models on this PC need no key. Model names are suggestions and may need updating by hand.
- **Save applies at once.** `config.Settings` is a mutable object shared with the running brain; `config.reload()` re-reads the `.env` into it, and every model call builds its client from it. `app.apply_settings()` runs on the Settings page's `settings_saved` signal. If the app started without a key, saving a valid one starts the brain then. A bad save (for example no key) keeps the old working settings and says why. Only the browser-link port and the speech model still need a restart, and the page says so.
- **MCP** (`mcpclient/`): `servers.py` is the saved list (`%APPDATA%\DeskBuddy\mcp_servers.json`) and the parsing of what the user types, including the usual `{"mcpServers": ...}` snippet. `hub.py` runs each server as a task on its own thread and turns its tools into Desk Buddy tools named `mcp_<server>_<tool>`. Types: local program (stdio), streamable HTTP, SSE. Risk wording for the Yes / No question comes from the server's own hints, then the tool name (send, delete, buy). `brain.tools.load_all()` is built fresh for each job, so new servers and a new Composio key show up in the next job.
- **Composio as MCP:** add its MCP address as an HTTP server (a key header can go in the Header box). The older Composio API-key route still works.
- Not done: signing in to an MCP server through a browser (OAuth). Servers that need it can use a key in a header for now.

## How the parts connect

- `app.main()` builds `BuddyWindow` and the tray first, so the robot and tray are up even if the brain fails.
- `config.load()` reads `.env`. If the AI key is missing it raises `ConfigError`, and `main()` falls back to a dashboard with memory only.
- Otherwise `main()` starts the brain (`Runner`), the browser bridge, the Listener (talk key), the reminder and habit timers, and the idea timer. Then it creates the full `Dashboard` and wires its signals.
- `Dashboard.hotkey_changed` → `Listener.set_hotkey`, so the talk key changes live.
- Dashboard orders go through `submit` → `Runner.submit`, the same path as typed orders on the robot.

## Known gaps and notes

- **No git commits yet.** The repo has a `master` branch with no commits. Almost everything is untracked. Make a first commit once you're happy with it.
- **`Habit`** is an empty stray file in the project root. It was created by an early shell command. Safe to delete.
- **`SettingsDialog`** in `ui/settings.py` is no longer used anywhere. It can be deleted, along with its test if any.
- **Packaged app needs the key entered in Settings.** The exe reads `.env` next to it. Enter the key on the dashboard's Settings page and restart.
- **The `.env` written by the Settings page** goes to the exe folder (packaged) or the project root (source). Keep it out of git. `.gitignore` covers `.env`.
- **Not verified on real hardware by the automated checks:**
  - real key presses through the live keyboard hook (the left Ctrl fix was checked by reading the library code and by the owner, who confirmed it works);
  - AltGr keyboards;
  - the Alt / F10 system-menu behaviour while recording;
  - high-DPI screens;
  - hover and pressed states of controls.
- **Small window:** the Spatial look and the sidebar get crowded at very small window sizes.
- **Light-variant small text:** a few placeholder and pill labels in Classic Light and Skeuomorphic Light sit a little under the 4.5:1 contrast target. They were left as shipped.
- **Packaged `.env.example`** is not produced by the build script; copy it by hand.
- **Generated folders** (`build/`, `dist/`, `__pycache__`, `.pytest_cache`) are not source. Rebuild instead of editing them.

## Useful commands

```bash
uv run pytest -q                                  # run all tests
uv run deskbuddy                                  # run from source
uv run python scripts/build_exe.py                # build dist\DeskBuddy\DeskBuddy.exe
uv run python scripts/hub_screens.py <folder> all both   # screenshots of every look and mode
```
