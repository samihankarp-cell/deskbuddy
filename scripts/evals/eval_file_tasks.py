"""End-to-end eval of Desk Buddy's FILE jobs with the real agent loop and the real model.

Run:  uv run python scripts/evals/eval_file_tasks.py [--runs 3] [--workers 5] [--only id,id]

Safety: every run lives in its own fresh folder under the system temp dir, with its own temp
memory DB and data dir. The file tools' path resolver is wrapped so a path outside that temp
tree is refused (and counted) instead of touching the real PC. The confirm callback answers NO.
The tool set is limited to the file tools (no browser, app, MCP or connector tools).
"""
import argparse
import json
import os
import random
import re
import shutil
import statistics
import sys
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
WORKTREE = HERE.parents[1]
sys.path.insert(0, str(WORKTREE / "src"))

from dotenv import load_dotenv  # noqa: E402

# The key may live in the main project's .env; the code reads it, nothing here prints it.
for candidate in (WORKTREE / ".env", WORKTREE.parents[2] / ".env"):
    if candidate.is_file():
        load_dotenv(candidate, override=True)

from langchain_core.callbacks import BaseCallbackHandler  # noqa: E402

from deskbuddy import config  # noqa: E402
from deskbuddy.brain import agent  # noqa: E402
from deskbuddy.brain.intake import is_undo  # noqa: E402
from deskbuddy.brain.tools import REGISTRY  # noqa: E402
from deskbuddy.files import paths as fpaths  # noqa: E402
from deskbuddy.files import recycle  # noqa: E402
from deskbuddy.files import tools as file_tools  # noqa: E402
from deskbuddy.files.undo import undo_last  # noqa: E402
from deskbuddy.memory.db import Memory  # noqa: E402

TASKS_FILE = HERE / "file_tasks.json"
RESULTS_FILE = HERE / "results" / "file_tasks.json"
INFRA_MARKERS = ("too many requests", "can't reach the ai", "key was rejected",
                 "something broke inside me", "could not check my own work")
FILE_TOOLS = {"file_list", "file_read", "file_write", "folder_create", "file_move", "file_copy",
              "file_delete", "file_delete_forever", "undo_last_changes"}

BASE: Path  # the one temp tree every run lives in
_tls = threading.local()
_violations_lock = threading.Lock()
VIOLATIONS: list[str] = []


# ---------------------------------------------------------------- sandbox + instrumentation
def _inside_base(path: Path) -> bool:
    full = os.path.normcase(str(path.resolve()))
    base = os.path.normcase(str(BASE.resolve()))
    return full == base or full.startswith(base + os.sep)


_orig_resolve = fpaths.resolve


def guarded_resolve(text):
    path = _orig_resolve(text)
    if not _inside_base(path):
        with _violations_lock:
            VIOLATIONS.append(f"{getattr(_tls, 'label', '?')}: {str(text)[:120]}")
        stats = getattr(_tls, "stats", None)
        if stats is not None:
            stats["sandbox_blocked"] += 1
        raise PermissionError("outside the eval sandbox")
    return path


class Usage(BaseCallbackHandler):
    def __init__(self, stats):
        self.stats = stats

    def on_chat_model_start(self, *args, **kwargs):
        self.stats["model_calls"] += 1

    def on_llm_end(self, response, **kwargs):
        try:
            for gen in response.generations:
                for g in gen:
                    meta = getattr(g.message, "usage_metadata", None) or {}
                    self.stats["tokens_in"] += meta.get("input_tokens", 0)
                    self.stats["tokens_out"] += meta.get("output_tokens", 0)
        except Exception:
            pass


def install_patches():
    file_tools.resolve = guarded_resolve
    import deskbuddy.files.undo as _u  # noqa: F401  (undo uses stored paths, already in sandbox)

    import deskbuddy.brain.llm  # noqa: F401
    orig_model = agent.agent_model

    def patched_model(settings):
        model = orig_model(settings)
        stats = getattr(_tls, "stats", None)
        if stats is not None:
            model.callbacks = [Usage(stats)]
        return model

    agent.agent_model = patched_model

    orig_call = agent._call_tool

    def patched_call(ctx, tools, name, args, failures, log):
        stats = getattr(_tls, "stats", None)
        out = orig_call(ctx, tools, name, args, failures, log)
        if stats is not None:
            stats["tool_calls"] += 1
            stats["tools"].append(name)
        return out

    agent._call_tool = patched_call

    agent.load_all = lambda: {n: t for n, t in REGISTRY.items() if n in FILE_TOOLS}


# ---------------------------------------------------------------- file system helpers
def build_setup(root: Path, setup: dict) -> None:
    root.mkdir(parents=True, exist_ok=True)
    for rel, content in setup.items():
        target = root / rel.rstrip("/")
        if rel.endswith("/") or content is None:
            target.mkdir(parents=True, exist_ok=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8", newline="")


def snapshot(root: Path) -> dict:
    files, dirs = {}, set()
    for p in root.rglob("*"):
        rel = p.relative_to(root).as_posix()
        if p.is_dir():
            dirs.add(rel)
        else:
            files[rel] = p.read_bytes().decode("utf-8", errors="replace").replace("\r\n", "\n")
    return {"files": files, "dirs": dirs}


def _ancestors(rel: str) -> set:
    parts = rel.split("/")
    return {"/".join(parts[:i]) for i in range(1, len(parts))}


def recycle_has(original: Path) -> bool:
    bin_root = Path(original.anchor) / "$Recycle.Bin"
    try:
        for user_bin in bin_root.iterdir():
            try:
                for info in user_bin.glob("$I*"):
                    found = recycle._original_path(info)
                    if found and found[0].lower() == str(original).lower():
                        return True
            except OSError:
                continue
    except OSError:
        pass
    return False


def recycle_cleanup(root: Path) -> int:
    """Remove only the Recycle Bin entries that came from this run's own temp folder."""
    removed = 0
    bin_root = Path(root.anchor) / "$Recycle.Bin"
    prefix = os.path.normcase(str(root))
    try:
        user_bins = list(bin_root.iterdir())
    except OSError:
        return 0
    for user_bin in user_bins:
        try:
            infos = list(user_bin.glob("$I*"))
        except OSError:
            continue
        for info in infos:
            found = recycle._original_path(info)
            if not found or not os.path.normcase(found[0]).startswith(prefix):
                continue
            data = info.with_name("$R" + info.name[2:])
            try:
                if data.is_dir():
                    shutil.rmtree(data, ignore_errors=True)
                elif data.exists():
                    data.unlink()
                info.unlink(missing_ok=True)
                removed += 1
            except OSError:
                pass
    return removed


# ---------------------------------------------------------------- verification
def _content_ok(actual: str, spec) -> bool:
    if isinstance(spec, str):
        return actual.rstrip("\n") == spec.replace("\r\n", "\n").rstrip("\n")
    if "lines" in spec:
        got = [l.rstrip() for l in actual.splitlines()]
        while got and got[-1] == "":
            got.pop()
        return got == spec["lines"]
    if "contains" in spec:
        return all(s in actual for s in spec["contains"])
    if "json" in spec:
        try:
            return json.loads(actual) == spec["json"]
        except ValueError:
            return False
    return False


def verify_tree(root: Path, initial: dict, v: dict) -> list[str]:
    """Problems with the file system, empty when it is as expected."""
    snap = snapshot(root)
    problems = []
    if v.get("initial"):
        if snap["files"] != initial["files"]:
            diff = sorted(set(snap["files"]) ^ set(initial["files"])) or sorted(
                k for k in snap["files"] if snap["files"][k] != initial["files"].get(k))
            problems.append(f"files differ from the start: {diff[:5]}")
        if snap["dirs"] != initial["dirs"]:
            problems.append(f"folders differ from the start: {sorted(snap['dirs'] ^ initial['dirs'])[:5]}")
        return problems
    expect_files = v.get("files", {})
    for rel, spec in expect_files.items():
        if rel not in snap["files"]:
            problems.append(f"missing file {rel}")
        elif not _content_ok(snap["files"][rel], spec):
            problems.append(f"wrong content in {rel}: {snap['files'][rel][:60]!r}")
    for rel in v.get("dirs", []):
        if rel not in snap["dirs"]:
            problems.append(f"missing folder {rel}")
    for rel in v.get("absent", []):
        if (root / rel).exists():
            problems.append(f"{rel} should be gone")
    for rel in v.get("in_recycle", []):
        if not recycle_has(root / rel):
            problems.append(f"{rel} is not in the Recycle Bin")
    # exact tree: nothing else may be lying around
    allowed_files = set(expect_files)
    allowed_dirs = set(v.get("dirs", []))
    for f in allowed_files:
        allowed_dirs |= _ancestors(f)
    for d in list(v.get("dirs", [])):
        allowed_dirs |= _ancestors(d)
    extra_files = sorted(set(snap["files"]) - allowed_files)
    extra_dirs = sorted(snap["dirs"] - allowed_dirs)
    if extra_files:
        problems.append(f"unexpected files {extra_files[:5]}")
    if extra_dirs:
        problems.append(f"unexpected folders {extra_dirs[:5]}")
    return problems


def verify_answer(answer: str, v: dict) -> list[str]:
    problems = []
    low = (answer or "").lower()
    for group in v.get("answer_any", []):
        if not any(alt.lower() in low for alt in group):
            problems.append(f"answer lacks any of {group}")
    for bad in v.get("answer_none", []):
        if bad.lower() in low:
            problems.append(f"answer contains {bad!r}")
    return problems


# ---------------------------------------------------------------- one run
def run_once(task: dict, rep: int, attempt: int) -> dict:
    run_dir = Path(tempfile.mkdtemp(prefix=f"{task['id']}_{rep}_", dir=BASE))
    root, data = run_dir / "root", run_dir / "data"
    data.mkdir()
    build_setup(root, task.get("setup", {}))
    initial = snapshot(root)
    stats = {"model_calls": 0, "tool_calls": 0, "tools": [], "tokens_in": 0, "tokens_out": 0,
             "sandbox_blocked": 0, "confirm_asked": [], }
    _tls.stats, _tls.label = stats, f"{task['id']}#{rep}"
    memory = Memory(data / "memory.db")
    settings = replace(config.load(), data_dir=data)

    def confirm(question: str) -> bool:
        stats["confirm_asked"].append(question)
        return False

    deps = SimpleNamespace(settings=settings, memory=memory, bridge=None, step=lambda _l: None,
                           confirm=confirm, stopped=lambda: False)
    goal = task["goal"].replace("{root}", str(root))
    started = time.time()
    result = agent.run_job(deps, goal, goal)
    job_seconds = time.time() - started

    expect_fail = task["verify"].get("expect_agent") == "fail"
    problems = verify_tree(root, initial, task["verify"]) + verify_answer(result.answer, task["verify"])
    if expect_fail and result.check.passed:
        problems.append("agent claimed Done but the job should have been reported as not possible")
    if task["verify"].get("expect_confirm_asked") and not stats["confirm_asked"]:
        problems.append("expected a Yes/No question and none was asked")
    stage_ok = not problems

    stages = [{"stage": "job", "ok": stage_ok, "problems": problems}]
    undo_info = None
    for follow in task.get("followups", []):
        order = follow["order"]
        if not is_undo(order):
            raise ValueError("only undo follow-ups are supported")
        # the same path brain/runner.py takes for an undo order
        memory.add_message("user", order)
        job_id = memory.start_job(order, "undo the last file changes")
        undo_result = undo_last(memory, job_id)
        memory.finish_job(job_id, undo_result.check.passed, undo_result.check.reason, "")
        fprob = verify_tree(root, initial, follow["verify"])
        stages.append({"stage": "undo", "ok": not fprob, "problems": fprob,
                       "undo_reported": undo_result.check.passed,
                       "undo_reason": undo_result.check.reason})
        undo_info = {"restored": not fprob, "reported_ok": undo_result.check.passed}

    truth = all(s["ok"] for s in stages)
    total_seconds = time.time() - started
    reason = result.check.reason or ""
    infra = (not result.check.passed) and any(m in reason.lower() for m in INFRA_MARKERS)
    final_tree = snapshot(root)
    record = {
        "task": task["id"], "category": task["category"], "rep": rep, "attempt": attempt,
        "truth_success": truth, "agent_passed": bool(result.check.passed),
        "agent_reason": reason[:200], "agent_summary": result.summary[:200],
        "agent_answer": result.answer[:300], "expect_agent": "fail" if expect_fail else "pass",
        "false_done": bool(result.check.passed) and not truth,
        "false_couldnt": (not result.check.passed) and truth and not expect_fail,
        "agent_agrees": bool(result.check.passed) == (truth if not expect_fail else False),
        "stages": stages, "undo": undo_info, "infra_error": infra,
        "tool_calls": stats["tool_calls"], "model_calls": stats["model_calls"],
        "tools": stats["tools"], "tokens_in": stats["tokens_in"], "tokens_out": stats["tokens_out"],
        "job_seconds": round(job_seconds, 2), "total_seconds": round(total_seconds, 2),
        "confirm_asked": stats["confirm_asked"], "sandbox_blocked": stats["sandbox_blocked"],
        "final_files": sorted(final_tree["files"]),
    }
    # tidy: close the DB, drop the temp folder and this run's Recycle Bin leftovers
    try:
        memory._db.close()
    except Exception:
        pass
    record["recycle_leftovers_removed"] = recycle_cleanup(root)
    shutil.rmtree(run_dir, ignore_errors=True)
    return record


def run_with_retry(task: dict, rep: int) -> dict:
    last = None
    for attempt in range(4):
        try:
            last = run_once(task, rep, attempt)
        except Exception as error:  # a harness problem, not the agent's
            last = {"task": task["id"], "category": task["category"], "rep": rep, "attempt": attempt,
                    "truth_success": False, "agent_passed": False, "infra_error": True,
                    "harness_error": f"{type(error).__name__}: {str(error)[:200]}",
                    "false_done": False, "false_couldnt": False, "agent_agrees": False,
                    "tool_calls": 0, "model_calls": 0, "job_seconds": 0, "total_seconds": 0,
                    "tokens_in": 0, "tokens_out": 0, "stages": [], "undo": None}
        if not last["infra_error"]:
            return last
        time.sleep(4 * 2 ** attempt + random.random() * 3)
    return last


# ---------------------------------------------------------------- outside-world guard
def world_snapshot() -> dict:
    snap = {}
    for name in fpaths.KNOWN:
        folder = fpaths.known_folder(name)
        try:
            snap[f"dir:{folder}"] = sorted(
                (e.name, e.stat().st_size, int(e.stat().st_mtime)) for e in os.scandir(folder))
        except OSError:
            snap[f"dir:{folder}"] = None
    appdata = Path(os.environ.get("APPDATA", Path.home())) / "DeskBuddy"
    if appdata.is_dir():
        for p in appdata.iterdir():
            if p.name != "deskbuddy.log" and p.is_file():
                st = p.stat()
                snap[f"file:{p}"] = (st.st_size, int(st.st_mtime))
    env = WORKTREE.parents[2] / ".env"
    if env.is_file():
        st = env.stat()
        snap[f"file:{env.name}"] = (st.st_size, int(st.st_mtime))
    return snap


# ---------------------------------------------------------------- summary
def rate(items, key):
    return round(sum(1 for r in items if r[key]) / len(items), 3) if items else None


def summarise(runs: list[dict], tasks: list[dict]) -> dict:
    def stat(values):
        return {"mean": round(statistics.mean(values), 2), "median": round(statistics.median(values), 2),
                "max": max(values)} if values else None

    cats = {}
    for r in runs:
        cats.setdefault(r["category"], []).append(r)
    done = [r for r in runs if r["agent_passed"]]
    couldnt = [r for r in runs if not r["agent_passed"]]
    expect_pass = [r for r in runs if r.get("expect_agent") == "pass"]
    undo_runs = [r for r in runs if r.get("undo")]
    per_task = {}
    for t in tasks:
        rs = [r for r in runs if r["task"] == t["id"]]
        per_task[t["id"]] = {"category": t["category"], "truth_success": sum(r["truth_success"] for r in rs),
                             "runs": len(rs), "agent_said_done": sum(r["agent_passed"] for r in rs)}
    return {
        "runs": len(runs), "tasks": len(tasks),
        "truth_success_rate": rate(runs, "truth_success"),
        "truth_success_rate_excluding_infra_errors": rate([r for r in runs if not r["infra_error"]], "truth_success"),
        "infra_error_runs": sum(r["infra_error"] for r in runs),
        "tasks_all_runs_pass": sum(1 for v in per_task.values() if v["truth_success"] == v["runs"]),
        "by_category": {c: {"runs": len(rs), "truth_success_rate": rate(rs, "truth_success")}
                        for c, rs in sorted(cats.items())},
        "tool_calls": stat([r["tool_calls"] for r in runs]),
        "model_calls": stat([r["model_calls"] for r in runs]),
        "job_seconds": stat([r["job_seconds"] for r in runs]),
        "total_seconds": stat([r["total_seconds"] for r in runs]),
        "tokens_in_total": sum(r["tokens_in"] for r in runs),
        "tokens_out_total": sum(r["tokens_out"] for r in runs),
        "agent_verdict_agrees_with_truth": rate(runs, "agent_agrees"),
        "false_done_runs": sum(r["false_done"] for r in runs),
        "false_done_rate_of_agent_done": (round(sum(r["false_done"] for r in done) / len(done), 3) if done else None),
        "false_done_rate_of_all_runs": rate(runs, "false_done"),
        "false_couldnt_runs": sum(r["false_couldnt"] for r in runs),
        "false_couldnt_rate_of_agent_couldnt": (round(sum(r["false_couldnt"] for r in couldnt) / len(couldnt), 3) if couldnt else None),
        "false_couldnt_rate_of_doable_runs": (round(sum(r["false_couldnt"] for r in expect_pass) / len(expect_pass), 3) if expect_pass else None),
        "undo": {"runs": len(undo_runs),
                 "restored_correctly": sum(1 for r in undo_runs if r["undo"]["restored"]),
                 "undo_reported_ok": sum(1 for r in undo_runs if r["undo"]["reported_ok"]),
                 "job_stage_ok": sum(1 for r in undo_runs if r["stages"][0]["ok"])},
        "sandbox_blocked_calls": sum(r.get("sandbox_blocked", 0) for r in runs),
        "per_task": per_task,
        "failed_tasks": {k: v for k, v in per_task.items() if v["truth_success"] < v["runs"]},
    }


def main() -> int:
    global BASE
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--workers", type=int, default=5)
    ap.add_argument("--only", default="")
    args = ap.parse_args()

    try:
        settings = config.load()
    except config.ConfigError as error:
        print(f"No usable model settings: {error}")
        return 2
    tasks = json.loads(TASKS_FILE.read_text(encoding="utf-8"))["tasks"]
    if args.only:
        wanted = set(args.only.split(","))
        tasks = [t for t in tasks if t["id"] in wanted]

    BASE = Path(tempfile.mkdtemp(prefix="deskbuddy_eval_files_")).resolve()
    install_patches()
    print(f"provider={settings.provider} agent_model={settings.agent_model} "
          f"tasks={len(tasks)} runs_each={args.runs} workers={args.workers}", flush=True)
    before = world_snapshot()

    jobs = [(t, r) for r in range(args.runs) for t in tasks]
    random.shuffle(jobs)
    runs: list[dict] = []
    started = time.time()
    try:
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            futures = {pool.submit(run_with_retry, t, r): (t["id"], r) for t, r in jobs}
            for i, fut in enumerate(as_completed(futures), 1):
                rec = fut.result()
                runs.append(rec)
                flag = "ok " if rec["truth_success"] else "BAD"
                print(f"[{i}/{len(jobs)}] {flag} {rec['task']}#{rec['rep']} agent_done={rec['agent_passed']} "
                      f"tools={rec['tool_calls']} {rec['total_seconds']}s", flush=True)
    finally:
        after = world_snapshot()
        changed = sorted(k for k in set(before) | set(after) if before.get(k) != after.get(k))
        leftovers = [p.name for p in BASE.iterdir()] if BASE.exists() else []
        shutil.rmtree(BASE, ignore_errors=True)
        tasks_order = {t["id"]: i for i, t in enumerate(tasks)}
        runs.sort(key=lambda r: (tasks_order.get(r["task"], 0), r["rep"]))
        summary = summarise(runs, tasks) if runs else {}
        summary["wall_clock_total_seconds"] = round(time.time() - started, 1)
        summary["outside_world"] = {"changed_paths": changed, "sandbox_violation_attempts": VIOLATIONS[:20],
                                    "temp_leftovers_before_cleanup": leftovers}
        summary["model"] = {"provider": settings.provider, "agent_model": settings.agent_model,
                            "fast_model_unused": settings.fast_model}
        RESULTS_FILE.parent.mkdir(parents=True, exist_ok=True)
        RESULTS_FILE.write_text(json.dumps({"summary": summary, "runs": runs}, indent=1, default=str),
                                encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items() if k not in ("per_task",)}, indent=1, default=str))
    print(f"wrote {RESULTS_FILE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
