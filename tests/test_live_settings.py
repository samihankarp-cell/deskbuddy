"""Saving settings applies them without a restart; providers; MCP servers added from Settings."""
import pytest

from deskbuddy import config, providers
from deskbuddy.brain import llm, tools
from deskbuddy.mcpclient import servers

ENV = ["DESKBUDDY_API_KEY", "DESKBUDDY_BASE_URL", "DESKBUDDY_FAST_MODEL", "DESKBUDDY_AGENT_MODEL",
       "DESKBUDDY_PROVIDER", "COMPOSIO_API_KEY", "DESKBUDDY_HOTKEY", "DESKBUDDY_WS_PORT"]


@pytest.fixture
def env(tmp_path, monkeypatch):
    for name in ENV:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("APPDATA", str(tmp_path / "appdata"))
    monkeypatch.setattr(config, "ROOT", tmp_path)
    return tmp_path / ".env"


def test_provider_presets_fill_address_and_models(env, monkeypatch):
    monkeypatch.setenv("DESKBUDDY_PROVIDER", "openai")
    monkeypatch.setenv("DESKBUDDY_API_KEY", "sk-test")
    s = config.load()
    assert (s.provider, s.base_url, s.agent_model) == ("openai", "https://api.openai.com/v1", "gpt-4.1")


def test_old_env_without_provider_is_recognised_by_its_address(env, monkeypatch):
    monkeypatch.setenv("DESKBUDDY_API_KEY", "k")
    monkeypatch.setenv("DESKBUDDY_BASE_URL", "https://api.groq.com/openai/v1")
    assert config.load().provider == "groq"


def test_no_key_is_an_error_except_for_models_on_this_pc(env, monkeypatch):
    with pytest.raises(config.ConfigError, match="NVIDIA"):
        config.load()
    monkeypatch.setenv("DESKBUDDY_PROVIDER", "ollama")
    s = config.load()
    assert s.base_url == "http://localhost:11434/v1" and s.api_key == "none"


def test_custom_provider_needs_an_address(env, monkeypatch):
    monkeypatch.setenv("DESKBUDDY_PROVIDER", "custom")
    monkeypatch.setenv("DESKBUDDY_API_KEY", "k")
    with pytest.raises(config.ConfigError, match="address"):
        config.load()


def test_reload_changes_the_same_object_and_the_next_model_uses_it(env):
    env.write_text("DESKBUDDY_API_KEY=first\nDESKBUDDY_PROVIDER=nvidia\n")
    settings = config.load()
    held_by_brain = settings                      # the runner keeps this very object
    env.write_text("DESKBUDDY_API_KEY=second\nDESKBUDDY_PROVIDER=openai\nDESKBUDDY_WS_PORT=9000\n")
    changed = config.reload(settings)
    assert {"api_key", "provider", "base_url", "agent_model", "ws_port"} <= set(changed)
    assert held_by_brain.api_key == "second" and held_by_brain.provider == "openai"
    model = llm.agent_model(held_by_brain)
    assert model.model_name == "gpt-4.1" and "openai.com" in str(model.openai_api_base)


def test_failed_reload_keeps_the_working_settings(env):
    env.write_text("DESKBUDDY_API_KEY=good\n")
    settings = config.load()
    env.write_text("DESKBUDDY_API_KEY=\n")
    with pytest.raises(config.ConfigError):
        config.reload(settings)
    assert settings.api_key == "good"


def test_connector_tools_follow_the_composio_key_without_restart(env, monkeypatch):
    monkeypatch.delenv("COMPOSIO_API_KEY", raising=False)
    assert "connector_run" not in tools.load_all()
    monkeypatch.setenv("COMPOSIO_API_KEY", "abc")
    assert "connector_run" in tools.load_all()          # was deleted for good before
    monkeypatch.setenv("COMPOSIO_API_KEY", "")
    assert "connector_run" not in tools.load_all()


def test_save_button_writes_provider_and_signals_the_app(qtbot, tmp_path, env):
    from deskbuddy.memory.db import Memory
    from deskbuddy.ui.hub.settings_page import SettingsPage

    page = SettingsPage(Memory(tmp_path / "m.db"), env_file=tmp_path / "x.env")
    qtbot.addWidget(page)
    page.choose_provider("openai")
    assert page.boxes["DESKBUDDY_BASE_URL"].text() == "https://api.openai.com/v1"
    assert page.boxes["DESKBUDDY_AGENT_MODEL"].text() == "gpt-4.1"
    page.boxes["DESKBUDDY_API_KEY"].setText("sk-live")
    with qtbot.waitSignal(page.settings_saved, timeout=1000):
        page.save()
    text = (tmp_path / "x.env").read_text()
    assert "DESKBUDDY_PROVIDER=openai" in text and "DESKBUDDY_API_KEY=sk-live" in text
    page.say_applied("Saved and applied.")
    assert page.saved.text() == "Saved and applied."


def test_custom_provider_keeps_what_was_typed(qtbot, tmp_path, env):
    from deskbuddy.memory.db import Memory
    from deskbuddy.ui.hub.settings_page import SettingsPage

    page = SettingsPage(Memory(tmp_path / "m.db"), env_file=tmp_path / "x.env")
    qtbot.addWidget(page)
    page.boxes["DESKBUDDY_BASE_URL"].setText("https://my.host/v1")
    page.choose_provider(providers.CUSTOM)
    assert page.boxes["DESKBUDDY_BASE_URL"].text() == "https://my.host/v1"


def test_adding_and_removing_an_mcp_server_from_settings(qtbot, tmp_path, env):
    from deskbuddy.memory.db import Memory
    from deskbuddy.ui.hub.settings_page import SettingsPage

    page = SettingsPage(Memory(tmp_path / "m.db"), env_file=tmp_path / "x.env")
    qtbot.addWidget(page)
    page.add_mcp_server()                                # empty form: refused, nothing saved
    assert "short name" in page.mcp_note.text() and servers.load() == []
    page.mcp_name.setText("Composio")
    page.mcp_target.setText("https://127.0.0.1:9/mcp")    # nothing listens here: it will fail, quietly
    page.mcp_extra.setText("x-api-key: abc")
    page.add_mcp_server()
    [saved] = servers.load()
    assert (saved.name, saved.transport, saved.headers) == ("composio", "http", {"x-api-key": "abc"})
    assert page.mcp_target.text() == ""
    page._change_mcp("composio", "toggle")
    assert servers.load()[0].enabled is False
    page._change_mcp("composio", "remove")
    assert servers.load() == []
