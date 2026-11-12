# Security

## Reporting a vulnerability

Please report security problems privately, not in a public issue. Use [Report a vulnerability](https://github.com/samihankarp-cell/deskbuddy/security/advisories/new) (GitHub private advisories). Include what you found, the steps to reproduce it, and the Desk Buddy version or commit.

I will reply as soon as I can and work with you on a fix before anything is made public.

## Supported versions

| Version | Supported |
| ------- | --------- |
| 0.1.x   | Yes       |

## Trust model

Desk Buddy is an agent that acts on your PC with your permissions. Read this before you run it.

**What it can do.** It can open and operate your browser (through the add-on), operate any desktop app with the real mouse and keyboard, and create, edit, rename, move, copy and delete files. It runs as your Windows user, with no sandbox.

**What asks Yes / No first.** Buying, sending, signing in, deleting permanently, and changes to Windows settings. File tools also ask before touching Windows folders, and refuse to delete or move whole Desktop, Documents, home or drive folders. Normal deletes go to the Recycle Bin. Desktop apps ask before buttons named like Send, Delete, Buy or Sign in and before shortcuts such as Ctrl+Enter, and the browser asks before pressing Enter in a box that is not a search box. These checks are rules in the code around the AI, not promises from the AI, but they only cover actions the code recognises as risky. They recognise button names in English, Spanish, French, German, Portuguese, Italian and Hindi; in other languages, and for buttons with unusual names ("Confirm", "Place bid"), they may not ask. Clicking a bare screen point (`screen_click`) cannot be judged and never asks. Treat it as a helper you supervise, not as something to leave alone with an account you cannot afford to lose.

**Passwords.** It never types into password boxes. Sign-in steps ask you first and leave the password to you.

**The browser add-on.** The add-on talks only to Desk Buddy on `127.0.0.1` (your own PC), on ports 8765 to 8769. Each add-on connection must be approved by you once. Replies are accepted only from the approved connection. The add-on can read pages and act in any tab you have open, signed in as you.

**What leaves your PC.** Page text, and for some apps a screenshot of that app's window, go to the AI provider you chose. That can include anything on screen, such as email subjects. Audio stays on your PC; speech is turned into text locally. Unasked suggestions run a web search for topics you have been working on.

**MCP servers and connectors.** An MCP server you add is fully trusted. A program on your PC runs with your permissions. A remote address gets the headers or keys you gave it. Desk Buddy asks before MCP tools that send, delete or pay, but it can only judge that from what the server reports, so only add servers you trust. The same goes for Composio connectors.

**Where secrets are stored.** Your AI key and Composio key live in `.env` in plain text. MCP server settings, including any key or header, live in `%APPDATA%\DeskBuddy\mcp_servers.json` in plain text. Memory and history are local files in `%APPDATA%\DeskBuddy`. Do not share these files or commit them.

**Prompt injection.** Web pages, emails and documents the agent reads can contain text written to trick an AI into doing something else. This is a known, unsolved risk for agents like this one. Desk Buddy marks everything a tool returns as data and tells the AI never to follow instructions found in it, and the Yes / No checks limit the damage, but neither removes the risk. Be careful about letting it read pages you do not trust while signed in to sensitive accounts.

**Logs.** `%APPDATA%\DeskBuddy\deskbuddy.log` records errors and crashes. Known key formats and the values of key settings are blanked out before anything is written, but read a log before attaching it to a public issue.
