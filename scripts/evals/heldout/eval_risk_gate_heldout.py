"""HELD-OUT variant: measure the risk gate on blind cases written from the documented policy only.

Loads scripts/evals/heldout/risk_cases_heldout.json, calls the real `risk(ctx, args)` function of each tool
(no network, no browser, no AI model, no file is touched), compares with the label, and writes
scripts/evals/heldout/results/risk_gate_heldout.json.

Run:  uv run python scripts/evals/heldout/eval_risk_gate_heldout.py
"""
import json
import os
import sys
import types
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
CASES = HERE / "risk_cases_heldout.json"
OUT = HERE / "results" / "risk_gate_heldout.json"


def make_ctx(setup: dict):
    from deskbuddy.brain.tools import Ctx

    class FakeBridge:
        connected = True
        browser = "FakeBrowser"

        def call(self, name, **kw):  # only reached if a tool does NOT refuse on its own
            return {"value": kw.get("text", ""), "url": "https://fake.test", "title": "fake", "tabId": 1}

    ctx = Ctx(job_id=0, goal="eval", settings=None, memory=None, bridge=FakeBridge(),
              step=lambda _s: None, confirm=lambda _q: False, stopped=lambda: False)
    if "elements" in setup:
        ctx.elements = {int(k): v for k, v in setup["elements"].items()}
    if "controls" in setup:
        ctx.controls = {int(k): types.SimpleNamespace(
            element_info=types.SimpleNamespace(name=v, control_type="Button"))
            for k, v in setup["controls"].items()}
    return ctx


def expand(value):
    """Replace {HOME} in string arguments."""
    home = str(Path.home())
    if isinstance(value, str):
        return value.replace("{HOME}", home)
    if isinstance(value, dict):
        return {k: expand(v) for k, v in value.items()}
    if isinstance(value, list):
        return [expand(v) for v in value]
    return value


def run_gate(case: dict, registry: dict):
    """Returns the question the gate would ask (a string) or None."""
    from deskbuddy.mcpclient.hub import risk_of

    args = expand(case["args"])
    if case["tool"] == "mcp_tool":
        s = case["setup"]
        hints = types.SimpleNamespace(readOnlyHint=s["read_only"]) if s.get("read_only") is not None else None
        item = types.SimpleNamespace(name=s["tool_name"], annotations=hints)
        return risk_of(s["server"], item, args)
    tool = registry[case["tool"]]
    if tool.risk is None:
        return None
    return tool.risk(make_ctx(case["setup"]), args)


def run_refusal(case: dict, registry: dict) -> tuple[bool, str]:
    """Does the tool itself refuse? Never runs a file tool body (nothing on disk is touched)."""
    args = expand(case["args"])
    if case["tool"] == "browser_type":
        ctx = make_ctx(case["setup"])
        outcome = registry["browser_type"].fn(ctx, **args)
        return (not outcome.ok and "password" in outcome.text.lower()), outcome.text[:100]
    from deskbuddy.files.tools import _refuse

    verb = "delete"
    refused = _refuse(args.get("path"), verb)
    return refused is not None, (refused.text if refused else "not refused")


def rates(rows: list[dict]) -> dict:
    risky = [r for r in rows if r["should_ask"]]
    safe = [r for r in rows if not r["should_ask"]]
    tp = sum(1 for r in risky if r["asked"])
    fp = sum(1 for r in safe if r["asked"])
    return {
        "cases": len(rows), "risky": len(risky), "harmless": len(safe),
        "flagged_correctly": tp, "missed": len(risky) - tp, "false_alarms": fp,
        "recall": round(tp / len(risky), 4) if risky else None,
        "false_alarm_rate": round(fp / len(safe), 4) if safe else None,
    }


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.path.insert(0, str(HERE.parents[2] / "src"))
    from deskbuddy.apps import tools as _a  # noqa: F401  (registers tools)
    from deskbuddy.browser import tools as _b  # noqa: F401
    from deskbuddy.connectors import tools as _c  # noqa: F401
    from deskbuddy.files import tools as _f  # noqa: F401
    from deskbuddy.brain.tools import REGISTRY

    data = json.loads(CASES.read_text(encoding="utf-8"))
    results, errors = [], 0
    for case in data["cases"]:
        row = {k: case[k] for k in ("id", "tool", "group", "subtype", "kind", "category", "should_ask", "note")}
        row["args"] = case["args"]
        row["setup"] = case["setup"]
        try:
            if case["kind"] == "refusal":
                refused, detail = run_refusal(case, REGISTRY)
                gate = run_gate(case, REGISTRY) if case["tool"] != "browser_type" else None
                row.update(tool_refused=refused, detail=detail, asked=bool(gate), question=gate,
                           correct=refused)
            else:
                question = run_gate(case, REGISTRY)
                row.update(asked=bool(question), question=question,
                           correct=bool(question) == case["should_ask"])
        except Exception as error:  # a crash in a risk function counts against it and is shown
            errors += 1
            row.update(asked=False, question=None, correct=False, tool_refused=False, error=f"{type(error).__name__}: {error}")
        if row["kind"] == "gate":
            row["outcome"] = ("TP" if row["asked"] else "FN") if row["should_ask"] else ("FP" if row["asked"] else "TN")
        results.append(row)

    gate = [r for r in results if r["kind"] == "gate"]
    refusal = [r for r in results if r["kind"] == "refusal"]
    by = lambda key, rows: {k: rates(v) for k, v in sorted(_group(rows, key).items())}
    summary = {
        "total_cases": len(results), "gate_cases": len(gate), "refusal_cases": len(refusal), "crashes": errors,
        "overall": rates(gate),
        "main": rates([r for r in gate if r["group"] == "main"]),
        "messy": rates([r for r in gate if r["group"] == "messy"]),
        "multilingual": rates([r for r in gate if r["group"] == "multilingual"]),
        "by_category": by("category", gate),
        "by_tool": by("tool", gate),
        "by_category_main": by("category", [r for r in gate if r["group"] == "main"]),
        "refusal_checks": {"cases": len(refusal), "refused": sum(r["tool_refused"] for r in refusal),
                           "not_refused_ids": [r["id"] for r in refusal if not r["tool_refused"]]},
        "misses": [{"id": r["id"], "group": r["group"], "subtype": r["subtype"], "tool": r["tool"], "note": r["note"],
                    "args": r["args"] if r["tool"] != "browser_click" else (r["setup"]["elements"]["1"]["text"] or r["setup"]["elements"]["1"]["label"])}
                   for r in gate if r["outcome"] == "FN"],
        "false_alarms": [{"id": r["id"], "group": r["group"], "tool": r["tool"], "note": r["note"], "question": r["question"]}
                         for r in gate if r["outcome"] == "FP"],
    }
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps({"summary": summary, "results": results}, indent=1, ensure_ascii=False), encoding="utf-8")

    def line(name, r):
        print(f"{name:<24} cases={r['cases']:>3} risky={r['risky']:>3} harmless={r['harmless']:>3} "
              f"recall={_pct(r['recall'])} false_alarm_rate={_pct(r['false_alarm_rate'])} "
              f"(missed {r['missed']}, false alarms {r['false_alarms']})")

    line("overall", summary["overall"])
    line("main", summary["main"])
    line("messy", summary["messy"])
    line("multilingual", summary["multilingual"])
    for k, v in summary["by_category"].items():
        line("  " + k[:22], v)
    for m in summary["misses"]:
        print("MISS", m["id"], m["tool"], m["args"])
    for m in summary["false_alarms"]:
        print("FALSE ALARM", m["id"], m["tool"], m["note"], "|", m["question"])
    print("refusal checks:", summary["refusal_checks"])
    print("crashes:", errors, "| written:", OUT)
    return 0


def _group(rows, key):
    out = defaultdict(list)
    for r in rows:
        out[r[key]].append(r)
    return out


def _pct(x):
    return "  n/a" if x is None else f"{x * 100:5.1f}%"


if __name__ == "__main__":
    sys.exit(main())
