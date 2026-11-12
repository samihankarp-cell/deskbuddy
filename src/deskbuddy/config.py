"""Settings, read from the private .env file. The key never lives in code.

`load()` makes the settings; `reload()` re-reads the .env into the same object, so the running
brain picks up a new key, provider or model on its next call without a restart."""
import os
import sys
from dataclasses import dataclass, fields
from pathlib import Path

from dotenv import load_dotenv

from deskbuddy import providers

# Source checkout: the project folder. Packaged exe: the folder that holds DeskBuddy.exe.
ROOT = (
    Path(sys.executable).resolve().parent
    if getattr(sys, "frozen", False)
    else Path(__file__).resolve().parents[2]
)

RESTART_FIELDS = {"ws_port": "the browser link port", "whisper_size": "the speech model"}


class ConfigError(Exception):
    pass


@dataclass
class Settings:
    base_url: str
    api_key: str
    fast_model: str
    agent_model: str
    hotkey: str
    ws_port: int
    whisper_size: str
    data_dir: Path
    provider: str = providers.DEFAULT


def data_dir() -> Path:
    """Where memory and pairing live. The folder is created if needed."""
    folder = Path(os.environ.get("APPDATA", Path.home())) / "DeskBuddy"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def _read_env(folder: Path) -> None:
    # override=True so a value changed in the file wins over the one read earlier; the project
    # file is read last so it still beats the AppData one, as it always did.
    load_dotenv(folder / ".env", override=True)
    load_dotenv(ROOT / ".env", override=True)


def load_env() -> None:
    """Read the .env files into the environment. Call before building anything that shows settings."""
    _read_env(data_dir())


def _build() -> Settings:
    folder = data_dir()
    _read_env(folder)
    env = os.environ.get
    base_url = env("DESKBUDDY_BASE_URL", "").strip()
    chosen = env("DESKBUDDY_PROVIDER", "").strip().lower()
    provider = providers.get(chosen) if chosen else providers.get(providers.guess(base_url))
    key = env("DESKBUDDY_API_KEY", "").strip()
    if not key:
        if provider.needs_key:
            raise ConfigError(f"there is no AI key for {provider.name} in the .env file")
        key = "none"   # a model on this PC wants no key, but the client needs some text
    base_url = base_url or provider.base_url
    if not base_url:
        raise ConfigError("there is no AI address in the .env file")
    try:
        port = int(env("DESKBUDDY_WS_PORT", "8765") or "8765")
    except ValueError:
        port = 8765
    # The add-on can't read this .env, so it tries 8765-8769 in turn; any other port would be unreachable.
    if not 8765 <= port <= 8769:
        port = 8765
    return Settings(
        provider=provider.key,
        base_url=base_url,
        api_key=key,
        fast_model=env("DESKBUDDY_FAST_MODEL", "").strip() or provider.fast_model,
        agent_model=env("DESKBUDDY_AGENT_MODEL", "").strip() or provider.agent_model,
        hotkey=env("DESKBUDDY_HOTKEY", "").strip() or "right ctrl",
        ws_port=port,
        whisper_size=env("DESKBUDDY_WHISPER", "small"),
        data_dir=folder,
    )


def load() -> Settings:
    return _build()


def reload(current: Settings) -> list[str]:
    """Re-read the .env into `current`, in place. Returns the names of the fields that changed.
    Raises ConfigError (and leaves `current` as it was) if the new settings are not usable."""
    fresh = _build()
    changed = []
    for field in fields(Settings):
        if getattr(current, field.name) != getattr(fresh, field.name):
            setattr(current, field.name, getattr(fresh, field.name))
            changed.append(field.name)
    return changed
