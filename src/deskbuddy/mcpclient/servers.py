"""The list of MCP servers Desk Buddy connects to, saved in one JSON file in the data folder.

A server is either a local program (stdio) or a web address (streamable HTTP, or the older SSE).
Composio's MCP servers are the web-address kind: paste the address Composio gives you.
The file can hold secrets (headers, environment values), like the .env file does."""
import json
import re
import shlex
from dataclasses import asdict, dataclass, field
from pathlib import Path

from deskbuddy import config

FILE = "mcp_servers.json"
STDIO, HTTP, SSE = "stdio", "http", "sse"


class ServerError(ValueError):
    """What the user typed cannot be made into a server. The message is shown to them."""


@dataclass
class Server:
    name: str
    transport: str = STDIO
    command: str = ""
    args: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)
    url: str = ""
    headers: dict[str, str] = field(default_factory=dict)
    enabled: bool = True

    @property
    def target(self) -> str:
        return self.url if self.transport != STDIO else " ".join([self.command, *self.args]).strip()


def slug(value: str) -> str:
    """Lower case letters, digits and underscores only: safe inside a tool name."""
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


def path() -> Path:
    return config.data_dir() / FILE


def load(file: Path | None = None) -> list[Server]:
    file = file or path()
    try:
        raw = json.loads(file.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    servers = []
    for item in raw if isinstance(raw, list) else []:
        try:
            servers.append(Server(**item))
        except TypeError:
            continue   # a hand-edited entry with unknown fields: skip it, keep the rest
    return servers


def save(servers: list[Server], file: Path | None = None) -> None:
    file = file or path()
    file.write_text(json.dumps([asdict(s) for s in servers], indent=2), encoding="utf-8")


def _pairs(text: str, sep: str) -> dict[str, str]:
    out = {}
    for part in text.split(";"):
        key, found, value = part.partition(sep)
        if found and key.strip():
            out[key.strip()] = value.strip()
    return out


def _headers(url: str, extra: str) -> dict[str, str]:
    """Headers from the box. `Name: value; Name2: value`, or just a bare key, which is sent the
    way that server expects. Composio's connect.composio.dev wants `x-consumer-api-key`."""
    headers = _pairs(extra, ":")
    host = re.sub(r"^https?://", "", url, flags=re.I).split("/")[0].lower()
    if not headers and extra.strip():
        key = re.sub(r"^bearer\s+", "", extra.strip(), flags=re.I)
        if host.startswith("connect.composio"):
            headers = {"x-consumer-api-key": key}
        elif "composio" in host:
            headers = {"x-api-key": key}
        else:
            headers = {"Authorization": f"Bearer {key}"}
    if host.startswith("connect.composio") and "x-api-key" in headers:
        headers["x-consumer-api-key"] = headers.pop("x-api-key")
    return headers


def from_fields(name: str, target: str, extra: str = "") -> Server:
    """Build a server from the three boxes on the Settings page.
    `target`: a web address (https://...) or a program with its arguments (npx -y some-server).
    `extra`: for a web address `Header: value; Header2: value`; for a program `KEY=value; KEY2=value`."""
    name, target = slug(name), target.strip()
    if not name:
        raise ServerError("give the server a short name")
    if not target:
        raise ServerError("enter its web address, or the program to run")
    if re.match(r"https?://", target, re.I):
        kind = SSE if target.rstrip("/").lower().endswith("/sse") else HTTP
        return Server(name, kind, url=target, headers=_headers(target, extra))
    try:
        parts = [p.strip('"') for p in shlex.split(target, posix=False)]
    except ValueError as error:
        raise ServerError(f"I can't read that command ({error})") from error
    return Server(name, STDIO, command=parts[0], args=parts[1:], env=_pairs(extra, "="))


def from_json(text: str, fallback_name: str = "") -> list[Server]:
    """Read the usual `{"mcpServers": {name: {command, args, env | url, headers}}}` snippet that
    server docs (Composio's too) hand out. A single bare entry works when a name is given."""
    try:
        data = json.loads(text)
    except ValueError as error:
        raise ServerError(f"that is not valid JSON ({error})") from error
    if not isinstance(data, dict):
        raise ServerError("expected a JSON object")
    entries = data.get("mcpServers") or data.get("servers")
    if entries is None:
        if not fallback_name:
            raise ServerError("give the server a short name")
        entries = {fallback_name: data}
    out = []
    for name, entry in entries.items():
        if not isinstance(entry, dict):
            continue
        if entry.get("url") or entry.get("serverUrl"):
            url = str(entry.get("url") or entry.get("serverUrl"))
            kind = SSE if (entry.get("type") == "sse" or url.rstrip("/").lower().endswith("/sse")) else HTTP
            out.append(Server(slug(name), kind, url=url, headers=_headers(url, "") | dict(entry.get("headers") or {})))
        elif entry.get("command"):
            out.append(Server(slug(name), STDIO, command=str(entry["command"]),
                              args=[str(a) for a in entry.get("args") or []],
                              env={str(k): str(v) for k, v in (entry.get("env") or {}).items()}))
    if not out:
        raise ServerError("I found no server with a \"command\" or a \"url\" in that")
    return out


def parse(name: str, target: str, extra: str = "") -> list[Server]:
    """Boxes or pasted JSON, whichever was given."""
    if target.strip().startswith("{"):
        return from_json(target, name and slug(name))
    return [from_fields(name, target, extra)]


def add(servers: list[Server], new: list[Server]) -> list[Server]:
    """The list with `new` added; a server with the same name is replaced."""
    names = {s.name for s in new}
    return [s for s in servers if s.name not in names] + new
