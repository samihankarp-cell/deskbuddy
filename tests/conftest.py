"""Keep every test away from the real MCP server list and the shared connection hub."""
import pytest

from deskbuddy.mcpclient import hub, servers


@pytest.fixture(autouse=True)
def isolated_mcp(tmp_path, monkeypatch):
    monkeypatch.setattr(servers, "path", lambda: tmp_path / "mcp_servers.json")
    monkeypatch.setattr(hub, "_hub", hub.McpHub())
    yield
    hub.get().shutdown()
