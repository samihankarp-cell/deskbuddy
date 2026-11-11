"""Plain conversation: small talk is answered directly, and replies carry no Done / I couldn't labels."""
from types import SimpleNamespace

from deskbuddy.brain import graph, intake
from deskbuddy.brain.report import format_report
from deskbuddy.brain.types import CheckResult, JobResult


def test_report_wording_has_no_labels():
    ok = JobResult("open notepad", CheckResult(True), summary="opened Notepad")
    bad = JobResult("play a song", CheckResult(False, "it needs a sign-in"))
    assert format_report([ok]) == "Opened Notepad."
    assert format_report([bad]) == "It needs a sign-in."
    assert format_report([JobResult("x", CheckResult(True), answer="Two new emails.")]) == "Two new emails."
    assert format_report([JobResult("x", CheckResult(False, "you said no"))]) == "Okay, I won't do that."
    for text in (format_report([ok, bad]), format_report([])):
        assert "Done" not in text and "couldn't" not in text and "Acknowledged" not in text


class _Model:
    def __init__(self, text):
        self.text = text

    def invoke(self, _messages):
        return SimpleNamespace(content=self.text)


def test_small_talk_gets_a_reply_and_no_job(monkeypatch):
    monkeypatch.setattr(intake, "fast_model", lambda _s: _Model('{"ack": "", "jobs": [], "reply": "Hey! What can I do for you?"}'))
    plan = intake.split_order(None, "hey", [])
    assert (plan.jobs, plan.reply) == ([], "Hey! What can I do for you?")


def test_a_real_order_is_still_a_job(monkeypatch):
    monkeypatch.setattr(intake, "fast_model", lambda _s: _Model('{"ack": "On it", "jobs": ["Open Notepad"], "reply": ""}'))
    plan = intake.split_order(None, "open notepad", [])
    assert plan.jobs == ["Open Notepad"] and plan.reply == ""


def test_graph_answers_small_talk_without_running_a_job(monkeypatch):
    monkeypatch.setattr(graph, "split_order", lambda *_a: intake.AckPlan("", [], "Hi there!"))
    ran = []
    monkeypatch.setattr(graph, "run_job", lambda *a: ran.append(a))
    deps = SimpleNamespace(settings=None, memory=SimpleNamespace(recent_messages=lambda _n: []),
                           step=lambda _t: None)
    state = graph.build_graph(deps).invoke({"order": "hey", "results": []})
    assert ran == [] and format_report(state["results"]) == "Hi there!"
