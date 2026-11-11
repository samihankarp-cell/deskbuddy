"""MCP servers: parsing what the user types, risk wording, and a real stdio round trip."""
import sys
import time
from pathlib import Path

import pytest

from deskbuddy.mcpclient import servers
from deskbuddy.mcpclient.hub import McpHub, risk_of

FIXTURE = Path(__file__).parent / "fixtures" / "echo_mcp_server.py"


def test_web_address_becomes_http_server_with_headers():
    [s] = servers.parse("Composio", "https://mcp.example.com/server/abc/mcp", "x-api-key: k1; Other: v")
    assert (s.name, s.transport, s.url) == ("composio", "http", "https://mcp.example.com/server/abc/mcp")
    assert s.headers == {"x-api-key": "k1", "Other": "v"}


def test_sse_address_and_program_command():
    assert servers.parse("a", "https://x.test/sse")[0].transport == "sse"
    [s] = servers.parse("files", "npx -y @modelcontextprotocol/server-filesystem C:/tmp", "TOKEN=1")
    assert (s.transport, s.command, s.args, s.env) == (
        "stdio", "npx", ["-y", "@modelcontextprotocol/server-filesystem", "C:/tmp"], {"TOKEN": "1"})


def test_pasted_mcpservers_json():
    pasted = '{"mcpServers": {"Composio": {"url": "https://c.test/mcp", "headers": {"A": "b"}}, ' \
             '"fs": {"command": "npx", "args": ["-y", "pkg"], "env": {"K": "V"}}}}'
    one, two = servers.parse("", pasted)
    assert (one.name, one.transport, one.headers) == ("composio", "http", {"A": "b"})
    assert (two.name, two.command, two.args, two.env) == ("fs", "npx", ["-y", "pkg"], {"K": "V"})


@pytest.mark.parametrize("name,target", [("", "npx x"), ("a", ""), ("a", "{not json")])
def test_bad_input_is_refused_with_a_reason(name, target):
    with pytest.raises(servers.ServerError):
        servers.parse(name, target)


def test_save_load_and_replace_same_name(tmp_path):
    file = tmp_path / "s.json"
    first = servers.from_fields("a", "https://one.test/mcp")
    servers.save([first], file)
    assert servers.load(file) == [first]
    again = servers.add(servers.load(file), [servers.from_fields("a", "https://two.test/mcp")])
    assert [s.url for s in again] == ["https://two.test/mcp"]


class _Tool:
    def __init__(self, name, **hints):
        self.name = name
        self.annotations = type("A", (), hints)() if hints else None


def test_risk_wording_by_name_and_hints():
    assert risk_of("mail", _Tool("list_threads")) is None
    assert risk_of("mail", _Tool("get_order")) is None            # reading, even with "order" in it
    assert "sends" in risk_of("mail", _Tool("send_email"))
    assert "delete" in risk_of("fs", _Tool("deleteFile"))
    assert risk_of("fs", _Tool("send_email", readOnlyHint=True)) is None
    assert risk_of("x", _Tool("update_thing", destructiveHint=True)) is not None
    assert risk_of("x", _Tool("update_thing")) is None


def test_stdio_server_end_to_end(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    hub = McpHub()
    hub.apply([servers.Server("echo", "stdio", command=sys.executable, args=[str(FIXTURE)])])
    try:
        deadline = time.time() + 40
        while time.time() < deadline and hub.status()[0][1] == "connecting":
            time.sleep(0.2)
        server, status, error, count = hub.status()[0]
        assert status == "connected", error
        tools = hub.tools()
        assert {"mcp_echo_echo", "mcp_echo_send_email"} <= set(tools)
        assert tools["mcp_echo_send_email"].risk(None, {}) is not None
        assert tools["mcp_echo_echo"].risk is None
        schema = tools["mcp_echo_echo"].schema()["function"]["parameters"]
        assert schema["required"] == ["text"]
        assert hub.call("echo", "echo", {"text": "hi"}) == (True, "echo: hi")
        hub.apply([])                                   # removing the server drops its tools
        deadline = time.time() + 10
        while time.time() < deadline and hub.tools():
            time.sleep(0.2)
        assert hub.tools() == {}
    finally:
        hub.shutdown()


def test_unreachable_server_reports_failure(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    hub = McpHub()
    hub.apply([servers.Server("nope", "stdio", command="definitely-not-a-program-xyz")])
    try:
        deadline = time.time() + 20
        while time.time() < deadline and hub.status()[0][1] == "connecting":
            time.sleep(0.2)
        assert hub.status()[0][1] == "failed" and hub.status()[0][2]
    finally:
        hub.shutdown()


def test_bare_key_is_sent_the_way_each_server_expects():
    [c] = servers.parse("c", "https://connect.composio.dev/mcp", "ck_abc")
    assert c.headers == {"x-consumer-api-key": "ck_abc"}
    [c] = servers.parse("c", "https://connect.composio.dev/mcp", "x-api-key: ck_abc")   # wrong name fixed
    assert c.headers == {"x-consumer-api-key": "ck_abc"}
    [m] = servers.parse("m", "https://mcp.composio.dev/x/mcp", "ak_1")
    assert m.headers == {"x-api-key": "ak_1"}
    [o] = servers.parse("o", "https://other.test/mcp", "Bearer sk-1")
    assert o.headers == {"Authorization": "Bearer sk-1"}


def test_refused_key_is_explained_in_one_line():
    from deskbuddy.mcpclient.hub import _explain

    text = _explain("Client error '401 Unauthorized' for url 'x'\nFor more information check: y")
    assert "refused the key" in text and "\n" not in text
