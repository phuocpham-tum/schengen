This directory contains (generatedd schematic) results from schengen for different configurations:

| Directory | Constraint Setting File | #Bends | #Crossings | HPWL | Aligned groups | Group spread | Groups kept | De-conflict action |
| ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- |
| `results/subcircuit_no-llm` | `constraint-subcircuit_no-llm.json` | 60 | 29 | 203 | 15/15 | 77 | 15/15 | none (no LLM to conflict) |
| `results/subcircuit_with-llm` | `constraint-subcircuit_with-llm.json` | 48 | 23 | 176 | 15/15 | 84 | 14/15 | dropped `MosfetSimpleCurrentMirror[2]` |
| `results/no-subcircuit_no-llm` | `constraint-no-subcircuit_no-llm.json` | 63 | 14 | 175 | – | – | – | – |
| `results/no-subcircuit_with-llm` | `constraint-no-subcircuit_with-llm.json` | 44 | 20 | 180 | – | – | – | – |
| `results/subcircuit_with-llm-claude` | `constraint-subcircuit_with-llm-claude.json` | 44 | 20 | 183 | 15/15 | 73 | 15/15 | none |

*Aligned groups* / *Group spread* come from each result JSON's `structure_score`, scored against
that config's declared subcircuit groups (all-same-row-or-column count, and bounding-box spread;
lower spread = tighter). *Groups kept* is how many declared groups survived automatic de-confliction
(their constraints were applied); the two differ because a group can end up aligned in the final
layout even when its own constraints were dropped. Rows with no declared subcircuit groups show `–`.

## Automatic subcircuit de-confliction

Subcircuit library functions add *hard* placement constraints. They used to be applied
unconditionally on every admission probe, so a mislabeled or over-constrained group silently
crowded out good LLM constraints: `subcircuit_with-llm` admitted only 52/64 LLM constraints and
landed at **54 bends / 19 crossings / 194 HPWL** — worse than `no-subcircuit_with-llm` on bends and
HPWL, defeating the point of supplying subcircuit info.

`generate_schematic` now de-conflicts automatically, for any subcircuit + LLM input, with no
per-circuit editing:

1. LLM constraints are admitted first, against **no** subcircuit constraints (59/64 here) — the
   high-value routing constraints get in on their own merits.
2. Each subcircuit group is then kept only if applying it displaces at most **2** of the retained
   LLM constraints. A group that clashes with several high-value LLM constraints is dropped;
   matched structures that clash only with low-value / internally-inconsistent LLM constraints are
   kept. Neither side is privileged — the conflict is resolved by whichever costs less.

On `subcircuit_with-llm` this automatically drops just `MosfetSimpleCurrentMirror[2]`
`[m1, m17, m19, m2]` — a truncated 4-of-5 current mirror whose forced `m17 < m2` ordering
contradicts the LLM `left_of m2 m17` (cost 3 > budget 2) — and keeps the other 14 groups (both
differential pairs, the cascodes, the remaining mirrors). Result: **48 / 23 / 176**, down from
54 / 19 / 194, now beating `no-subcircuit_with-llm` on HPWL (176 vs 180). The retained groups are
recorded as `constraint_subcircuit_accepted` in the result JSON.

## Structural quality

Bends/crossings/HPWL don't capture *matched-device layout quality* — the reason subcircuit info
exists. `generate_schematic` also reports a `structure_score` (in the result JSON): for each
declared group of matched devices, whether it is **aligned** (all devices share a row or a column,
the analog convention) and its **spread** (bounding-box row_span + col_span; lower = tighter). The
result JSON also stores `component_positions`, so any layout can be scored post-hoc against a fixed
reference set of matched groups.

Scoring both `with-llm` layouts against the 15 declared groups of `subcircuit_with-llm`:

| Config | #Bends | #Crossings | HPWL | Aligned groups | Group spread |
| ----- | ----- | ----- | ----- | ----- | ----- |
| `subcircuit_with-llm` (auto de-conflicted) | 48–49 | 23 | 176 | **15/15** | **84** |
| `no-subcircuit_with-llm` | 42–44 | 19–20 | 180 | 14/15 | 100 |

`no-subcircuit_with-llm` wins on raw bends but is *structurally worse*: it leaves one matched pair
unaligned (e.g. `MosfetAnalogInverter[1] = [m17, m24]`) and its groups are ~19% more scattered
(spread 100 vs 84). With subcircuit info the layout keeps every matched group aligned **and** wins
on HPWL — competitive on routing, better on structure.
