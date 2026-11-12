"""The local link between Desk Buddy and its browser add-on (this PC only)."""
import asyncio
import concurrent.futures
import itertools
import json
import threading

from websockets.asyncio.server import serve

ALLOWED_ORIGINS = ("chrome-extension://", "moz-extension://")


class BridgeError(Exception):
    pass


class Bridge:
    def __init__(self, port: int, paired_file=None):
        self._port = port
        self._paired_file = paired_file
        self._paired = (set(json.loads(paired_file.read_text()))
                        if paired_file and paired_file.exists() else set())
        self.approve = None  # set by the app: approve(question) -> bool
        self._refused: set[str] = set()
        self._loop = asyncio.new_event_loop()
        self._clients: dict = {}      # connection -> browser name
        self._current = None          # the browser used most recently
        self._pending: dict[int, tuple] = {}  # id -> (connection asked, future)
        self._ids = itertools.count(1)
        self.start_error: str | None = None
        self._done: asyncio.Event | None = None   # set to close the server (made on the loop)
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        self._thread = threading.Thread(target=self._run, daemon=True, name="buddy-bridge")
        self._thread.start()

    def stop(self, timeout: float = 5) -> None:
        """Close the server and end its thread (tests, and a clean quit)."""
        if self._done is not None and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._done.set)
        if self._thread is not None:
            self._thread.join(timeout)

    def _run(self) -> None:
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._serve())
        except Exception as error:  # e.g. the port is taken
            self.start_error = str(error)

    async def _serve(self) -> None:
        self._done = asyncio.Event()
        async with serve(self._handle, "127.0.0.1", self._port, max_size=8 * 1024 * 1024):
            await self._done.wait()

    async def _handle(self, ws) -> None:
        origin = ws.request.headers.get("Origin", "")
        if not origin.startswith(ALLOWED_ORIGINS):
            await ws.close(1008, "only the Desk Buddy add-on may connect")
            return
        try:
            async for raw in ws:
                try:
                    msg = json.loads(raw)
                except ValueError:
                    continue
                if not isinstance(msg, dict):
                    continue
                if "hello" in msg:
                    name = str(msg["hello"])
                    if origin in self._refused:
                        await ws.close(1008, "not approved")
                        return
                    if origin not in self._paired:  # first time this add-on connects: ask once
                        ask = self.approve
                        allowed = bool(ask) and await self._loop.run_in_executor(
                            None, ask, f"Let the Desk Buddy add-on in {name} connect to me?")
                        if not allowed:
                            self._refused.add(origin)
                            await ws.close(1008, "not approved")
                            return
                        self._paired.add(origin)
                        if self._paired_file:
                            self._paired_file.write_text(json.dumps(sorted(self._paired)))
                    self._clients[ws] = name
                    self._current = ws
                elif ws not in self._clients:
                    continue  # never said hello / not approved: ignore everything else
                elif "active" in msg:
                    self._current = ws
                elif "id" in msg:
                    entry = self._pending.get(msg["id"]) if isinstance(msg["id"], int) else None
                    # only the connection the request went to may answer it
                    if entry and entry[0] is ws:
                        self._pending.pop(msg["id"], None)
                        if not entry[1].done():
                            entry[1].set_result(msg)
        finally:
            self._clients.pop(ws, None)
            if self._current is ws:
                self._current = next(iter(self._clients), None)

    # ---- used by the tools (any thread) ----------------------------------
    @property
    def connected(self) -> bool:
        return self._current is not None

    @property
    def browser(self) -> str:
        return self._clients.get(self._current, "your browser")

    def call(self, method: str, timeout: float = 30, **params):
        ws = self._current
        if ws is None:
            raise BridgeError("the Desk Buddy add-on is not connected in your browser")
        msg_id = next(self._ids)
        future: concurrent.futures.Future = concurrent.futures.Future()
        self._pending[msg_id] = (ws, future)
        payload = json.dumps({"id": msg_id, "method": method, "params": params})
        sent = asyncio.run_coroutine_threadsafe(ws.send(payload), self._loop)
        try:
            try:
                sent.result(min(2, timeout))  # a closed socket fails here, so don't wait it out
            except concurrent.futures.TimeoutError:
                pass
            except Exception:
                self._pending.pop(msg_id, None)
                raise BridgeError("the browser connection closed") from None
            reply = future.result(timeout)
        except concurrent.futures.TimeoutError:
            self._pending.pop(msg_id, None)
            raise BridgeError(f"the browser did not answer '{method}' in time") from None
        if not reply.get("ok"):
            raise BridgeError(str(reply.get("error", "the browser refused")))
        return reply.get("result")
