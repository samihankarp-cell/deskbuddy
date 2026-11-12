"""The browser link: only the connection a request went to may answer it; port range; pairing questions."""
import asyncio
import json
import socket
import threading
import time

import pytest
from websockets.asyncio.client import connect

from deskbuddy import config
from deskbuddy.browser.bridge import Bridge, BridgeError
from deskbuddy.brain.runner import Runner

ORIGIN_A = "chrome-extension://aaaa"
ORIGIN_B = "chrome-extension://bbbb"


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture
def bridge(tmp_path):
    b = Bridge(free_port(), tmp_path / "paired.json")
    b.approve = lambda question: True
    b.start()
    deadline = time.time() + 5
    while time.time() < deadline:
        try:
            socket.create_connection(("127.0.0.1", b._port), 0.2).close()
            break
        except OSError:
            time.sleep(0.05)
    yield b
    b.stop()
    assert b._thread is not None and not b._thread.is_alive()


def run(coro):
    return asyncio.run(coro)


async def wait_until(predicate, seconds=3):
    end = time.time() + seconds
    while time.time() < end:
        if predicate():
            return True
        await asyncio.sleep(0.02)
    return False


def call_in_thread(bridge, results, **kw):
    def work():
        try:
            results.append(bridge.call("ping", timeout=kw.get("timeout", 5)))
        except BridgeError as error:
            results.append(error)
    t = threading.Thread(target=work)
    t.start()
    return t


def test_paired_client_reply_resolves_call(bridge):
    async def scenario():
        async with connect(f"ws://127.0.0.1:{bridge._port}", origin=ORIGIN_A) as ws:
            await ws.send(json.dumps({"hello": "Chrome"}))
            assert await wait_until(lambda: bridge.connected)
            results = []
            t = call_in_thread(bridge, results)
            request = json.loads(await ws.recv())
            await ws.send(json.dumps({"id": request["id"], "ok": True, "result": "pong"}))
            await asyncio.to_thread(t.join, 5)
            return results
    assert run(scenario()) == ["pong"]


def test_unpaired_connection_cannot_spoof_a_reply(bridge):
    async def scenario():
        async with connect(f"ws://127.0.0.1:{bridge._port}", origin=ORIGIN_A) as good, \
                connect(f"ws://127.0.0.1:{bridge._port}", origin=ORIGIN_B) as rogue:
            await good.send(json.dumps({"hello": "Chrome"}))
            assert await wait_until(lambda: bridge.connected)
            results = []
            t = call_in_thread(bridge, results)
            request = json.loads(await good.recv())
            # the rogue never said hello, but guesses the id
            await rogue.send(json.dumps({"id": request["id"], "ok": True, "result": "FAKE"}))
            await asyncio.sleep(0.3)
            assert results == []
            await good.send(json.dumps({"id": request["id"], "ok": True, "result": "real"}))
            await asyncio.to_thread(t.join, 5)
            return results
    assert run(scenario()) == ["real"]


def test_garbage_does_not_kill_the_server(bridge):
    async def scenario():
        async with connect(f"ws://127.0.0.1:{bridge._port}", origin=ORIGIN_B) as bad:
            for junk in ("not json{", "123", '"xhello-string"', "[1,2]", "null"):
                await bad.send(junk)
            await asyncio.sleep(0.2)
        async with connect(f"ws://127.0.0.1:{bridge._port}", origin=ORIGIN_A) as ws:
            await ws.send(json.dumps({"hello": "Chrome"}))
            assert await wait_until(lambda: bridge.connected)
            results = []
            t = call_in_thread(bridge, results)
            request = json.loads(await ws.recv())
            await ws.send(json.dumps({"id": request["id"], "ok": True, "result": 1}))
            await asyncio.to_thread(t.join, 5)
            return results, bridge._refused
    results, refused = run(scenario())
    assert results == [1] and not refused


def test_call_fails_fast_when_socket_closed(bridge):
    async def scenario():
        async with connect(f"ws://127.0.0.1:{bridge._port}", origin=ORIGIN_A) as ws:
            await ws.send(json.dumps({"hello": "Chrome"}))
            assert await wait_until(lambda: bridge.connected)
            ws_server = bridge._current
        # client gone; make the server still think it is current
        bridge._current = ws_server
        start = time.time()
        with pytest.raises(BridgeError):
            await asyncio.to_thread(bridge.call, "ping", 20)
        return time.time() - start
    assert run(scenario()) < 8


@pytest.mark.parametrize("value,expected", [("9000", 8765), ("80", 8765), ("abc", 8765),
                                            ("8767", 8767), ("8769", 8769)])
def test_ws_port_outside_the_add_on_range_falls_back(tmp_path, monkeypatch, value, expected):
    for name in ["DESKBUDDY_API_KEY", "DESKBUDDY_BASE_URL", "DESKBUDDY_PROVIDER"]:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("APPDATA", str(tmp_path / "appdata"))
    monkeypatch.setattr(config, "ROOT", tmp_path)
    monkeypatch.setenv("DESKBUDDY_PROVIDER", "ollama")
    monkeypatch.setenv("DESKBUDDY_WS_PORT", value)
    assert config.load().ws_port == expected


def test_ask_user_works_after_escape():
    runner = Runner(None, None, None)
    runner._stop.set()  # the user pressed Esc earlier
    runner.ask.connect(lambda question: runner.answer(True))
    assert runner.ask_user("Let the add-on connect?") is True
    # while a job's confirm still refuses once stopped
    assert runner._confirm("x") is False
