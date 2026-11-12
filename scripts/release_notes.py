"""Print the GitHub release notes for one version: how to install, then its CHANGELOG.md section.

    uv run python scripts/release_notes.py 0.1.0
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

INSTALL = """\
## Install

1. Download `DeskBuddy-v{version}-windows-x64.zip` below and unzip it anywhere.
2. Run `DeskBuddy.exe`. It is not code-signed yet, so Windows SmartScreen may warn you:
   choose **More info**, then **Run anyway**. The `.sha256` file lets you check the download.
3. Double-click the robot, open **Settings**, pick your AI provider, paste your key and press **Save**.
4. Load the browser add-on from the `addon` folder next to the exe (Developer mode, "Load unpacked").

Developers can run from source instead: see the [README](https://github.com/samihankarp-cell/deskbuddy#quick-start).
"""


def section(changelog: str, version: str) -> str:
    """The body of `## [version]` up to the next `## [` heading or the link list."""
    match = re.search(rf"^## \[{re.escape(version)}\][^\n]*\n(.*?)(?=^## \[|^\[[^\]]+\]: |\Z)",
                      changelog, re.S | re.M)
    if not match:
        raise SystemExit(f"CHANGELOG.md has no section for {version}")
    return match.group(1).strip()


def main() -> None:
    version = sys.argv[1].lstrip("v")
    body = section((ROOT / "CHANGELOG.md").read_text(encoding="utf-8"), version)  # fail first
    print(INSTALL.format(version=version))
    print("## What's in it\n")
    print(body)


if __name__ == "__main__":
    main()
