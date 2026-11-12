# Changelog

All notable changes are listed here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

## [0.1.0] - 2026-11-12

First public release. Windows 10/11, for developers. The packaged `DeskBuddy.exe` is attached to the GitHub release.

### Features
- Works in your own open browser through a bundled add-on: open sites, search, click, type, scroll, read pages, play YouTube.
- Opens and operates desktop apps with the real mouse and keyboard.
- File tools: create, edit, rename, move, copy, delete (to the Recycle Bin), with "undo that".
- Hold-to-talk voice input with speech turned into text on your PC, or type by clicking the robot.
- Works with NVIDIA, OpenAI, Claude, Gemini, OpenRouter, Groq, Together, Mistral, DeepSeek, Ollama, LM Studio, or any OpenAI-compatible address.
- Optional Composio connectors and MCP servers, added in Settings with no restart.
- Dashboard with updates, activity, reminders, memory, connectors and live settings.
- Remembers lasting facts and routines, and offers occasional suggestions.
- Says Done only after a separate check confirms the result; asks Yes / No before buying, sending, signing in, permanent deletes and Windows settings changes.

### Security
- Refusing a risky step now stops the rest of that step's batch.
- The browser link only accepts replies from the approved add-on connection.
- MCP meta-tools (for example Composio's multi-execute) now ask before sending, deleting or paying.
- File tools refuse to delete or move whole Desktop, Documents, home or drive folders.
- Desktop apps now ask before clicking Send, Delete, Buy or Sign in, and before Ctrl+Enter, Alt+S, Shift+Delete or Windows-key shortcuts. Typing into a password box is refused.
- In the browser, pressing Enter in a box that is not a search box asks first, and delete buttons ask too.
- Browser and app checks understand Spanish, French, German, Portuguese, Italian and Hindi as well as English.
- The add-on marks page elements with a fresh random token on each look, so a page cannot redirect a click to another element.
- Accepting an unasked suggestion opens the link directly; the link text is never handed to the AI as an order.
- Tool results are fenced as data, and the AI is told never to follow instructions found inside them.
- `screen_look` sends only the app window being worked on, not the whole screen.

### Fixed
- The add-on finds Desk Buddy on ports 8765 to 8769, so changing the port in Settings works.
- The add-on pairing question is no longer silently refused after pressing Esc.
- Removed two stray empty files.
- `screen_look` and `screen_click` failed every time because Pillow was missing; it is now a dependency.
- Key names with spaces ("page down", "print screen") work in `app_keys`.

### Added
- LICENSE, SECURITY, CONTRIBUTING and Code of Conduct files.
- CI workflow, a release workflow that builds and publishes `DeskBuddy.exe` from a tag, issue templates and a pull request template.
- A README for developers: how an order flows through the code, the safety model, configuration, development, and screenshots.
- The original design document, now at `docs/design.md`.
- A log file, `%APPDATA%\DeskBuddy\deskbuddy.log`, with keys blanked out, that also records crashes. Settings has an "Open logs folder" button.

[Unreleased]: https://github.com/samihankarp-cell/deskbuddy/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/samihankarp-cell/deskbuddy/releases/tag/v0.1.0
