"""3-arm sweep for issue #79 / paper Table 1.

For each arm (no-llm | opus | gpt) x 15 circuits x 10 seeds, run the schengen
CLI once (SCHENGEN_SEED=s, --num 1), then record per run:
  - the four metrics (from the result JSON)
  - per-stage timing (parsed from run.log's "Timing summary")
  - admitted / generated LLM-constraint counts (from result JSON `constraint_llm`)
  - failure reason when no result JSON is produced (parsed from run.log)

Parallelism is pinned (--conc, default 8) and recorded; each run is a single
CP-SAT worker (SCHENGEN_SEED pins num_search_workers=1), so on a many-core box
the runs do not oversubscribe and per-run timing stays close to solo.

Results are merged into examples/sweep_3arm.json (existing arms preserved), so
arms can be run in separate invocations. Big result JSONs are deleted after
parsing; run.log is kept (gitignored via *.log).

Usage:
  uv run python scripts/run_sweep_3arm.py --arms no-llm,opus [--conc 8]
"""
import argparse
import json
import os
import platform
import re
import shutil
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SWEEP = REPO / "sweep"
OUT_JSON = REPO / "examples" / "sweep_3arm.json"
SEEDS = list(range(1, 11))
EXAMPLES = list(range(1, 16))
ARM_CF = {
    "no-llm": "opus_4.8_constraint_no-llm.json",
    "opus": "opus_4.8_constraint.json",
    "gpt": "gpt_5.4_constraint.json",
}
TIMING_KEYS = ("placement:constraint_admission", "placement:final_solve",
               "routing:redraw_components", "routing:astar",
               "routing:rescale_and_intersections", "routing:total", "total")
# Timing lines are emitted through loguru, so each carries a "<ts> | INFO | ... - "
# prefix; match the "<stage>: <float>" at the end of the line instead of anchoring.
TIMING_RE = re.compile(r"([\w:]+):\s+([0-9]+\.[0-9]+)\s*$")
STATUS_RE = re.compile(r"Solver status:\s*(\w+)")
SAT_RE = re.compile(r"LLM constraints satisfied in final placement:\s*(\d+)/(\d+)")


def parse_timing(text):
    t = {}
    for line in text.splitlines():
        m = TIMING_RE.search(line)
        if m and m.group(1) in TIMING_KEYS:
            t[m.group(1)] = float(m.group(2))
    return t


def _traceback_tail(text, n=18):
    lines = text.splitlines()
    for idx in range(len(lines) - 1, -1, -1):
        if "Traceback (most recent call last)" in lines[idx]:
            return "\n".join(lines[idx:idx + 40][-n:])
    return None


def classify_failure(text):
    statuses = STATUS_RE.findall(text)
    if "Failed to find a valid component placement" in text:
        last = statuses[-1] if statuses else None
        if last == "INFEASIBLE":
            return "cpsat_infeasible", None
        if last in ("UNKNOWN", "MODEL_INVALID"):
            return "cpsat_budget", None
        return f"placement_failed({last})", None
    if "Traceback (most recent call last)" in text:
        tb = _traceback_tail(text)
        exc = [ln for ln in text.splitlines() if ln.strip()][-1][:200]
        return f"exception: {exc}", tb
    if "Unrouted net" in text:
        return "router_unrouted", None
    return "unknown", None


def run_one(arm, i, seed):
    cf = ARM_CF[arm]
    outdir = SWEEP / arm / f"example-{i}" / f"seed-{seed}"
    if outdir.exists():
        shutil.rmtree(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, SCHENGEN_SEED=str(seed))
    logpath = outdir / "run.log"
    t0 = time.perf_counter()
    with open(logpath, "w") as lf:
        try:
            subprocess.run(
                ["uv", "run", "python", "-m", "src.cli", "--num", "1",
                 "--ckt", str(REPO / f"examples/example-{i}/netlist.ckt"),
                 "--constraint-file", str(REPO / f"examples/example-{i}/{cf}"),
                 "--output_dir", str(outdir)],
                cwd=REPO, env=env, stdout=lf, stderr=subprocess.STDOUT, timeout=900,
            )
        except subprocess.TimeoutExpired:
            lf.write("\n[harness] TIMEOUT after 900s\n")
    wall = round(time.perf_counter() - t0, 2)
    text = logpath.read_text(errors="replace")
    timing = parse_timing(text)
    res = next((f for f in outdir.iterdir()
                if f.name.startswith("schematic_result_") and f.suffix == ".json"), None)
    rec = {"seed": seed, "wall_external": wall, "timing": timing}
    if res is not None:
        d = json.loads(res.read_text())
        cl = d.get("constraint_llm", [])
        sat = SAT_RE.findall(text)
        rec.update(
            ok=True,
            routing_cost=d["routing_cost"], bends=d["num_bends"],
            crossings=d["num_crossings"], hpwl=d["hpwl_cost"],
            llm_admitted=sum(1 for c in cl if c[1]), llm_total=len(cl),
            llm_satisfied=(int(sat[-1][0]) if sat else None),
            unrouted=len(d.get("unrouted_nets", [])),
        )
        res.unlink()  # drop the ~700KB artifact; metrics are captured
    else:
        failure, tb = classify_failure(text)
        rec.update(ok=False, failure=failure)
        if tb:
            rec["traceback_tail"] = tb
    return arm, i, rec


def machine_info():
    model = "?"
    try:
        for ln in Path("/proc/cpuinfo").read_text().splitlines():
            if ln.startswith("model name"):
                model = ln.split(":", 1)[1].strip()
                break
    except Exception:
        pass
    mem_gb = None
    try:
        for ln in Path("/proc/meminfo").read_text().splitlines():
            if ln.startswith("MemTotal"):
                mem_gb = round(int(ln.split()[1]) / 1_048_576)
                break
    except Exception:
        pass
    return {"cpu": model, "cores": os.cpu_count(), "ram_gb": mem_gb,
            "platform": platform.platform()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arms", default="no-llm,opus")
    ap.add_argument("--conc", type=int, default=8)
    args = ap.parse_args()
    arms = args.arms.split(",")

    results = {}
    if OUT_JSON.exists():
        results = json.loads(OUT_JSON.read_text())
    meta = results.get("_meta", {})
    meta.update(machine_info())
    meta["concurrency"] = args.conc
    meta["seeds"] = SEEDS
    meta["solver_time_limit_s"] = 10
    meta["note"] = ("SCHENGEN_SEED pins num_search_workers=1; placement time limit "
                    "is wall-clock 10s. Timing measured under the recorded concurrency.")
    results["_meta"] = meta
    for i in EXAMPLES:
        results.setdefault(str(i), {})
        for arm in arms:
            results[str(i)][arm] = []

    jobs = [(arm, i, s) for arm in arms for i in EXAMPLES for s in SEEDS]
    done = 0
    with ThreadPoolExecutor(max_workers=args.conc) as pool:
        futs = [pool.submit(run_one, *j) for j in jobs]
        for fut in as_completed(futs):
            arm, i, rec = fut.result()
            results[str(i)][arm].append(rec)
            done += 1
            status = "ok" if rec.get("ok") else f"FAIL:{rec.get('failure')}"
            print(f"[{done}/{len(jobs)}] {arm} ex{i} seed{rec['seed']} "
                  f"{status} t={rec['timing'].get('total','?')}", flush=True)
            if done % 15 == 0:
                OUT_JSON.write_text(json.dumps(results, indent=2))

    for arm in arms:
        for i in EXAMPLES:
            results[str(i)][arm].sort(key=lambda r: r["seed"])
    OUT_JSON.write_text(json.dumps(results, indent=2))
    print("DONE ->", OUT_JSON, flush=True)


if __name__ == "__main__":
    main()
