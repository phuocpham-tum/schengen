This directory contains (generated schematic) results from schengen for different configurations
of the same circuit (`netlist.ckt`, 30 MOSFETs). Each config crosses two switches — whether
matched-device **subcircuit** info is supplied, and whether **LLM**-generated placement constraints
are supplied:

| Directory | Constraint Setting File | #Bends | #Crossings | HPWL | Aligned groups | Group spread | Groups kept | De-conflict action |
| ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- |
| `results/subcircuit_no-llm` | `constraint-subcircuit_no-llm.json` | 33 | 11 | 153 | 9/11 | 78 | 11/11 | none (no LLM to conflict) |
| `results/subcircuit_with-llm` | `constraint-subcircuit_with-llm.json` | 29 | 4 | 201 | 9/11 | 65 | 9/11 | dropped `MosfetSimpleCurrentMirror[2]` and `[4]` |
| `results/no-subcircuit_no-llm` | `constraint-no-subcircuit_no-llm.json` | 34 | 8 | 140 | – | – | – | – |
| `results/no-subcircuit_with-llm` | `constraint-no-subcircuit_with-llm.json` | 44 | 10 | 186 | – | – | – | – |

Each result directory holds 10 runs (`schematic_result_<idx>_<routing_cost>_<bends>_<crossings>_<hpwl>.json`
plus a matching `.png`). The row above reports the **lowest-`routing_cost`** run per config; the
placement/routing pipeline is not fully deterministic, so runs vary within small ranges (e.g.
`subcircuit_with-llm`: bends 29–30, crossings 4, HPWL 201). Regenerate any config with:

```bash
uv run python -m src.cli --ckt=netlist.ckt --constraint-file=constraint-subcircuit_with-llm.json --num=10 --render --output_dir=results/subcircuit_with-llm
```

*Aligned groups* / *Group spread* come from each result JSON's `structure_score`, scored against
that config's 11 declared subcircuit groups (all-same-row-or-column count, and bounding-box spread;
lower spread = tighter). *Groups kept* is how many declared groups survived automatic de-confliction
(their constraints were applied); it can differ from *Aligned groups* because a group can end up
aligned in the final layout even when its own constraints were dropped. Rows with no declared
subcircuit groups show `–`.

## Automatic subcircuit de-confliction

Subcircuit library functions add *hard* placement constraints. Applied unconditionally, a
mislabeled or over-constrained group silently crowds out good LLM constraints. `generate_schematic`
de-conflicts automatically, for any subcircuit + LLM input, with no per-circuit editing:

1. LLM constraints are admitted first, against **no** subcircuit constraints — the high-value
   routing constraints get in on their own merits. Here **59/66** are admitted.
2. Each subcircuit group is then kept only if applying it displaces at most **2** of the retained
   LLM constraints. A group that clashes with several high-value LLM constraints is dropped; matched
   structures that clash only with low-value / internally-inconsistent LLM constraints are kept.
   Neither side is privileged — the conflict is resolved by whichever costs less.

On `subcircuit_with-llm` this automatically drops two simple current mirrors:

- `MosfetSimpleCurrentMirror[2]` `[m27, m28]` — would displace **4** LLM constraints (> budget 2)
- `MosfetSimpleCurrentMirror[4]` `[m6, m7, m5]` — would displace **3** LLM constraints (> budget 2)

Both fight the LLM `same_row` / `left_of` chains that thread these devices through the main signal
row (e.g. `left_of m6 m8`, `same_row m5 m6`, and the `same_column_above` bias stacks on `m5`), so
forcing them into a tight mirror group would cost more than it is worth. The other **9/11** groups
(the differential pair, both cascoded inverters, both four-transistor current mirrors, and the
remaining simple mirrors) are kept, and **55** LLM constraints are retained. The kept groups are
recorded as `constraint_subcircuit_accepted` in the result JSON; **55/65** softenable LLM
constraints hold in the final placement.

## Structural quality

Bends/crossings/HPWL don't capture *matched-device layout quality* — the reason subcircuit info
exists. `generate_schematic` also reports a `structure_score` (in the result JSON): for each
declared group of matched devices, whether it is **aligned** (all devices share a row or a column,
the analog convention) and its **spread** (bounding-box row_span + col_span; lower = tighter). The
result JSON also stores `component_positions`, so any layout can be scored post-hoc against a fixed
reference set of matched groups.

Scoring both `with-llm` layouts against the 11 declared groups of `subcircuit_with-llm`:

| Config | #Bends | #Crossings | HPWL | Aligned groups | Group spread |
| ----- | ----- | ----- | ----- | ----- | ----- |
| `subcircuit_with-llm` (auto de-conflicted) | **29** | **4** | 201 | 9/11 | **65** |
| `no-subcircuit_with-llm` | 44 | 10 | **186** | 9/11 | 76 |

Both layouts align the same 9/11 groups — the two unaligned ones are the four-transistor current
mirrors (`MosfetFourTransistorCurrentMirror[0]`/`[1]`), which share devices (`m10`, `m1`) and
inherently span both a row and a column, so neither config can collapse them onto one axis. But with
subcircuit info the matched groups are ~14% **tighter** (spread 65 vs 76) and the routing is far
cleaner — **29 bends / 4 crossings vs 44 / 10**. `no-subcircuit_with-llm` wins only on HPWL
(186 vs 201). With subcircuit info the schematic is markedly more readable (fewer bends and
crossings, tighter matched devices) at a modest HPWL cost.
