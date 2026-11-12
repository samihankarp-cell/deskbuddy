"""One reply can hold several tool calls: a refusal or a stop must end the whole batch."""
from types import SimpleNamespace

from langchain_core.messages import AIMessage

from deskbuddy.brain import agent
from deskbuddy.brain.tools import Ctx, Outcome, Tool
from deskbuddy.brain.types import CheckResult


class _Model:
    """Hands back one scripted reply per turn."""

    def __init__(self, replies):
        self.replies = list(replies)

    def bind_tools(self, _tools):
        return self

    def invoke(self, _messages):
        return self.replies.pop(0)


def _batch(*names):
    calls = [{"name": n, "args": {}, "id": f"id{i}"} for i, n in enumerate(names)]
    return AIMessage(content="", tool_calls=calls)


def _setup(monkeypatch, replies, tools):
    monkeypatch.setattr(agent, "load_all", lambda: tools)
    monkeypatch.setattr(agent, "agent_model", lambda _s: _Model(replies))
    monkeypatch.setattr(agent, "_about_user", lambda _c: "")
    monkeypatch.setattr(agent, "_check", lambda *_a: CheckResult(True))


def _tool(name, ran, risk=None, stop_reason=""):
    def fn(_ctx):
        ran.append(name)
        return Outcome(True, "ok", verified=True, stop_reason=stop_reason)
    return Tool(name=name, description=name, params={}, fn=fn, label=lambda _a: name,
                risk=(lambda _c, _a: risk) if risk else None)


def _ctx(confirm=lambda _q: True, stopped=lambda: False):
    memory = SimpleNamespace(recent_messages=lambda _n: [], notes_for=lambda _g: [])
    return Ctx(job_id=1, goal="g", settings=None, memory=memory, bridge=None,
               step=lambda _t: None, confirm=confirm, stopped=stopped)


def test_refusal_stops_the_rest_of_the_batch(monkeypatch):
    ran = []
    tools = {"danger": _tool("danger", ran, risk="delete forever"), "safe": _tool("safe", ran)}
    _setup(monkeypatch, [_batch("danger", "safe")], tools)
    result = agent._work(_ctx(confirm=lambda _q: False), "g", [])
    assert ran == []
    assert result.check.reason == "you said no"


def test_stop_mid_batch_skips_the_rest(monkeypatch):
    ran = []
    tools = {"a": _tool("a", ran), "b": _tool("b", ran)}
    _setup(monkeypatch, [_batch("a", "b")], tools)
    result = agent._work(_ctx(stopped=lambda: bool(ran)), "g", [])
    assert ran == ["a"]
    assert (result.check.passed, result.check.reason) == (False, "you stopped me")


def test_stop_reason_ends_the_batch(monkeypatch):
    ran = []
    tools = {"a": _tool("a", ran, stop_reason="needs sign-in"), "b": _tool("b", ran)}
    _setup(monkeypatch, [_batch("a", "b")], tools)
    result = agent._work(_ctx(), "g", [])
    assert ran == ["a"]
    assert result.check.reason == "needs sign-in"


def test_finish_ends_the_batch(monkeypatch):
    ran = []
    tools = {"b": _tool("b", ran)}
    reply = AIMessage(content="", tool_calls=[
        {"name": "finish", "args": {"summary": "did it"}, "id": "f"},
        {"name": "b", "args": {}, "id": "b"}])
    _setup(monkeypatch, [reply], tools)
    result = agent._work(_ctx(), "g", [])
    assert ran == [] and result.check.passed


def test_normal_batch_runs_every_tool(monkeypatch):
    ran = []
    tools = {"a": _tool("a", ran), "b": _tool("b", ran)}
    finish = AIMessage(content="", tool_calls=[
        {"name": "finish", "args": {"summary": "did it"}, "id": "f"}])
    _setup(monkeypatch, [_batch("a", "b"), finish], tools)
    result = agent._work(_ctx(), "g", [])
    assert ran == ["a", "b"] and result.check.passed
