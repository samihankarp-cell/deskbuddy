"""Connects to MCP servers and turns their tools into Desk Buddy tools.

Each server runs as one task on a private asyncio loop (its own thread). The task opens the
connection, lists the tools, then waits until the server is removed. Everything about one
connection stays inside that one task, as the MCP SDK requires.
"""
import asyncio
import atexit
import os
import re
import shutil
import threading
from contextlib import AsyncExitStack
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any

from deskbuddy import config
from deskbuddy.brain.tools import Ctx, Outcome, Tool
from deskbuddy.mcpclient.servers import HTTP, SSE, STDIO, Server

CONNECT_TIMEOUT = 45     # seconds to start a server and list its tools
CALL_TIMEOUT = 90        # seconds for one tool call
RESULT_LIMIT = 6000
STOP_TIMEOUT = 8

READ_WORDS = {"get", "list", "search", "read", "fetch", "find", "query", "describe", "show",
              "view", "check", "lookup", "count"}
SEND_WORDS = {"send", "reply", "forward", "post", "publish", "tweet", "invite", "share", "email"}
DELETE_WORDS = {"delete", "remove", "trash", "purge", "empty", "drop", "destroy", "erase"}
BUY_WORDS = {"pay", "purchase", "charge", "checkout", "order", "buy", "transfer"}


@dataclass
class State:
    server: Server
    status: str = "connecting"          # connecting | connected | failed
    error: str = ""
    tools: list = field(default_factory=list)   # mcp.types.Tool
    session: Any = None
    stop: Any = None                    # asyncio.Event, made on the loop
    task: Any = None


def _words(name: str) -> list[str]:
    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", name)
    return [w for w in re.split(r"[^A-Za-z0-9]+", spaced.lower()) if w]


# Keys that name an action to run. Plain "name" is left out: file and record tools use it for
# ordinary names ("delete_old.txt") and would ask for no reason.
ACTION_KEYS = {"tool_slug", "slug", "action", "tool_name", "tool"}


def _actions_in(value, depth: int = 0) -> list[str]:
    """Action names a call's arguments point at (Composio's execute tools take them as data)."""
    found: list[str] = []
    if depth > 6:
        return found
    if isinstance(value, dict):
        for key, item in value.items():
            if str(key).lower() in ACTION_KEYS and isinstance(item, str) and item.strip():
                found.append(item.strip())
            else:
                found += _actions_in(item, depth + 1)
    elif isinstance(value, list):
        for item in value[:50]:
            found += _actions_in(item, depth + 1)
    return found


def _kind(name: str, action: bool = False) -> str | None:
    words = _words(name)
    if not action and words and words[0] in READ_WORDS:
        return None
    if DELETE_WORDS & set(words):
        return "this can delete or overwrite things"
    if BUY_WORDS & set(words):
        return "this looks like buying or paying"
    if SEND_WORDS & set(words) and not (action and READ_WORDS & set(words)):
        return "this sends or shares something"
    return None


def risk_of(server: str, tool, arguments: dict | None = None) -> str | None:
    """Words for the Yes / No question, or None when the call looks harmless. The tool's name
    decides (unless the server says it only reads), and so does any action its arguments name,
    because a generic execute tool hides the real action there."""
    hints = getattr(tool, "annotations", None)
    if not getattr(hints, "readOnlyHint", None):
        why = _kind(tool.name)
        if why:
            return f"use {tool.name.replace('_', ' ')} on {server} ({why})"
    for action in dict.fromkeys(_actions_in(arguments)):
        why = _kind(action, action=True)
        if why:
            return f"use {' '.join(_words(action))} on {server} ({why})"
    return None


def _flatten(error: BaseException) -> str:
    """The real cause inside the groups of errors anyio wraps around everything."""
    while getattr(error, "exceptions", None):
        error = error.exceptions[0]
    return (str(error) or type(error).__name__)[:200]


def _explain(message: str) -> str:
    """One short line, with the usual causes spelled out."""
    first = message.strip().splitlines()[0] if message.strip() else "unknown error"
    if "401" in first or "403" in first or "nauthorized" in first:
        return ("the server refused the key (" + ("401" if "401" in first else "403") + "). Check the key "
                "and its header. Composio's connect.composio.dev wants the ck_ key as x-consumer-api-key.")
    return first[:200]


def _text_of(result) -> str:
    parts = []
    for item in getattr(result, "content", None) or []:
        kind = getattr(item, "type", "")
        if kind == "text":
            parts.append(item.text)
        elif kind == "resource" and getattr(item.resource, "text", None):
            parts.append(item.resource.text)
        else:
            parts.append(f"[{kind or 'unknown'} content]")
    if not parts and getattr(result, "structuredContent", None):
        parts.append(str(result.structuredContent))
    return "\n".join(parts)


class McpHub:
    def __init__(self):
        self._loop: asyncio.AbstractEventLoop | None = None
        self._lock = threading.Lock()
        self._states: dict[str, State] = {}
        self.configured: list[Server] = []

    # ---- the background loop ----------------------------------------------------------
    def _ensure_loop(self) -> asyncio.AbstractEventLoop:
        with self._lock:
            if self._loop is None:
                loop = asyncio.new_event_loop()
                threading.Thread(target=loop.run_forever, daemon=True, name="buddy-mcp").start()
                self._loop = loop
                atexit.register(self.shutdown)
            return self._loop

    def apply(self, servers: list[Server]) -> None:
        """Make the running connections match `servers`. Returns at once; connecting happens
        in the background and shows up in `status()`."""
        self.configured = list(servers)
        if not servers and not self._states:
            return
        asyncio.run_coroutine_threadsafe(self._apply(list(servers)), self._ensure_loop())

    def retry(self, name: str) -> None:
        servers = list(self.configured)
        wanted = next((s for s in servers if s.name == name), None)
        if wanted is None:
            return
        asyncio.run_coroutine_threadsafe(self._restart(wanted), self._ensure_loop())

    def shutdown(self) -> None:
        loop = self._loop
        if loop is None or not loop.is_running():
            return
        try:
            asyncio.run_coroutine_threadsafe(self._apply([]), loop).result(STOP_TIMEOUT + 2)
        except Exception:
            pass

    async def _apply(self, servers: list[Server]) -> None:
        wanted = {s.name: s for s in servers if s.enabled}
        for name in [n for n, st in self._states.items() if wanted.get(n) != st.server]:
            await self._stop(name)
        for name, server in wanted.items():
            if name not in self._states:
                self._start(server)

    async def _restart(self, server: Server) -> None:
        await self._stop(server.name)
        if server.enabled:
            self._start(server)

    def _start(self, server: Server) -> None:
        state = State(server, stop=asyncio.Event())
        self._states[server.name] = state
        state.task = asyncio.get_running_loop().create_task(self._run(state))

    async def _stop(self, name: str) -> None:
        state = self._states.pop(name, None)
        if state is None:
            return
        state.stop.set()
        try:
            await asyncio.wait_for(state.task, STOP_TIMEOUT)
        except (asyncio.TimeoutError, asyncio.CancelledError, Exception):
            state.task.cancel()

    async def _run(self, state: State) -> None:
        server = state.server
        log = None
        try:
            async with AsyncExitStack() as stack:
                if server.transport == STDIO:
                    from mcp import StdioServerParameters
                    from mcp.client.stdio import stdio_client

                    # a log file per server: the SDK writes the server's own messages there
                    log = open(config.data_dir() / f"mcp-{server.name}.log", "a", encoding="utf-8")
                    stack.callback(log.close)
                    command = shutil.which(server.command) or server.command   # npx -> npx.cmd
                    params = StdioServerParameters(command=command, args=server.args,
                                                   env=server.env or None)
                    read, write = await stack.enter_async_context(stdio_client(params, errlog=log))
                elif server.transport == SSE:
                    from mcp.client.sse import sse_client

                    read, write = await stack.enter_async_context(
                        sse_client(server.url, headers=server.headers or None))
                else:
                    from mcp.client.streamable_http import streamable_http_client
                    from mcp.shared._httpx_utils import create_mcp_http_client

                    client = create_mcp_http_client(headers=server.headers or None)
                    await stack.enter_async_context(client)   # closed with the connection
                    read, write, _ = await stack.enter_async_context(
                        streamable_http_client(server.url, http_client=client))
                from mcp import ClientSession

                session = await stack.enter_async_context(ClientSession(read, write))
                await asyncio.wait_for(session.initialize(), CONNECT_TIMEOUT)
                tools, cursor = [], None
                while True:
                    page = await asyncio.wait_for(session.list_tools(cursor), CONNECT_TIMEOUT)
                    tools += page.tools
                    cursor = page.nextCursor
                    if not cursor:
                        break
                state.tools, state.session, state.status = tools, session, "connected"
                await state.stop.wait()
        except asyncio.CancelledError:
            raise
        except BaseException as error:
            state.status, state.error = "failed", _explain(_flatten(error))
            if "timeout" in type(error).__name__.lower() or isinstance(error, asyncio.TimeoutError):
                state.error = "it did not answer in time"
        finally:
            state.session = None
            if state.status == "connected":
                state.status = "failed" if not state.stop.is_set() else state.status

    # ---- for the rest of the app ---------------------------------------------------------
    def status(self) -> list[tuple[Server, str, str, int]]:
        """(server, status, error, number of tools) for every server in the list."""
        rows = []
        for server in self.configured:
            state = self._states.get(server.name)
            if not server.enabled:
                rows.append((server, "off", "", 0))
            elif state is None:
                rows.append((server, "connecting", "", 0))
            else:
                rows.append((server, state.status, state.error, len(state.tools)))
        return rows

    def tools(self) -> dict[str, Tool]:
        """Desk Buddy tools for every tool of every connected server."""
        out: dict[str, Tool] = {}
        for state in list(self._states.values()):
            if state.status != "connected":
                continue
            for item in state.tools:
                name = f"mcp_{state.server.name}_{item.name}"
                name = re.sub(r"[^A-Za-z0-9_-]", "_", name)[:64]
                while name in out:
                    name = name[:60] + "_" + str(len(out) % 1000)
                out[name] = self._wrap(state.server.name, item, name)
        return out

    def _wrap(self, server: str, item, name: str) -> Tool:
        schema = dict(item.inputSchema or {})
        schema.pop("$schema", None)
        schema.setdefault("type", "object")
        schema.setdefault("properties", {})
        hints = getattr(item, "annotations", None)

        def run(ctx: Ctx, **arguments) -> Outcome:
            ctx.places.add(server)
            ok, text = self.call(server, item.name, arguments)
            return Outcome(ok, text or ("Done." if ok else "the server gave no reason"), verified=ok)

        description = f"[{server}] {(item.description or item.name).strip()}"[:1000]
        return Tool(name, description, {}, run,
                    label=lambda _a, t=item.name, s=server: f"Using {t.replace('_', ' ')} ({s})",
                    risk=lambda _c, a, i=item, s=server: risk_of(s, i, a),
                    reads_only=bool(getattr(hints, "readOnlyHint", False)),
                    json_schema=schema)

    def call(self, server: str, tool: str, arguments: dict, timeout: int = CALL_TIMEOUT) -> tuple[bool, str]:
        state = self._states.get(server)
        if state is None or state.session is None or self._loop is None:
            return False, f"{server} is not connected right now"
        future = asyncio.run_coroutine_threadsafe(
            state.session.call_tool(tool, arguments or {}, read_timeout_seconds=timedelta(seconds=timeout)),
            self._loop)
        try:
            result = future.result(timeout + 5)
        except Exception as error:
            future.cancel()
            return False, f"{server} did not answer ({_flatten(error)})"
        text = _text_of(result)[:RESULT_LIMIT]
        return (not getattr(result, "isError", False)), text


_hub: McpHub | None = None


def get() -> McpHub:
    global _hub
    if _hub is None:
        _hub = McpHub()
    return _hub
