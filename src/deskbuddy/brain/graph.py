"""The LangGraph flow of one order: intake -> jobs side by side -> report."""
import operator
from typing import Annotated, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.types import Send

from deskbuddy.brain.agent import run_job
from deskbuddy.brain.intake import split_order
from deskbuddy.brain.report import format_report
from deskbuddy.brain.types import JobResult


class OrderState(TypedDict, total=False):
    order: str
    ack: str
    jobs: list[str]
    results: Annotated[list[JobResult], operator.add]
    report: str


def build_graph(deps):
    def intake(state: OrderState) -> dict:
        plan = split_order(deps.settings, state["order"], deps.memory.recent_messages(6))
        deps.step(plan.ack)
        return {"ack": plan.ack, "jobs": plan.jobs}

    def fan_out(state: OrderState):
        return [Send("job", {"order": state["order"], "goal": goal}) for goal in state["jobs"]]

    def job(payload: dict) -> dict:
        return {"results": [run_job(deps, payload["order"], payload["goal"])]}

    def report(state: OrderState) -> dict:
        return {"report": format_report(state.get("results", []))}

    graph = StateGraph(OrderState)
    graph.add_node("intake", intake)
    graph.add_node("job", job)
    graph.add_node("report", report)
    graph.add_edge(START, "intake")
    graph.add_conditional_edges("intake", fan_out, ["job"])
    graph.add_edge("job", "report")
    graph.add_edge("report", END)
    return graph.compile()
