"""Aggregate examples/sweep_3arm.json into the deliverables issue #79 asks for
and print a Markdown report (paste into the issue).

Sum basis follows ADR-0005 / #76: sum of per-circuit means, std propagated in
quadrature. Metric means use only successful runs; N is reported so the reader
can see survivorship (the no-llm arm crashes on many seeds, so its metrics are
measured only on the placements that did not overflow the grid).
"""
import json
import math
import statistics
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
d = json.load(open(REPO / "examples/sweep_3arm.json"))
DEV = {1: 26, 2: 30, 3: 48, 4: 20, 5: 14, 6: 36, 7: 19, 8: 17,
       9: 19, 10: 44, 11: 25, 12: 27, 13: 18, 14: 35, 15: 24}
ARMS = [a for a in ("no-llm", "opus", "gpt") if any(a in d[str(i)] and d[str(i)][a] for i in range(1, 16))]
METRICS = ("crossings", "bends", "hpwl", "routing_cost")


def ok_runs(i, arm):
    return [r for r in d[str(i)].get(arm, []) if r.get("ok")]


def mean_std(vals):
    if not vals:
        return None, None
    return statistics.mean(vals), (statistics.pstdev(vals) if len(vals) > 1 else 0.0)


print(f"## Machine\n\n`{d['_meta']['cpu']}` — {d['_meta']['cores']} threads, "
      f"{d['_meta']['ram_gb']} GB, {d['_meta']['platform']}. "
      f"Concurrency {d['_meta']['concurrency']}, seeds {d['_meta']['seeds'][0]}–{d['_meta']['seeds'][-1]}, "
      f"placement solve limit {d['_meta']['solver_time_limit_s']}s (wall).\n")

# --- success rate + failure reasons ---
print("## Success rate & failure reasons\n")
print("| Arm | Success (runs) | Failures | Breakdown |")
print("| --- | ---: | ---: | --- |")
for arm in ARMS:
    ok = fail = 0
    kinds = {}
    for i in range(1, 16):
        for r in d[str(i)].get(arm, []):
            if r.get("ok"):
                ok += 1
            else:
                fail += 1
                k = r["failure"].split(":")[0].strip()
                kinds[k] = kinds.get(k, 0) + 1
    kd = ", ".join(f"{k}×{v}" for k, v in sorted(kinds.items(), key=lambda x: -x[1])) or "—"
    print(f"| {arm} | {ok}/{ok+fail} ({100*ok/(ok+fail):.0f}%) | {fail} | {kd} |")

print("\n### Per-circuit success rate (ok / 10 seeds)\n")
print("| Ex | Dev | " + " | ".join(ARMS) + " |")
print("| --- | ---: | " + " | ".join("---:" for _ in ARMS) + " |")
for i in range(1, 16):
    row = [f"example-{i}", str(DEV[i])]
    for arm in ARMS:
        n = len(ok_runs(i, arm))
        row.append(f"{n}/10")
    print("| " + " | ".join(row) + " |")

# --- aggregate metric sums (sum of per-circuit means, std in quadrature) ---
print("\n## Aggregate metrics (sum of per-circuit means ± std in quadrature)\n")
print("| Metric | " + " | ".join(ARMS) + " |")
print("| --- | " + " | ".join("---:" for _ in ARMS) + " |")
sums = {arm: {} for arm in ARMS}
for mkey in METRICS:
    cells = []
    for arm in ARMS:
        s = 0.0
        var = 0.0
        for i in range(1, 16):
            vals = [r[mkey] for r in ok_runs(i, arm)]
            m, sd = mean_std(vals)
            if m is not None:
                s += m
                var += sd * sd
        sums[arm][mkey] = (s, math.sqrt(var))
        cells.append(f"{s:.0f}±{math.sqrt(var):.0f}")
    print(f"| {mkey} | " + " | ".join(cells) + " |")
# deltas vs no-llm
if "no-llm" in ARMS:
    print("\nReduction vs `no-llm` (sum of means):\n")
    for arm in ARMS:
        if arm == "no-llm":
            continue
        parts = []
        for mkey in METRICS:
            base = sums["no-llm"][mkey][0]
            v = sums[arm][mkey][0]
            parts.append(f"{mkey} {100*(base-v)/base:+.0f}%")
        print(f"- **{arm}**: " + ", ".join(parts))

# --- timing ---
print("\n## Runtime (median seconds per circuit, successful runs)\n")
print("| Ex | Dev | " + " | ".join(f"{a} total" for a in ARMS) + " | " +
      " | ".join(f"{a} place/route" for a in ARMS) + " |")
print("| --- | ---: | " + " | ".join("---:" for _ in ARMS) + " | " + " | ".join("---:" for _ in ARMS) + " |")
med_tot = {arm: [] for arm in ARMS}
for i in range(1, 16):
    tots, splits = [], []
    for arm in ARMS:
        runs = ok_runs(i, arm)
        t = [r["timing"].get("total") for r in runs if r["timing"].get("total")]
        pl = [r["timing"].get("placement:constraint_admission", 0) + r["timing"].get("placement:final_solve", 0)
              for r in runs if r["timing"]]
        ro = [r["timing"].get("routing:total", 0) for r in runs if r["timing"]]
        tots.append(f"{statistics.median(t):.1f}" if t else "—")
        splits.append(f"{statistics.median(pl):.1f}/{statistics.median(ro):.1f}" if pl else "—")
        if t:
            med_tot[arm].append(statistics.median(t))
    print(f"| example-{i} | {DEV[i]} | " + " | ".join(tots) + " | " + " | ".join(splits) + " |")

# --- admission ---
print("\n## LLM-constraint admission (mean admitted / generated over successful runs)\n")
print("| Ex | " + " | ".join(a for a in ARMS if a != "no-llm") + " |")
print("| --- | " + " | ".join("---:" for a in ARMS if a != "no-llm") + " |")
adm_tot = {a: [0, 0] for a in ARMS if a != "no-llm"}
for i in range(1, 16):
    cells = []
    for arm in ARMS:
        if arm == "no-llm":
            continue
        runs = ok_runs(i, arm)
        adm = [r["llm_admitted"] for r in runs if r.get("llm_admitted") is not None]
        tot = [r["llm_total"] for r in runs if r.get("llm_total") is not None]
        if adm:
            cells.append(f"{statistics.mean(adm):.0f}/{statistics.mean(tot):.0f} ({100*statistics.mean(adm)/statistics.mean(tot):.0f}%)")
            adm_tot[arm][0] += statistics.mean(adm)
            adm_tot[arm][1] += statistics.mean(tot)
        else:
            cells.append("—")
    print(f"| example-{i} | " + " | ".join(cells) + " |")
print("\nOverall admitted fraction: " + ", ".join(
    f"**{a}** {100*adm_tot[a][0]/adm_tot[a][1]:.0f}% ({adm_tot[a][0]:.0f}/{adm_tot[a][1]:.0f})"
    for a in adm_tot))

# --- per-circuit crossings means (size-conditioned) ---
print("\n## Per-circuit mean crossings (size-conditioned)\n")
print("| Ex | Dev | " + " | ".join(ARMS) + " |")
print("| --- | ---: | " + " | ".join("---:" for _ in ARMS) + " |")
for i in sorted(range(1, 16), key=lambda x: DEV[x]):
    row = [f"example-{i}", str(DEV[i])]
    for arm in ARMS:
        m, sd = mean_std([r["crossings"] for r in ok_runs(i, arm)])
        row.append(f"{m:.1f}±{sd:.1f}" if m is not None else "—")
    print("| " + " | ".join(row) + " |")

print("\n### Median total wall (algorithm) per arm: " +
      ", ".join(f"{a} {statistics.median(med_tot[a]):.1f}s" for a in ARMS if med_tot[a]))
