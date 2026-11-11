"""Build the Windows app: dist/DeskBuddy/DeskBuddy.exe plus the browser add-on and .env template.

Run from the project root with the project venv:
    .venv\Scripts\python.exe scripts\build_exe.py
"""
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist" / "DeskBuddy"

# Packages that load code, models or data by name at runtime, which PyInstaller misses.
COLLECT_ALL = ["faster_whisper", "ctranslate2", "tokenizers", "langgraph", "composio"]
# Imported inside functions (and by the MCP SDK by name), so name them. Not collect-all: that
# also imports mcp.cli, which needs an optional package.
HIDDEN = ["mcp.client.stdio", "mcp.client.sse", "mcp.client.streamable_http",
          "mcp.shared._httpx_utils", "deskbuddy.mcpclient.hub"]


def main() -> int:
    args = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm", "--clean", "--onedir", "--windowed",
        "--name", "DeskBuddy",
        "--distpath", str(ROOT / "dist"),
        "--workpath", str(ROOT / "build"),
        "--specpath", str(ROOT / "build"),
        "--paths", str(ROOT / "src"),
    ]
    for package in COLLECT_ALL:
        args += ["--collect-all", package]
    for name in HIDDEN:
        args += ["--hidden-import", name]
    args.append(str(ROOT / "scripts" / "deskbuddy_launcher.py"))
    result = subprocess.run(args, cwd=ROOT)
    if result.returncode != 0:
        return result.returncode

    # The browser add-on is loaded by hand once per browser, so it ships beside the exe.
    shutil.copytree(ROOT / "addon", DIST / "addon", dirs_exist_ok=True)
    shutil.copyfile(ROOT / ".env.example", DIST / ".env.example")
    print(f"\nBuilt: {DIST / 'DeskBuddy.exe'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
