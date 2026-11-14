# The Desk Buddy browser add-on

Desk Buddy works in the browser you already use, signed in to your own accounts. This small add-on is how it does that: it opens tabs, reads pages, clicks and types when Desk Buddy asks it to. It talks only to the Desk Buddy app on your own PC (`127.0.0.1`, ports 8765 to 8769) and nothing else.

It isn't in the Chrome Web Store or Firefox Add-ons yet, so you load it from this folder. It takes about a minute, once per browser.

## 1. Find the folder

| You got Desk Buddy from | The add-on folder is |
| --- | --- |
| The release zip | `DeskBuddy\addon`, next to `DeskBuddy.exe` |
| `git clone` | `deskbuddy\addon` in the project |

The right folder is the one that contains `manifest.json` and `background.js`. Leave it where it is after loading: the browser reads the add-on from that folder every time it starts. If you move or delete it, the add-on stops working.

## 2. Load it

### Chrome

1. Type `chrome://extensions` in the address bar and press Enter.
2. Turn on **Developer mode** (the switch at the top right).
3. Click **Load unpacked** (top left).
4. Pick the `addon` folder from step 1 and click **Select Folder**.
5. A **Desk Buddy** card appears. Optional: click the puzzle-piece icon in the toolbar and pin it.

### Edge

1. Go to `edge://extensions`.
2. Turn on **Developer mode** (in the left panel; on a narrow window it is under the menu).
3. Click **Load unpacked** and pick the `addon` folder.

### Brave

1. Go to `brave://extensions`.
2. Turn on **Developer mode** (top right), click **Load unpacked**, and pick the `addon` folder.

### Comet and other Chromium browsers

Open the extensions page (menu, then **Extensions**, then **Manage extensions**, or try `chrome://extensions`), turn on **Developer mode**, click **Load unpacked**, and pick the `addon` folder.

### Firefox (121 or newer)

1. Go to `about:debugging#/runtime/this-firefox`.
2. Click **Load Temporary Add-on...**.
3. Open the `addon` folder and pick **`manifest.json`** (Firefox wants the file, not the folder).

Firefox removes temporary add-ons when it closes, so repeat this after each restart. A permanent Firefox install needs the add-on signed by Mozilla, which is on the roadmap.

## 3. Allow it in Desk Buddy

Start Desk Buddy (`uv run deskbuddy` or `DeskBuddy.exe`). The order doesn't matter: the add-on looks for the app every few seconds.

The first time the add-on connects, the robot asks:

> Let the Desk Buddy add-on in Chrome connect to me?

Click **Yes**. It asks once per browser and remembers the answer in `%APPDATA%\DeskBuddy\paired.json`.

## 4. Check it works

Type or say: **"open wikipedia"**. It should open in a new tab of that browser, and the bubble should say what it is doing. If the robot says the add-on isn't connected, or the page opens without it saying it confirmed anything, see [Troubleshooting](#troubleshooting).

If you use more than one browser, load the add-on in each. Desk Buddy works in whichever one you used last.

## Updating

When you update Desk Buddy (a new release, or `git pull`), reload the add-on too, because the app and the add-on must match:

- **Chrome, Edge, Brave, Comet:** on the extensions page, click the circular reload arrow on the Desk Buddy card.
- **Firefox:** on `about:debugging`, click **Reload** under Desk Buddy.

If you unzipped a new release into a different folder, remove the old add-on and load the new `addon` folder instead.

## What it is allowed to do, and why

| Permission | Why |
| --- | --- |
| `tabs` | Open, switch, read the address of and close tabs. |
| `scripting` | Read a page and click or type in it, when Desk Buddy asks. |
| `alarms` | Wake up every 30 seconds to keep the connection to the app. |
| Access to all sites | So it can work on whatever site you ask about. |

It never types into password boxes, and it asks you first before buying, sending, deleting or signing in. [SECURITY.md](../SECURITY.md) has the full picture.

## Troubleshooting

- **Desk Buddy says the add-on isn't connected.** Check that Desk Buddy is running, and that the add-on's card is switched on. On the card, click **Details**, then **Errors**, to see whether something failed. The add-on only looks on ports 8765 to 8769, so keep the port in Desk Buddy's Settings inside that range.
- **You clicked No by mistake.** Desk Buddy only remembers a refusal until it closes. Quit it from the tray icon, start it again, and click **Yes** this time.
- **"Manifest file is missing or unreadable".** You picked the wrong folder. Pick the one that contains `manifest.json`. In the release zip that is `DeskBuddy\addon`, not `DeskBuddy`.
- **Chrome warns about developer mode extensions on start-up.** That is normal for add-ons loaded from a folder. Keep it, or close the warning.
- **The card says the service worker is inactive.** That is normal: Chrome pauses it between requests and it wakes up when needed.
- **It can't work on some pages.** Browsers don't let any add-on act on their own pages (`chrome://`, `edge://`, `about:`), on the Chrome Web Store, or in the built-in PDF viewer.

## Removing it

Click **Remove** on the add-on's card (or **Remove** on `about:debugging` in Firefox). To make Desk Buddy forget that it ever allowed a browser, delete `%APPDATA%\DeskBuddy\paired.json` while Desk Buddy is closed.
