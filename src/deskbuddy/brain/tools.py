"""The tool registry. Every ability Desk Buddy has is one Tool in REGISTRY."""
import threading
from dataclasses import dataclass, field
from typing import Any, Callable

MOUSE_LOCK = threading.Lock()  # only one job at a time may drive the real mouse/keyboard


@dataclass
class Outcome:
    ok: bool                # the action ran without error
    text: str               # what the agent is told
    verified: bool = False  # the world was re-read and shows the expected result
    stop_reason: str = ""   # set when the job cannot go on; ends it at once with this reason


@dataclass
class Ctx:
    """What a running job hands to its tools."""
    job_id: int
    goal: str
    settings: Any
    memory: Any
    bridge: Any
    step: Callable[[str], None]
    confirm: Callable[[str], bool]
    stopped: Callable[[], bool]
    tab_id: int | None = None
    elements: dict = field(default_factory=dict)   # last browser_look, id -> element
    look_token: str = ""                           # last browser_look's secret page-marker token
    controls: dict = field(default_factory=dict)   # last app_look, id -> control
    places: set = field(default_factory=set)       # sites/apps touched, for the notebook
    used_app: bool = False


@dataclass
class Tool:
    name: str
    description: str
    params: dict[str, str]                 # name -> "type: description", "?" suffix = optional
    fn: Callable[..., Outcome]
    label: Callable[[dict], str]
    risk: Callable[[Ctx, dict], str | None] | None = None
    physical: bool = False                 # uses the real mouse/keyboard
    reads_only: bool = False               # looking, not changing
    json_schema: dict | None = None        # a ready-made parameter schema (tools from MCP servers)

    def schema(self) -> dict:
        if self.json_schema is not None:
            return {"type": "function", "function": {
                "name": self.name, "description": self.description, "parameters": self.json_schema}}
        props, required = {}, []
        for raw_name, spec in self.params.items():
            name = raw_name.rstrip("?")
            kind, _, desc = spec.partition(":")
            props[name] = {"type": kind.strip(), "description": desc.strip()}
            if not raw_name.endswith("?"):
                required.append(name)
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {"type": "object", "properties": props, "required": required},
            },
        }


REGISTRY: dict[str, Tool] = {}


def tool(name, description, params=None, label=None, risk=None, physical=False, reads_only=False):
    def register(fn):
        REGISTRY[name] = Tool(
            name, description, params or {}, fn,
            label or (lambda _a: name.replace("_", " ").capitalize()),
            risk, physical, reads_only,
        )
        return fn

    return register


def load_all() -> dict[str, Tool]:
    """Every tool available right now. Built fresh on each call, so a connector key or an MCP
    server added in Settings shows up in the next job without a restart."""
    from deskbuddy.apps import tools as _apps  # noqa: F401
    from deskbuddy.browser import tools as _browser  # noqa: F401
    from deskbuddy.files import tools as _files  # noqa: F401
    from deskbuddy.memory import tools as _memory  # noqa: F401
    from deskbuddy.brain import web as _web  # noqa: F401
    from deskbuddy.connectors import tools as connectors
    from deskbuddy.mcpclient import hub

    tools = dict(REGISTRY)
    if not connectors.enabled():  # no Composio key: leave the connector tools out
        for name in [n for n in tools if n.startswith(('connector_', 'gmail_'))]:
            del tools[name]
    tools.update(hub.get().tools())
    return tools
