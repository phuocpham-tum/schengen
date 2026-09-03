"""Structure-score sweep: how tightly are recognized subcircuit blocks drawn?

Table 1 captures routing quality; it says nothing about whether the *functional
blocks* a reader looks for are laid out as compact, aligned groups. The result
JSON already carries `structure_score` (src/schengen.py:compute_structure_score),
but run_sweep_3arm.py discards it with the artifact, so this re-runs the arms and
keeps it.

Only the five circuits with subcircuit information (1, 2, 4, 5, 6) are run: the
score is computed over recognized groups, so it is empty for the other ten.

Writes examples/sweep_structure.json. Deliberately a separate script and a
separate output file -- run_sweep_3arm.py rewrites examples/sweep_3arm.json in
place, which is the source of truth for Table 1.

  uv run python scripts/run_structure_sweep.py [--arms no-llm,opus,gpt] [--conc 8]
"""
import argparse
import json
import os
import shutil
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SWEEP = REPO / "sweep-structure"
OUT_JSON = REPO / "examples" / "sweep_structure.json"
SEEDS = list(range(1, 11))
EXAMPLES = [1, 2, 4, 5, 6]  # the circuits with subcircuit information
ARM_CF = {
    "no-llm": "opus_4.8_constraint_no-llm.json",
    "opus": "opus_4.8_constraint.json",
    "gpt": "gpt_5.4_constraint.json",
}


def run_one(arm, i, seed):
    outdir = SWEEP / arm / f"example-{i}" / f"seed-{seed}"
    if outdir.exists():
        shutil.rmtree(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, SCHENGEN_SEED=str(seed))
    logpath = outdir / "run.log"
    with open(logpath, "w") as lf:
        try:
            subprocess.run(
                ["uv", "run", "python", "-m", "src.cli", "--num", "1",
                 "--ckt", str(REPO / f"examples/example-{i}/netlist.ckt"),
                 "--constraint-file", str(REPO / f"examples/example-{i}/{ARM_CF[arm]}"),
                 "--output_dir", str(outdir)],
                cwd=REPO, env=env, stdout=lf, stderr=subprocess.STDOUT, timeout=900,
            )
        except subprocess.TimeoutExpired:
            lf.write("\n[harness] TIMEOUT after 900s\n")
    res = next((f for f in outdir.iterdir()
                if f.name.startswith("schematic_result_") and f.suffix == ".json"), None)
    rec = {"seed": seed}
    if res is None:
        rec["ok"] = False
        return arm, i, rec
    d = json.loads(res.read_text())
    rec.update(
        ok=True,
        structure_score=d.get("structure_score"),
        subcircuit_accepted=len(d.get("constraint_subcircuit_accepted") or {}),
        subcircuit_total=len(d.get("constraint_subcircuit") or {}),
        crossings=d["num_crossings"], bends=d["num_bends"], hpwl=d["hpwl_cost"],
    )
    res.unlink()  # drop the ~700KB artifact; the score is captured
    return arm, i, rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arms", default="no-llm,opus,gpt")
    ap.add_argument("--conc", type=int, default=8)
    args = ap.parse_args()
    arms = args.arms.split(",")

    results = {str(i): {arm: [] for arm in arms} for i in EXAMPLES}
    jobs = [(arm, i, s) for arm in arms for i in EXAMPLES for s in SEEDS]
    done = 0
    t0 = time.perf_counter()
    with ThreadPoolExecutor(max_workers=args.conc) as pool:
        futs = [pool.submit(run_one, *j) for j in jobs]
        for fut in as_completed(futs):
            arm, i, rec = fut.result()
            results[str(i)][arm].append(rec)
            done += 1
            ss = (rec.get("structure_score") or {})
            print(f"[{done}/{len(jobs)}] {arm} ex{i} seed{rec['seed']} "
                  f"ok={rec.get('ok')} spread={ss.get('total_spread')} "
                  f"aligned={ss.get('aligned_groups')}/{ss.get('num_groups')}", flush=True)
            if done % 15 == 0:
                OUT_JSON.write_text(json.dumps(results, indent=2))

    for arm in arms:
        for i in EXAMPLES:
            results[str(i)][arm].sort(key=lambda r: r["seed"])
    OUT_JSON.write_text(json.dumps(results, indent=2))
    print(f"DONE -> {OUT_JSON} in {time.perf_counter()-t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
