# Contributing

Thanks for helping. Small, clear changes are easiest to review.

## Prerequisites

- Windows 10 or 11 (the app drives Windows apps, so it does not run elsewhere)
- [uv](https://docs.astral.sh/uv/)
- Python 3.12 (uv will fetch it)

## Get started

Fork the repository on GitHub, then:

```bash
git clone https://github.com/<you>/deskbuddy.git
cd deskbuddy
uv sync
uv run deskbuddy      # start the app
uv run pytest         # run the tests
```

To try the browser side, load the add-on unpacked from the `addon/` folder: in Chrome, Edge, Brave or Comet turn on Developer mode on the extensions page and choose "Load unpacked". In Firefox use `about:debugging`, "This Firefox", "Load Temporary Add-on", and pick `addon/manifest.json`. Approve it when Desk Buddy asks.

The project layout is in the [README](README.md#development), and how an order flows through the code is in [How it works](README.md#how-it-works).

## Style

- Keep files small, under about 500 lines. Split when one grows past that.
- Comments and anything the user sees are plain English, short sentences, no jargon.
- No new dependency without discussing it in an issue first.
- Add or update tests for what you change. Tests must not touch your real settings or files; see `tests/conftest.py`.

## Adding a tool

1. Add a function with the `@tool` decorator in `src/deskbuddy/brain/tools.py` (or the module that registers tools for its area).
2. Give it a plain description the AI can follow, and a `label` for the speech bubble.
3. If it sends, buys, signs in or deletes anything, pass `risk=`. It returns the sentence for the Yes / No question, or `None` when the call is harmless.
4. Return an `Outcome`. After acting, re-read the world (the page, the file, the window) and set `verified=True` only if the result is really there. The "Done" wording depends on this.
5. Add a test.

## Pull request checklist

- [ ] `uv run pytest` passes
- [ ] New risky actions use `risk=`
- [ ] No keys, `.env` files or personal data in the diff
- [ ] User-facing text is plain English
- [ ] README or CHANGELOG updated if behaviour changed
