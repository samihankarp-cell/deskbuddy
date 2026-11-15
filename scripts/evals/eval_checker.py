"""Eval: does the checker (_check in brain/agent.py) catch false 'Done' claims and pass true ones?

Run: uv run python scripts/evals/eval_checker.py
Calls the real _check with the real agent model; only _fresh_evidence is replaced by each case's
canned text (no browser). Never prints the key; settings are loaded through deskbuddy.config.
"""
import json
import random
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "src"))

from dotenv import load_dotenv  # noqa: E402

# the worktree has no .env; the main checkout's one is where the key lives (never printed)
for candidate in [ROOT / ".env", *[p / ".env" for p in ROOT.parents[:4]]]:
    if candidate.exists():
        load_dotenv(candidate, override=True)
        break

from deskbuddy import config  # noqa: E402
from deskbuddy.brain import agent  # noqa: E402
from deskbuddy.brain.tools import Ctx  # noqa: E402

RUNS = 3
WORKERS = 6
PRECHECK = "none of the things I tried worked"


def precheck_fires(log) -> bool:
    actions = [e for e in log if not e["reads_only"]]
    return bool(actions) and not any(e["ok"] for e in actions)


def rate(num, den):
    return round(num / den, 4) if den else None


def summarize(cases, runs):
    by = {c["id"]: c for c in cases}
    def stats(ids):
        rs = [r for r in runs if r["id"] in ids and not r["errored"]]
        fails = [r for r in rs if by[r["id"]]["truth"] == "fail"]
        passes = [r for r in rs if by[r["id"]]["truth"] == "pass"]
        correct = sum((not r["passed"]) if by[r["id"]]["truth"] == "fail" else r["passed"] for r in rs)
        base_correct = len(passes)  # trusting the agent = always "pass"
        return {
            "cases": len(ids), "runs_scored": len(rs),
            "false_success_catch_rate": rate(sum(not r["passed"] for r in fails), len(fails)),
            "true_success_pass_rate": rate(sum(r["passed"] for r in passes), len(passes)),
            "accuracy": rate(correct, len(rs)),
            "baseline_trust_agent_accuracy": rate(base_correct, len(rs)),
        }
    out = {"all": stats({c["id"] for c in cases})}
    for cat in sorted({c["category"] for c in cases}):
        out[f"category:{cat}"] = stats({c["id"] for c in cases if c["category"] == cat})
    # per-case consistency: all runs gave the same verdict
    ids = [c["id"] for c in cases]
    verdicts = {i: [r["passed"] for r in runs if r["id"] == i and not r["errored"]] for i in ids}
    consistent = sum(len(set(v)) == 1 for v in verdicts.values() if v)
    out["consistency"] = {"cases_with_identical_verdict_across_runs": consistent, "of": len(ids)}
    out["errored_runs"] = sum(r["errored"] for r in runs)
    wrong = []
    for c in cases:
        rs = [r for r in runs if r["id"] == c["id"] and not r["errored"]]
        bad = [r for r in rs if (r["passed"]) != (c["truth"] == "pass")]
        if bad:
            wrong.append({"id": c["id"], "truth": c["truth"], "category": c["category"],
                          "wrong_runs": f"{len(bad)}/{len(rs)}", "goal": c["goal"],
                          "note": c["note"], "checker_reason": bad[0]["reason"]})
    out["wrong_cases"] = wrong
    return out


def main():
    cases = json.loads((HERE / "checker_cases.json").read_text(encoding="utf-8"))
    try:
        settings = config.load()
    except Exception as error:
        sys.exit(f"no usable settings: {error}")
    print(f"provider={settings.provider} model={settings.agent_model} cases={len(cases)} runs={RUNS}")
    pre = {c["id"]: precheck_fires(c["log"]) for c in cases}
    jobs = [(c, r) for c in cases for r in range(RUNS)]
    with ThreadPoolExecutor(WORKERS) as pool:
        results = list(pool.map(lambda j: run_one_ctx(settings, *j), jobs))
    summary = summarize(cases, results)
    summary["precheck_cases"] = [i for i, v in pre.items() if v]
    summary["precheck_all_false_claims"] = all(c["truth"] == "fail" for c in cases if pre[c["id"]])
    summary["provider"], summary["model"] = settings.provider, settings.agent_model
    out = {"summary": summary, "runs": results,
           "labels": {c["id"]: {"truth": c["truth"], "category": c["category"], "precheck": pre[c["id"]]}
                      for c in cases}}
    (HERE / "results").mkdir(exist_ok=True)
    (HERE / "results" / "checker.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items() if k != "wrong_cases"}, indent=1))
    for w in summary["wrong_cases"]:
        print(w["id"], w["truth"], w["wrong_runs"], "|", w["checker_reason"][:150])


def run_one_ctx(settings, case, run_idx):
    ctx = Ctx(job_id=0, goal=case["goal"], settings=settings, memory=None, bridge=None,
              step=lambda s: None, confirm=lambda s: True, stopped=lambda: False)
    ctx.canned_evidence = case["fresh_evidence"]
    for attempt in range(6):
        res = agent._check(ctx, case["goal"], case["log"], case["summary"], case["answer"], {})
        reason = res.reason or ""
        transient = reason.startswith("I could not check my own work")
        if not transient:
            break
        time.sleep(min(30, 2 ** attempt + random.random()))
    return {"id": case["id"], "run": run_idx, "passed": bool(res.passed), "reason": reason,
            "errored": transient}


# thread-safe replacement for the real _fresh_evidence: reads the canned text off the Ctx
agent._fresh_evidence = lambda ctx: getattr(ctx, "canned_evidence", "(nothing more to look at)")

if __name__ == "__main__":
    main()
