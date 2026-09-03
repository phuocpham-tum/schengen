# Generated Schematics — example-1 … example-15

Auto-generated with schengen's CLI (`python -m src.cli --ckt … --constraint-file … --render`). For each example one canonical schematic is shown together with its input netlist and the constraint set used. Metric encoding in result filenames: `schematic_result_{run}_{routingCost}_{bends}_{crossings}_{hpwl}`.

## Summary

| Example | Circuit | Devices | Bends | Crossings | HPWL |
| --- | --- | ---: | ---: | ---: | ---: |
| [`example-1`](#example-1) | Two-stage single-ended MOS OTA | 26 | 36 | 27 | 174 |
| [`example-2`](#example-2) | Single-stage folded-cascode OTA | 30 | 13 | 14 | 150 |
| [`example-3`](#example-3) | BJT cube-root function circuit | 48 | 309 | 265 | 648 |
| [`example-4`](#example-4) | Two-stage single-ended MOS OTA | 20 | 10 | 6 | 101 |
| [`example-5`](#example-5) | Two-stage cascode single-ended MOS OTA | 14 | 6 | 4 | 69 |
| [`example-6`](#example-6) | Single-stage fully-differential folded-cascode OTA | 36 | 98 | 54 | 207 |
| [`example-7`](#example-7) | Two-stage single-ended MOS op-amp | 19 | 19 | 2 | 104 |
| [`example-8`](#example-8) | Two-stage fully-differential MOS op-amp | 17 | 20 | 6 | 103 |
| [`example-9`](#example-9) | Two-stage single-ended MOS op-amp | 19 | 16 | 8 | 103 |
| [`example-10`](#example-10) | Two-stage fully-differential MOS op-amp with CMFB | 44 | 75 | 64 | 317 |
| [`example-11`](#example-11) | Two-stage single-ended MOS op-amp | 25 | 20 | 7 | 140 |
| [`example-12`](#example-12) | Three-stage NMC single-ended MOS op-amp | 27 | 34 | 19 | 137 |
| [`example-13`](#example-13) | Three-stage RNMC single-ended MOS op-amp | 18 | 22 | 8 | 80 |
| [`example-14`](#example-14) | Three-stage NMC fully-differential MOS op-amp | 35 | 56 | 46 | 277 |
| [`example-15`](#example-15) | Three-stage RNMC fully-differential MOS op-amp | 24 | 35 | 16 | 142 |

---

## LLM-generated constraints (Opus 4.8)

Generated with `scripts/generate_llm_constraints.py` (prompt `v0.0.2`, model `claude-opus-4-8`) into `example-N/opus_4.8_constraint.json`. All 15 pass validation with zero unknown-primitive and zero unknown-component warnings.

### Constraint counts

| Example | # LLM constraints |
| --- | ---: |
| example-1 | 58 |
| example-2 | 65 |
| example-3 | 28 |
| example-4 | 39 |
| example-5 | 30 |
| example-6 | 64 |
| example-7 | 27 |
| example-8 | 33 |
| example-9 | 30 |
| example-10 | 68 |
| example-11 | 44 |
| example-12 | 40 |
| example-13 | 34 |
| example-14 | 59 |
| example-15 | 40 |

### With vs without LLM constraints

Apples-to-apples A/B on the **same** base constraint file per example — identical subcircuit groups, path-based, orientation and user-defined constraints — toggling only whether the Opus-4.8 `llm_generated` list is included (`example-N/opus_4.8_constraint.json` vs `example-N/opus_4.8_constraint_no-llm.json`). Each cell is **mean ± population std over 10 seeds** (`SCHENGEN_SEED=1..10`, `--num 1`). Lower is better for every metric; `w/` = with LLM constraints, `w/o` = without.

| Example | Devices | Crossings w/ · w/o | Bends w/ · w/o | HPWL w/ · w/o | Routing cost w/ · w/o |
| --- | ---: | ---: | ---: | ---: | ---: |
| example-1 | 26 | 23.7±1.6 · 26.8±2.2 | 25.6±0.7 · 37.5±2.9 | 176.0±0.0 · 204.2±1.5 | 19618±1040 · 31363±963 |
| example-2 | 30 | 13.0±0.0 · 13.0±3.4 | 10.3±1.2 · 16.7±3.8 | 163.0±0.0 · 155.5±2.9 | 9686±595 · 12777±2612 |
| example-3 | 48 | 208.3±25.1 · 242.3±32.5 | 232.2±27.0 · 254.3±42.8 | 586.9±30.4 · 679.3±34.3 | 99294±8649 · 111776±14250 |
| example-4 | 20 | 6.0±0.0 · 6.0±0.0 | 10.4±0.5 · 10.7±0.5 | 101.0±0.0 · 101.0±0.0 | 6947±2500 · 5418±2341 |
| example-5 | 14 | 3.0±0.0 · 4.0±0.0 | 11.0±0.0 · 6.0±0.0 | 76.0±0.0 · 69.0±0.0 | 2685±0 · 3225±0 |
| example-6 † | 36 | 40.7±8.3 · 70.3±16.5 | 64.1±9.4 · 87.9±7.8 | 252.3±11.1 · 329.6±26.3 | 36425±2285 · 48933±7370 |
| example-7 | 19 | 3.9±4.7 · 8.7±4.8 | 15.5±4.0 · 29.3±5.8 | 81.5±1.4 · 96.8±6.7 | 9626±3709 · 18886±3534 |
| example-8 | 17 | 11.6±1.2 · 10.5±3.7 | 28.9±1.4 · 29.8±10.2 | 89.0±0.0 · 82.5±7.0 | 12447±623 · 15622±4655 |
| example-9 | 19 | 7.2±1.1 · 18.7±7.1 | 26.1±2.7 · 36.4±5.0 | 101.0±0.0 · 136.3±26.4 | 18335±1117 · 26452±7538 |
| example-10 † | 44 | 70.5±15.2 · 122.3±22.1 | 78.0±10.2 · 108.3±12.4 | 333.9±28.9 · 510.7±57.9 | 50050±3381 · 86288±13380 |
| example-11 | 25 | 13.5±1.5 · 26.8±6.6 | 25.9±4.0 · 41.6±6.1 | 123.4±3.2 · 187.6±18.9 | 20690±2163 · 30043±4589 |
| example-12 | 27 | 9.3±0.5 · 27.1±9.7 | 18.0±1.6 · 38.5±6.8 | 145.0±0.0 · 201.6±49.7 | 11362±463 · 28581±5580 |
| example-13 | 18 | 4.4±0.8 · 10.3±4.0 | 13.8±0.4 · 19.9±4.3 | 94.0±0.0 · 93.5±8.3 | 6012±243 · 13530±5941 |
| example-14 | 35 | 39.2±8.7 · 67.1±17.2 | 44.8±5.9 · 64.6±11.9 | 256.9±14.0 · 350.5±62.4 | 27884±3836 · 47801±8007 |
| example-15 † | 24 | 19.0±0.0 · 25.2±7.7 | 23.0±0.0 · 42.1±6.2 | 182.0±0.0 · 172.4±21.4 | 12026±227 · 24662±4747 |
| **Total** | — | **473±32 · 679±49** | **628±32 · 824±50** | **2762±46 · 3370±115** | **343086±11587 · 505356±26734** |

† without-LLM successful runs < 10 (example-6: 9, example-10: 6, example-15: 9). Without the LLM constraints the pipeline occasionally fails to place/route at the feasibility boundary; those means use the successful runs. All with-LLM runs succeeded (10/10). Totals are the sum of per-example means (std propagated in quadrature).

Averaged over 10 seeds the LLM constraints reduce crossings by ~30% (679 → 473), bends by ~24% (824 → 628), HPWL by ~18% (3370 → 2762) and routing cost by ~32% (505356 → 343086). They also **stabilise** the result: the without-LLM runs have markedly higher seed-to-seed variance and occasionally fail to route at all (see †), whereas every with-LLM run succeeded and several are near-deterministic (std 0). On mean crossings the LLM set wins in 12 of 15 examples, ties 2 (examples 2 and 4), and loses only 1 (example-8, by ~1 crossing — well within one std). The apparent regressions from the earlier single-seed run (examples 2, 4, 8) turn out to be ties or noise once averaged.

> A/B metrics above are seed averages and are **not** directly comparable to the canonical figures in the [Summary](#summary) table, which were rendered from each example's own committed constraint file (best-of-many).

### Side-by-side renders

Each pair is the same circuit placed and routed **with** (left) and **without** (right) the Opus-4.8 LLM constraints. These are single representative renders (`SCHENGEN_SEED=42`); exact pixels vary with seed, but the structural difference is consistent with the averaged metrics above.

| Example | With LLM | Without LLM |
| --- | --- | --- |
| example-1 | ![ex1 with LLM](example-1/opus_4.8_ab/with_llm.png) | ![ex1 without LLM](example-1/opus_4.8_ab/without_llm.png) |
| example-2 | ![ex2 with LLM](example-2/opus_4.8_ab/with_llm.png) | ![ex2 without LLM](example-2/opus_4.8_ab/without_llm.png) |
| example-3 | ![ex3 with LLM](example-3/opus_4.8_ab/with_llm.png) | ![ex3 without LLM](example-3/opus_4.8_ab/without_llm.png) |
| example-4 | ![ex4 with LLM](example-4/opus_4.8_ab/with_llm.png) | ![ex4 without LLM](example-4/opus_4.8_ab/without_llm.png) |
| example-5 | ![ex5 with LLM](example-5/opus_4.8_ab/with_llm.png) | ![ex5 without LLM](example-5/opus_4.8_ab/without_llm.png) |
| example-6 | ![ex6 with LLM](example-6/opus_4.8_ab/with_llm.png) | ![ex6 without LLM](example-6/opus_4.8_ab/without_llm.png) |
| example-7 | ![ex7 with LLM](example-7/opus_4.8_ab/with_llm.png) | ![ex7 without LLM](example-7/opus_4.8_ab/without_llm.png) |
| example-8 | ![ex8 with LLM](example-8/opus_4.8_ab/with_llm.png) | ![ex8 without LLM](example-8/opus_4.8_ab/without_llm.png) |
| example-9 | ![ex9 with LLM](example-9/opus_4.8_ab/with_llm.png) | ![ex9 without LLM](example-9/opus_4.8_ab/without_llm.png) |
| example-10 | ![ex10 with LLM](example-10/opus_4.8_ab/with_llm.png) | ![ex10 without LLM](example-10/opus_4.8_ab/without_llm.png) |
| example-11 | ![ex11 with LLM](example-11/opus_4.8_ab/with_llm.png) | ![ex11 without LLM](example-11/opus_4.8_ab/without_llm.png) |
| example-12 | ![ex12 with LLM](example-12/opus_4.8_ab/with_llm.png) | ![ex12 without LLM](example-12/opus_4.8_ab/without_llm.png) |
| example-13 | ![ex13 with LLM](example-13/opus_4.8_ab/with_llm.png) | ![ex13 without LLM](example-13/opus_4.8_ab/without_llm.png) |
| example-14 | ![ex14 with LLM](example-14/opus_4.8_ab/with_llm.png) | ![ex14 without LLM](example-14/opus_4.8_ab/without_llm.png) |
| example-15 | ![ex15 with LLM](example-15/opus_4.8_ab/with_llm.png) | ![ex15 without LLM](example-15/opus_4.8_ab/without_llm.png) |

---

### example-1 — Two-stage single-ended MOS OTA

Single netlist with declared subcircuit groups; rendered with the LLM+subcircuit constraint set (`constraint-subcircuit_with-llm-claude.json`).

**Metrics** — devices: 26 · bends: **36** · crossings: **27** · HPWL: **174** · routing cost: 28366

![example-1 schematic](example-1/docgen/schematic_result_0_28366_36_27_174.png)

<details><summary><b>Netlist</b> — <code>example-1/netlist.ckt</code> (26 components)</summary>

```spice
m1 net1 net1 vdd! vdd pmos
m2 net2 net1 vdd! vdd pmos
m3 ibias ibias gnd! gnd! nmos
m4 net1 ibias gnd! gnd! nmos
m5 net4 ibias gnd! gnd! nmos
m6 net5 in1 net4 gnd! nmos
m7 net6 in2 net4 gnd! nmos
m8 net5 net5 vdd! vdd! pmos
m9 net6 net6 vdd! vdd! pmos
m10 out1 net5 vdd! vdd! pmos
m11 out2 net6 vdd! vdd! pmos
m12 out1 net2 net7 gnd! nmos
m13 out2 net2 net8 gnd! nmos
m14 net7 net9 gnd! gnd! nmos
m15 net8 net9 gnd! gnd! nmos
m16 net9 net9 gnd! gnd! nmos
m17 net9 net1 vdd! vdd! pmos
m18 net10 net1 vdd! vdd! pmos
m19 net13 net1 vdd! vdd! pmos
m20 net11 out2 net10 vdd! pmos
m21 net9 vcm net10 vdd! pmos
m22 net9 vcm net13 vdd! pmos
m23 net11 out1 net13 vdd! pmos
m24 net9 net11 gnd! gnd! nmos
m25 net11 net11 gnd! gnd! nmos
m26 net2 net2 gnd! gnd! nmos
```
</details>

<details><summary><b>Constraints</b></summary>

Constraint file: [`constraint-subcircuit_with-llm-claude.json`](example-1/constraint-subcircuit_with-llm-claude.json)

**Subcircuit groups**
```json
{
  "MosfetCascodedNMOSAnalogInverter[1]": [
    "m10",
    "m12",
    "m14"
  ],
  "MosfetCascodedNMOSAnalogInverter[2]": [
    "m11",
    "m13",
    "m15"
  ],
  "MosfetPmosNonInvertingInverter[1]": [
    "m1",
    "m4"
  ],
  "MosfetAnalogInverter[1]": [
    "m17",
    "m24"
  ],
  "MosfetDifferentialPair[1]": [
    "m20",
    "m21"
  ],
  "MosfetDifferentialPair[2]": [
    "m23",
    "m22"
  ],
  "MosfetDifferentialPair[3]": [
    "m6",
    "m7"
  ],
  "MosfetNmosDiodeAnalogInverter[1]": [
    "m2",
    "m26"
  ],
  "MosfetNmosDiodeAnalogInverter[2]": [
    "m17",
    "m16"
  ],
  "MosfetSimpleCurrentMirror[1]": [
    "m3",
    "m4",
    "m5"
  ],
  "MosfetSimpleCurrentMirror[2]": [
    "m1",
    "m17",
    "m19",
    "m2"
  ],
  "MosfetSimpleCurrentMirror[3]": [
    "m25",
    "m24"
  ],
  "MosfetSimpleCurrentMirror[4]": [
    "m8",
    "m10"
  ],
  "MosfetSimpleCurrentMirror[5]": [
    "m9",
    "m11"
  ],
  "MosfetSimpleCurrentMirror[6]": [
    "m16",
    "m14",
    "m15"
  ]
}
```

**LLM-generated constraints**
```json
[
  [
    "left_of",
    "m6",
    "m7"
  ],
  [
    "same_row",
    "m6",
    "m7"
  ],
  [
    "left_of",
    "m8",
    "m9"
  ],
  [
    "same_row",
    "m8",
    "m9"
  ],
  [
    "left_of",
    "m10",
    "m11"
  ],
  [
    "same_row",
    "m10",
    "m11"
  ],
  [
    "left_of",
    "m12",
    "m13"
  ],
  [
    "same_row",
    "m12",
    "m13"
  ],
  [
    "left_of",
    "m14",
    "m15"
  ],
  [
    "same_row",
    "m14",
    "m15"
  ],
  [
    "left_of",
    "m20",
    "m21"
  ],
  [
    "same_row",
    "m20",
    "m21"
  ],
  [
    "left_of",
    "m23",
    "m22"
  ],
  [
    "same_row",
    "m23",
    "m22"
  ],
  [
    "left_of",
    "m24",
    "m25"
  ],
  [
    "same_row",
    "m24",
    "m25"
  ],
  [
    "left_of",
    "m1",
    "m2"
  ],
  [
    "same_row",
    "m1",
    "m2"
  ],
  [
    "left_of",
    "m17",
    "m18"
  ],
  [
    "same_row",
    "m17",
    "m18"
  ],
  [
    "left_of",
    "m18",
    "m19"
  ],
  [
    "same_row",
    "m18",
    "m19"
  ],
  [
    "left_of",
    "m3",
    "m4"
  ],
  [
    "same_row",
    "m3",
    "m4"
  ],
  [
    "left_of",
    "m4",
    "m5"
  ],
  [
    "same_row",
    "m4",
    "m5"
  ],
  [
    "same_column_above",
    "m8",
    "m6"
  ],
  [
    "same_column_above",
    "m9",
    "m7"
  ],
  [
    "same_column_above",
    "m10",
    "m12"
  ],
  [
    "same_column_above",
    "m11",
    "m13"
  ],
  [
    "same_column_above",
    "m12",
    "m14"
  ],
  [
    "same_column_above",
    "m13",
    "m15"
  ],
  [
    "same_column_above",
    "m1",
    "m4"
  ],
  [
    "same_column_above",
    "m2",
    "m26"
  ],
  [
    "same_column_above",
    "m17",
    "m16"
  ],
  [
    "same_column_above",
    "m18",
    "m20"
  ],
  [
    "same_column_above",
    "m19",
    "m22"
  ],
  [
    "t_junction",
    "m5",
    "m6",
    "m7"
  ]
]
```

**Path-based constraints**
```
CONSTRAINT_2_SORT_VDD_GND_TRACABILITY
CONSTRAINT_3_1_SHARE_GATE_TO_GATE_CONNECTION_NO_CLEAR_COLUMNS
CONSTRAINT_6_PLACE_VDD_DIFFERENT_COLUMN
CONSTRAINT_7_DONT_PLACE_TOO_CLOSE_TO_BOUNDARIES
CONSTRAINT_8_PLACE_CAPACITORS_MIDDLE
CONSTRAINT_9_PLACE_INPUT_PORTS_LEFT
CONSTRAINT_10_PLACE_OUTPUT_PORTS_RIGHT
CONSTRAINT_11_PLACE_BIASING_PORTS_LEFT
CONSTRAINT_12_PLACE_VDD_PORTS_TOP_RIGHT
CONSTRAINT_4_SHARE_SOURCE_TO_SOURCE_CONNECTION
CONSTRAINT_5_PLACE_SEPARATELY_2
```

**Terminals**: `in1`, `in2`, `out1`, `out2`, `vdd!`, `ibias`, `gnd!`

</details>

---

### example-2 — Single-stage folded-cascode OTA

Rendered with its matching LLM+subcircuit constraint set.

**Metrics** — devices: 30 · bends: **13** · crossings: **14** · HPWL: **150** · routing cost: 11174

![example-2 schematic](example-2/docgen/schematic_result_0_11174_13_14_150.png)

<details><summary><b>Netlist</b> — <code>example-2/netlist.ckt</code> (30 components)</summary>

```spice
m1 net1 ibias vdd! vdd! pmos
m2 net3 ibias vdd! vdd! pmos
m3 net5 ibias vdd! vdd! pmos
m4 net10 net12 vdd! vdd! pmos
m5 net6 net8 vdd! vdd! pmos
m6 net8 net8 vdd! vdd! pmos
m7 net8 net8 vdd! vdd! pmos
m8 net12 net12 vdd! vdd! pmos
m9 net11 net12 vdd! vdd! pmos
m10 ibias ibias net1 vdd! pmos
m11 net2 ibias net3 vdd! pmos
m12 net4 ibias net5 vdd! pmos
m13 net9 ibias net10 vdd! pmos
m14 output_n ibias net6 vdd! pmos
m15 net7 ibias net8 vdd! pmos
m16 output_p ibias net11 vdd! pmos
m17 net8 in1 net13 gnd! nmos
m18 net12 in2 net13 gnd! nmos
m19 net2 net2 gnd! gnd! nmos
m20 net13 net2 gnd! gnd! nmos
m21 net4 net4 net14 gnd! nmos
m22 net9 net4 net17 gnd! nmos
m23 output_n net4 net15 gnd! nmos
m24 net7 net4 net16 gnd! nmos
m25 output_p net4 net18 gnd! nmos
m26 net14 net14 gnd! gnd! nmos
m27 net17 net17 gnd! gnd! nmos
m28 net15 net17 gnd! gnd! nmos
m29 net16 net16 gnd! gnd! nmos
m30 net18 net16 gnd! gnd! nmos
```
</details>

<details><summary><b>Constraints</b></summary>

Constraint file: [`constraint-subcircuit_with-llm.json`](example-2/constraint-subcircuit_with-llm.json)

**Subcircuit groups**
```json
{
  "MosfetDifferentialPair[0]": [
    "m17",
    "m18"
  ],
  "MosfetCascodeAnalogInverterNmosDiodeTransistor[0]": [
    "m13",
    "m4",
    "m22",
    "m27"
  ],
  "MosfetCascodedAnalogInverter[0]": [
    "m14",
    "m5",
    "m23",
    "m28"
  ],
  "MosfetCascodedAnalogInverter[1]": [
    "m16",
    "m9",
    "m25",
    "m30"
  ],
  "MosfetFourTransistorCurrentMirror[0]": [
    "m10",
    "m1",
    "m11",
    "m2"
  ],
  "MosfetFourTransistorCurrentMirror[1]": [
    "m10",
    "m1",
    "m12",
    "m3"
  ],
  "MosfetSimpleCurrentMirror[0]": [
    "m8",
    "m4",
    "m9"
  ],
  "MosfetSimpleCurrentMirror[1]": [
    "m29",
    "m30"
  ],
  "MosfetSimpleCurrentMirror[2]": [
    "m27",
    "m28"
  ],
  "MosfetSimpleCurrentMirror[3]": [
    "m19",
    "m20"
  ],
  "MosfetSimpleCurrentMirror[4]": [
    "m6",
    "m7",
    "m5"
  ]
}
```

**LLM-generated constraints**
```json
[
  [
    "left_of",
    "m1",
    "m2"
  ],
  [
    "left_of",
    "m2",
    "m3"
  ],
  [
    "left_of",
    "m3",
    "m7"
  ],
  [
    "left_of",
    "m7",
    "m5"
  ],
  [
    "left_of",
    "m5",
    "m6"
  ],
  [
    "left_of",
    "m6",
    "m8"
  ],
  [
    "left_of",
    "m8",
    "m9"
  ],
  [
    "left_of",
    "m9",
    "m4"
  ],
  [
    "same_row",
    "m1",
    "m2"
  ],
  [
    "same_row",
    "m2",
    "m3"
  ],
  [
    "same_row",
    "m3",
    "m7"
  ],
  [
    "same_row",
    "m7",
    "m5"
  ],
  [
    "same_row",
    "m5",
    "m6"
  ],
  [
    "same_row",
    "m6",
    "m8"
  ],
  [
    "same_row",
    "m8",
    "m9"
  ],
  [
    "same_row",
    "m9",
    "m4"
  ],
  [
    "same_row",
    "m10",
    "m11"
  ],
  [
    "same_row",
    "m11",
    "m12"
  ],
  [
    "same_row",
    "m12",
    "m15"
  ],
  [
    "same_row",
    "m15",
    "m14"
  ],
  [
    "same_row",
    "m14",
    "m17"
  ],
  [
    "same_row",
    "m17",
    "m18"
  ],
  [
    "same_row",
    "m18",
    "m16"
  ],
  [
    "same_row",
    "m16",
    "m13"
  ],
  [
    "same_row",
    "m19",
    "m21"
  ],
  [
    "same_row",
    "m21",
    "m24"
  ],
  [
    "same_row",
    "m24",
    "m23"
  ],
  [
    "same_row",
    "m23",
    "m20"
  ],
  [
    "same_row",
    "m20",
    "m25"
  ],
  [
    "same_row",
    "m25",
    "m22"
  ],
  [
    "same_row",
    "m26",
    "m29"
  ],
  [
    "same_row",
    "m29",
    "m28"
  ],
  [
    "same_row",
    "m28",
    "m30"
  ],
  [
    "same_row",
    "m30",
    "m27"
  ],
  [
    "same_column_above",
    "m1",
    "m10"
  ],
  [
    "same_column_above",
    "m2",
    "m11"
  ],
  [
    "same_column_above",
    "m11",
    "m19"
  ],
  [
    "same_column_above",
    "m3",
    "m12"
  ],
  [
    "same_column_above",
    "m12",
    "m21"
  ],
  [
    "same_column_above",
    "m21",
    "m26"
  ],
  [
    "same_column_above",
    "m7",
    "m15"
  ],
  [
    "same_column_above",
    "m15",
    "m24"
  ],
  [
    "same_column_above",
    "m24",
    "m29"
  ],
  [
    "same_column_above",
    "m5",
    "m14"
  ],
  [
    "same_column_above",
    "m14",
    "m23"
  ],
  [
    "same_column_above",
    "m23",
    "m28"
  ],
  [
    "same_column_above",
    "m6",
    "m17"
  ],
  [
    "same_column_above",
    "m8",
    "m18"
  ],
  [
    "same_column_above",
    "m9",
    "m16"
  ],
  [
    "same_column_above",
    "m16",
    "m25"
  ],
  [
    "same_column_above",
    "m25",
    "m30"
  ],
  [
    "same_column_above",
    "m4",
    "m13"
  ],
  [
    "same_column_above",
    "m13",
    "m22"
  ],
  [
    "same_column_above",
    "m22",
    "m27"
  ],
  [
    "row_proximity",
    1,
    "m3",
    "m12"
  ],
  [
    "row_proximity",
    1,
    "m12",
    "m21"
  ],
  [
    "row_proximity",
    1,
    "m21",
    "m26"
  ],
  [
    "column_proximity",
    2,
    "m1",
    "m2"
  ],
  [
    "column_proximity",
    2,
    "m2",
    "m3"
  ],
  [
    "column_proximity",
    2,
    "m3",
    "m7"
  ],
  [
    "column_proximity",
    2,
    "m7",
    "m5"
  ],
  [
    "column_proximity",
    2,
    "m5",
    "m6"
  ],
  [
    "column_proximity",
    2,
    "m6",
    "m8"
  ],
  [
    "column_proximity",
    2,
    "m8",
    "m9"
  ],
  [
    "column_proximity",
    2,
    "m9",
    "m4"
  ],
  [
    "t_junction",
    "m20",
    "m17",
    "m18"
  ]
]
```

**Path-based constraints**
```
CONSTRAINT_1_SHARE_DRAIN_SOURCE_CONNECTION
CONSTRAINT_1_SHARE_DRAIN_DRAIN_CONNECTION
CONSTRAINT_2_SORT_VDD_GND_TRACABILITY
CONSTRAINT_6_PLACE_VDD_DIFFERENT_COLUMN
CONSTRAINT_7_DONT_PLACE_TOO_CLOSE_TO_BOUNDARIES
CONSTRAINT_8_PLACE_CAPACITORS_MIDDLE
CONSTRAINT_9_PLACE_INPUT_PORTS_LEFT
CONSTRAINT_10_PLACE_OUTPUT_PORTS_RIGHT
CONSTRAINT_11_PLACE_BIASING_PORTS_LEFT
CONSTRAINT_12_PLACE_VDD_PORTS_TOP_RIGHT
CONSTRAINT_4_SHARE_SOURCE_TO_SOURCE_CONNECTION
CONSTRAINT_5_PLACE_SEPARATELY_2
```

**Terminals**: `ibias`, `in1`, `in2`, `output_n`, `output_p`, `vdd!`, `gnd!`

</details>

---

### example-3 — BJT cube-root function circuit

Dense BJT analog computer. Rendered with the generic constraint set (`constraints-general.json`).

**Metrics** — devices: 48 · bends: **309** · crossings: **265** · HPWL: **648** · routing cost: 121739

![example-3 schematic](example-3/docgen/schematic_result_0_121739_309_265_648.png)

<details><summary><b>Netlist</b> — <code>example-3/netlist.ckt</code> (48 components)</summary>

```spice
Q1 net_internal_10 net_internal_6 net_input_0 pnp
R1 net_internal_10 -15V 3110178.7
R2 net_internal_9 net_internal_4 161102112.9
Q2 net_internal_17 -15V net_internal_13 pnp
Q3 net_internal_4 net_internal_10 net_output_0 pnp
Q4 net_output_0 net_internal_4 net_internal_17 npn
R3 -15V net_internal_4 7615.4
Q5 net_output_0 net_internal_24 net_internal_11 pnp
Q6 net_internal_3 net_internal_6 net_internal_10 npn
R4 net_internal_0 net_internal_6 617886.2
R5 net_internal_0 net_internal_9 1000000000.0
R6 +15V net_output_0 1155.5
R7 GND net_internal_0 10918279.7
R8 net_internal_5 net_internal_0 2408606.5
R9 net_internal_5 net_internal_13 247270875.4
Q7 net_internal_5 GND net_internal_2 pnp
R10 net_internal_10 net_internal_5 690664162.6
R11 net_output_0 net_internal_2 8234226.5
R12 -15V net_input_0 2624416.3
R13 net_internal_10 net_internal_13 579383811.9
Q8 net_internal_19 net_internal_8 net_internal_8 pnp
R14 net_internal_11 net_internal_8 1000000000.0
Q9 net_internal_26 net_internal_8 net_internal_6 pnp
R15 net_internal_4 net_internal_14 51281086.1
R16 GND net_internal_23 210406.0
Q10 GND net_internal_2 net_internal_5 pnp
Q11 net_internal_5 net_internal_11 net_internal_1 pnp
Q12 net_internal_5 net_output_0 net_internal_23 pnp
R17 net_internal_3 net_internal_2 126965281.4
R18 net_internal_21 net_internal_26 38850620.1
Q13 net_internal_3 net_internal_14 net_internal_5 npn
Q14 net_internal_13 net_internal_14 net_output_0 pnp
R19 net_internal_1 net_internal_16 368418577.0
Q15 net_internal_12 net_internal_26 net_internal_19 pnp
Q16 net_internal_16 net_internal_12 -15V npn
Q17 net_internal_22 net_internal_10 net_internal_7 pnp
R20 net_internal_22 net_internal_5 160893.8
Q18 net_internal_22 net_internal_20 net_internal_9 pnp
Q19 -15V net_internal_9 net_internal_12 pnp
R21 net_internal_24 net_input_0 84681453.6
Q20 net_internal_16 net_internal_7 net_internal_12 pnp
Q21 -15V net_internal_7 -15V pnp
Q22 net_internal_20 net_internal_15 net_internal_5 pnp
Q23 net_internal_15 net_internal_1 net_internal_9 npn
R22 net_internal_21 net_internal_16 424487.3
Q24 net_internal_8 net_internal_15 net_internal_11 pnp
R23 net_output_0 net_internal_14 33433232.1
Q25 net_internal_6 net_internal_23 net_internal_10 pnp
```
</details>

<details><summary><b>Constraints</b></summary>

Constraint file: [`constraints-general.json`](example-3/constraints-general.json)

**User-defined constraints**
```json
[
  [
    "above_all",
    1,
    "terminal_+15V"
  ],
  [
    "below_all",
    1,
    "terminal_-15V"
  ],
  [
    "middle_all",
    "terminal_GND"
  ]
]
```

**Path-based constraints**
```
CONSTRAINT_1_SHARE_DRAIN_SOURCE_CONNECTION
CONSTRAINT_3_SHARE_GATE_TO_GATE_CONNECTION
CONSTRAINT_6_PLACE_VDD_DIFFERENT_COLUMN
CONSTRAINT_7_DONT_PLACE_TOO_CLOSE_TO_BOUNDARIES
CONSTRAINT_8_PLACE_CAPACITORS_MIDDLE
CONSTRAINT_9_PLACE_INPUT_PORTS_LEFT
CONSTRAINT_10_PLACE_OUTPUT_PORTS_RIGHT
CONSTRAINT_11_PLACE_BIASING_PORTS_LEFT
CONSTRAINT_12_PLACE_VDD_PORTS_TOP_RIGHT
CONSTRAINT_5_PLACE_SEPARATELY_3
```

**Terminals**: `net_output_0`, `net_input_0`, `+15V`, `-15V`, `GND`

</details>

---

### example-4 — Two-stage single-ended MOS OTA

Single netlist + single constraint set.

**Metrics** — devices: 20 · bends: **10** · crossings: **6** · HPWL: **101** · routing cost: 8981

![example-4 schematic](example-4/docgen/schematic_result_0_8981_10_6_101.png)

<details><summary><b>Netlist</b> — <code>example-4/netlist.ckt</code> (20 components)</summary>

```spice
c1 net1 out
c2 net2 out
m1 net3 ibias gnd! gnd! nmos
m2 net4 ibias gnd! gnd! nmos
m3 net5 net5 vdd! vdd! pmos
m4 net1 net3 net6 net6 pmos
m5 net6 net5 vdd! vdd! pmos
m6 net7 ibias gnd! gnd! nmos
m7 net5 in1 net7 net7 nmos
m8 net1 in2 net7 net7 nmos
c3 out gnd!
m9 net8 net8 gnd! gnd! nmos
m10 net8 net1 vdd! vdd! pmos
m11 net2 net8 gnd! gnd! nmos
m12 net2 net4 vdd! vdd! pmos
m13 out ibias gnd! gnd! nmos
m14 out net2 vdd! vdd! pmos
m15 ibias ibias gnd! gnd! nmos
m16 net3 net3 vdd! vdd! pmos
m17 net4 net4 vdd! vdd! pmos
```
</details>

<details><summary><b>Constraints</b></summary>

Constraint file: [`constraint.json`](example-4/constraint.json)

**Subcircuit groups**
```json
{
  "MosfetAnalogInverter[0]": [
    "m14",
    "m13"
  ],
  "MosfetAnalogInverter[1]": [
    "m12",
    "m11"
  ],
  "MosfetDifferentialPair[1]": [
    "m7",
    "m8"
  ],
  "MosfetNmosDiodeAnalogInverter[1]": [
    "m10",
    "m9"
  ],
  "MosfetPmosDiodeAnalogInverter[1]": [
    "m16",
    "m1"
  ],
  "MosfetPmosDiodeAnalogInverter[2]": [
    "m17",
    "m2"
  ],
  "MosfetSimpleCurrentMirror[1]": [
    "m3",
    "m5"
  ],
  "MosfetSimpleCurrentMirror[2]": [
    "m9",
    "m11"
  ],
  "MosfetSimpleCurrentMirror[3]": [
    "m15",
    "m6",
    "m1",
    "m2",
    "m13"
  ],
  "MosfetSimpleCurrentMirror[7]": [
    "m17",
    "m12"
  ]
}
```

**User-defined constraints**
```json
[
  [
    "t_junction",
    "m6",
    "m7",
    "m8"
  ]
]
```

**Orientation constraints**
```json
{
  "m16": 1,
  "m5": 1,
  "m12": 1,
  "m14": 1
}
```

**Path-based constraints**
```
CONSTRAINT_1_SHARE_DRAIN_SOURCE_CONNECTION
CONSTRAINT_1_SHARE_DRAIN_DRAIN_CONNECTION
CONSTRAINT_2_SORT_VDD_GND_TRACABILITY
CONSTRAINT_3_SHARE_GATE_TO_GATE_CONNECTION
CONSTRAINT_6_PLACE_VDD_DIFFERENT_COLUMN
CONSTRAINT_7_DONT_PLACE_TOO_CLOSE_TO_BOUNDARIES
CONSTRAINT_8_PLACE_CAPACITORS_MIDDLE
CONSTRAINT_9_PLACE_INPUT_PORTS_LEFT
CONSTRAINT_10_PLACE_OUTPUT_PORTS_RIGHT
CONSTRAINT_11_PLACE_BIASING_PORTS_LEFT
CONSTRAINT_12_PLACE_VDD_PORTS_TOP_RIGHT
CONSTRAINT_4_SHARE_SOURCE_TO_SOURCE_CONNECTION
CONSTRAINT_5_PLACE_SEPARATELY_2
```

**Terminals**: `in1`, `in2`, `out`, `vdd!`, `gnd!`, `ibias`

</details>

---

### example-5 — Two-stage cascode single-ended MOS OTA

Single netlist + single constraint set.

**Metrics** — devices: 14 · bends: **6** · crossings: **4** · HPWL: **69** · routing cost: 3226

![example-5 schematic](example-5/docgen/schematic_result_0_3226_6_4_69.png)

<details><summary><b>Netlist</b> — <code>example-5/netlist.ckt</code> (14 components)</summary>

```spice
c1 net1 out
m1 net2 ibias gnd! gnd! nmos
m2 net3 net3 vdd! vdd! pmos
m3 net1 net2 net4 net4 pmos
m4 net4 net3 vdd! vdd! pmos
m5 net5 ibias gnd! gnd! nmos
m6 net3 in1 net5 net5 nmos
m7 net1 in2 net5 net5 nmos
c2 out gnd!
m8 out ibias gnd! gnd! nmos
m9 out net2 net6 net6 pmos
m10 net6 net1 vdd! vdd! pmos
m11 ibias ibias gnd! gnd! nmos
m12 net2 net2 vdd! vdd! pmos
```
</details>

<details><summary><b>Constraints</b></summary>

Constraint file: [`constraint.json`](example-5/constraint.json)

**Subcircuit groups**
```json
{
  "MosfetCascodedPMOSAnalogInverter[0]": [
    "m9",
    "m8"
  ],
  "MosfetDifferentialPair[0]": [
    "m6",
    "m7"
  ],
  "MosfetSimpleCurrentMirror[0]": [
    "m2",
    "m4"
  ],
  "MosfetSimpleCurrentMirror[1]": [
    "m11",
    "m5",
    "m8",
    "m1"
  ]
}
```

**Path-based constraints**
```
CONSTRAINT_1_SHARE_DRAIN_SOURCE_CONNECTION
CONSTRAINT_1_SHARE_DRAIN_DRAIN_CONNECTION
CONSTRAINT_2_SORT_VDD_GND_TRACABILITY
CONSTRAINT_3_SHARE_GATE_TO_GATE_CONNECTION
CONSTRAINT_6_PLACE_VDD_DIFFERENT_COLUMN
CONSTRAINT_7_DONT_PLACE_TOO_CLOSE_TO_BOUNDARIES
CONSTRAINT_8_PLACE_CAPACITORS_MIDDLE
CONSTRAINT_9_PLACE_INPUT_PORTS_LEFT
CONSTRAINT_10_PLACE_OUTPUT_PORTS_RIGHT
CONSTRAINT_11_PLACE_BIASING_PORTS_LEFT
CONSTRAINT_12_PLACE_VDD_PORTS_TOP_RIGHT
CONSTRAINT_4_SHARE_SOURCE_TO_SOURCE_CONNECTION
CONSTRAINT_5_PLACE_SEPARATELY_2
```

**Terminals**: `in1`, `in2`, `out`, `vdd!`, `gnd!`, `ibias`

</details>

---

### example-6 — Single-stage fully-differential folded-cascode OTA

Rendered with its LLM constraint set (`constraint-with-llm.json`).

**Metrics** — devices: 36 · bends: **98** · crossings: **54** · HPWL: **207** · routing cost: 48306

![example-6 schematic](example-6/docgen/schematic_result_0_48306_98_54_207.png)

<details><summary><b>Netlist</b> — <code>example-6/netlist.ckt</code> (36 components)</summary>

```spice
m1 nref nref vdd! vdd! pmos
m2 vntop nref vdd! vdd! pmos
m3 vnbot vntop net1 gnd! nmos
m4 net1 vnbot gnd! gnd! nmos
m5 vpbot vnbot gnd! gnd! nmos
m6 net3 vptop vdd! vdd! pmos
m7 vptop vpbot net3 vdd! pmos
r1 nref gnd! 1k
r2 vntop vnbot 13.4k
r3 vptop vpbot 13.4k
m9 tail vptop vdd! vdd! pmos
m15 foldp inp tail vdd! pmos
m16 foldn inn tail vdd! pmos
m17 foldp vnbot gnd! gnd! nmos
m18 foldn vnbot gnd! gnd! nmos
m19 vo1p vntop foldp gnd! nmos
m20 vo1n vntop foldn gnd! nmos
m21 vo1p vpbot ptl vdd! pmos
m22 vo1n vpbot ptr vdd! pmos
m23 ptl vcmfb vdd! vdd! pmos
m24 ptr vcmfb vdd! vdd! pmos
m11 outp vpbot vdd! vdd! pmos
m12 outm vpbot vdd! vdd! pmos
m8 outp vo1p gnd! gnd! nmos
m10 outm vo1n gnd! gnd! nmos
r4 outp vfcascmv 200k
r5 outm vfcascmv 200k
r6 outp ncp 4k
c1 ncp vo1p 20f
r7 outm ncn 4k
c2 ncn vo1n 20f
m25 ctail vnbot gnd! gnd! nmos
m26 cn1 vrefcm ctail gnd! nmos
m27 vcmfb vfcascmv ctail gnd! nmos
m28 cn1 cn1 vdd! vdd! pmos
m29 vcmfb cn1 vdd! vdd! pmos
```
</details>

<details><summary><b>Constraints</b></summary>

Constraint file: [`constraint-with-llm.json`](example-6/constraint-with-llm.json)

**Subcircuit groups**
```json
{
  "MosfetSimpleCurrentMirror[1]": [
    "m1",
    "m2"
  ],
  "MosfetSimpleCurrentMirror[2]": [
    "m28",
    "m29"
  ],
  "MosfetSimpleCurrentMirror[3]": [
    "m17",
    "m18"
  ],
  "MosfetSimpleCurrentMirror[4]": [
    "m11",
    "m12"
  ],
  "MosfetSimpleCurrentMirror[5]": [
    "m21",
    "m22"
  ],
  "MosfetSimpleCurrentMirror[6]": [
    "m23",
    "m24"
  ],
  "MosfetSimpleCurrentMirror[7]": [
    "m19",
    "m20"
  ],
  "MosfetDifferentialPair[1]": [
    "m16",
    "m15"
  ]
}
```

**LLM-generated constraints**
```json
[
  [
    "same_column_above",
    "m3",
    "m4"
  ],
  [
    "same_column_above",
    "m6",
    "m7"
  ],
  [
    "same_column_above",
    "m23",
    "m21"
  ],
  [
    "same_column_above",
    "m21",
    "m19"
  ],
  [
    "same_column_above",
    "m19",
    "m17"
  ],
  [
    "same_column_above",
    "m24",
    "m22"
  ],
  [
    "same_column_above",
    "m22",
    "m20"
  ],
  [
    "same_column_above",
    "m20",
    "m18"
  ],
  [
    "same_row",
    "m23",
    "m24"
  ],
  [
    "same_row",
    "m21",
    "m22"
  ],
  [
    "same_row",
    "m19",
    "m20"
  ],
  [
    "same_row",
    "m17",
    "m18"
  ],
  [
    "left_of",
    "m23",
    "m24"
  ],
  [
    "left_of",
    "m21",
    "m22"
  ],
  [
    "left_of",
    "m19",
    "m20"
  ],
  [
    "left_of",
    "m17",
    "m18"
  ],
  [
    "same_column_above",
    "m11",
    "m8"
  ],
  [
    "same_column_above",
    "m12",
    "m10"
  ],
  [
    "same_row",
    "m11",
    "m12"
  ],
  [
    "left_of",
    "m11",
    "m12"
  ],
  [
    "same_row",
    "m8",
    "m10"
  ],
  [
    "left_of",
    "m8",
    "m10"
  ],
  [
    "same_column_above",
    "m28",
    "m26"
  ],
  [
    "same_column_above",
    "m29",
    "m27"
  ],
  [
    "same_row",
    "m28",
    "m29"
  ],
  [
    "left_of",
    "m28",
    "m29"
  ],
  [
    "left_of",
    "m2",
    "m15"
  ],
  [
    "left_of",
    "m15",
    "m21"
  ],
  [
    "left_of",
    "m16",
    "m22"
  ],
  [
    "left_of",
    "m21",
    "m11"
  ],
  [
    "left_of",
    "m22",
    "m12"
  ],
  [
    "left_of",
    "m11",
    "m28"
  ],
  [
    "left_of",
    "m12",
    "m29"
  ],
  [
    "same_column_above",
    "m9",
    "m15"
  ],
  [
    "same_column_above",
    "m26",
    "m25"
  ],
  [
    "same_row",
    "m26",
    "m27"
  ],
  [
    "left_of",
    "m26",
    "m27"
  ]
]
```

**User-defined constraints**
```json
[
  [
    "same_row",
    "terminal_vrefcm",
    "m26"
  ],
  [
    "column_proximity",
    3,
    "terminal_vrefcm",
    "m26"
  ]
]
```

**Path-based constraints**
```
CONSTRAINT_1_SHARE_DRAIN_SOURCE_CONNECTION
CONSTRAINT_2_SORT_VDD_GND_TRACABILITY
CONSTRAINT_3_SHARE_GATE_TO_GATE_CONNECTION
CONSTRAINT_6_PLACE_VDD_DIFFERENT_COLUMN
CONSTRAINT_7_DONT_PLACE_TOO_CLOSE_TO_BOUNDARIES
CONSTRAINT_8_PLACE_CAPACITORS_MIDDLE
CONSTRAINT_9_PLACE_INPUT_PORTS_LEFT
CONSTRAINT_10_PLACE_OUTPUT_PORTS_RIGHT
CONSTRAINT_11_PLACE_BIASING_PORTS_LEFT
CONSTRAINT_12_PLACE_VDD_PORTS_TOP_RIGHT
CONSTRAINT_4_SHARE_SOURCE_TO_SOURCE_CONNECTION
CONSTRAINT_5_PLACE_SEPARATELY_2
```

**Terminals**: `inp`, `inn`, `outp`, `outm`, `vrefcm`, `vdd!`, `gnd!`

</details>

---

### example-7 — Two-stage single-ended MOS op-amp

Single netlist + single constraint set.

**Metrics** — devices: 19 · bends: **19** · crossings: **2** · HPWL: **104** · routing cost: 9038

![example-7 schematic](example-7/docgen/schematic_result_0_9038_19_2_104.png)

<details><summary><b>Netlist</b> — <code>example-7/netlist.ckt</code> (19 components)</summary>

```spice
m1 net1 in1 net2 net2 nmos
m2 net3 in2 net2 net2 nmos
m3 net1 net1 vdd! vdd! pmos
m4 net3 net1 vdd! vdd! pmos
r1 net2 gnd!
m5 ibias ibias gnd! gnd! nmos
m6 net4 ibias gnd! gnd! nmos
m7 net4 net4 vdd! vdd! pmos
m8 net5 net4 vdd! vdd! pmos
m9 net5 net5 gnd! gnd! nmos
m10 net6 ibias gnd! gnd! nmos
m11 net7 net5 net6 gnd! nmos
m12 net7 net7 vdd! vdd! pmos
m13 net8 net7 vdd! vdd! pmos
m14 net8 net8 gnd! gnd! nmos
r2 net3 net9
c1 net9 out
m15 out net3 vdd! vdd! pmos
m16 out net8 gnd! gnd! nmos
```
</details>

<details><summary><b>Constraints</b></summary>

Constraint file: [`constraint.json`](example-7/constraint.json)

**LLM-generated constraints**
```json
[
  [
    "left_of",
    "m1",
    "m2"
  ],
  [
    "left_of",
    "m3",
    "m4"
  ],
  [
    "below",
    "r1",
    "m1"
  ],
  [
    "left_of",
    "m4",
    "m15"
  ],
  [
    "left_of",
    "m5",
    "m1"
  ],
  [
    "left_of",
    "m9",
    "m1"
  ],
  [
    "column_proximity",
    2,
    "r1",
    "m1"
  ],
  [
    "column_proximity",
    2,
    "r1",
    "m2"
  ],
  [
    "same_row",
    "m1",
    "m2"
  ],
  [
    "same_row",
    "m3",
    "m4"
  ],
  [
    "same_column_above",
    "m3",
    "m1"
  ],
  [
    "same_column_above",
    "m4",
    "m2"
  ],
  [
    "same_column_above",
    "m15",
    "m16"
  ],
  [
    "same_row",
    "m5",
    "m6"
  ],
  [
    "same_row",
    "m6",
    "m10"
  ],
  [
    "same_column_above",
    "m7",
    "m6"
  ],
  [
    "same_column_above",
    "m8",
    "m9"
  ],
  [
    "same_column_above",
    "m12",
    "m11"
  ],
  [
    "same_column_above",
    "m13",
    "m14"
  ],
  [
    "same_row",
    "terminal_in1",
    "m1"
  ],
  [
    "left_of",
    "terminal_in1",
    "m1"
  ],
  [
    "column_proximity",
    2,
    "terminal_in1",
    "m1"
  ],
  [
    "same_row",
    "terminal_in2",
    "m2"
  ],
  [
    "right_of",
    "terminal_in2",
    "m2"
  ],
  [
    "column_proximity",
    2,
    "terminal_in2",
    "m2"
  ]
]
```

**Orientation constraints**
```json
{
  "m1": 1,
  "m2": 0
}
```

**Path-based constraints**
```
CONSTRAINT_1_SHARE_DRAIN_SOURCE_CONNECTION
CONSTRAINT_2_SORT_VDD_GND_TRACABILITY
CONSTRAINT_3_SHARE_GATE_TO_GATE_CONNECTION
CONSTRAINT_6_PLACE_VDD_DIFFERENT_COLUMN
CONSTRAINT_7_DONT_PLACE_TOO_CLOSE_TO_BOUNDARIES
CONSTRAINT_8_PLACE_CAPACITORS_MIDDLE
CONSTRAINT_10_PLACE_OUTPUT_PORTS_RIGHT
CONSTRAINT_11_PLACE_BIASING_PORTS_LEFT
CONSTRAINT_12_PLACE_VDD_PORTS_TOP_RIGHT
CONSTRAINT_4_SHARE_SOURCE_TO_SOURCE_CONNECTION
CONSTRAINT_5_PLACE_SEPARATELY_2
```

**Terminals**: `ibias`, `in1`, `in2`, `out`, `vdd!`, `gnd!`

</details>

---

### example-8 — Two-stage fully-differential MOS op-amp

Single netlist + single constraint set.

**Metrics** — devices: 17 · bends: **20** · crossings: **6** · HPWL: **103** · routing cost: 10650

![example-8 schematic](example-8/docgen/schematic_result_0_10650_20_6_103.png)

<details><summary><b>Netlist</b> — <code>example-8/netlist.ckt</code> (17 components)</summary>

```spice
m1 net1 in1 net2 net2 pmos
m2 net3 in2 net2 net2 pmos
r1 net1 gnd!
r2 net3 gnd!
m3 net4 net4 vdd! vdd! pmos
m4 net2 net4 vdd! vdd! pmos
m5 ibias ibias gnd! gnd! nmos
m6 net5 ibias gnd! gnd! nmos
m7 net5 net5 vdd! vdd! pmos
m8 net4 ibias gnd! gnd! nmos
c1 net3 outp
r3 net1 net6
c2 net6 outn
m9 outp net3 gnd! gnd! nmos
m10 outp net5 vdd! vdd! pmos
m11 outn net1 gnd! gnd! nmos
m12 outn net5 vdd! vdd! pmos
```
</details>

<details><summary><b>Constraints</b></summary>

Constraint file: [`constraint.json`](example-8/constraint.json)

**LLM-generated constraints**
```json
[
  [
    "left_of",
    "m1",
    "m2"
  ],
  [
    "left_of",
    "m3",
    "m4"
  ],
  [
    "left_of",
    "r1",
    "r2"
  ],
  [
    "above",
    "m4",
    "m1"
  ],
  [
    "above",
    "m4",
    "m2"
  ],
  [
    "left_of",
    "m2",
    "m9"
  ],
  [
    "left_of",
    "m2",
    "m11"
  ],
  [
    "left_of",
    "m5",
    "m1"
  ],
  [
    "column_proximity",
    3,
    "m4",
    "m2"
  ],
  [
    "same_row",
    "m1",
    "m2"
  ],
  [
    "same_row",
    "m3",
    "m4"
  ],
  [
    "same_row",
    "m9",
    "m11"
  ],
  [
    "same_row",
    "m10",
    "m12"
  ],
  [
    "same_row",
    "m5",
    "m6"
  ],
  [
    "same_row",
    "m6",
    "m8"
  ],
  [
    "same_column_above",
    "m1",
    "r1"
  ],
  [
    "same_column_above",
    "m2",
    "r2"
  ],
  [
    "same_column_above",
    "m10",
    "m9"
  ],
  [
    "same_column_above",
    "m12",
    "m11"
  ],
  [
    "same_column_above",
    "m7",
    "m6"
  ],
  [
    "same_row",
    "terminal_in1",
    "m1"
  ],
  [
    "left_of",
    "terminal_in1",
    "m1"
  ],
  [
    "column_proximity",
    2,
    "terminal_in1",
    "m1"
  ],
  [
    "same_row",
    "terminal_in2",
    "m2"
  ],
  [
    "right_of",
    "terminal_in2",
    "m2"
  ],
  [
    "column_proximity",
    2,
    "terminal_in2",
    "m2"
  ]
]
```

**Orientation constraints**
```json
{
  "m1": 1,
  "m2": 0
}
```

**Path-based constraints**
```
CONSTRAINT_1_SHARE_DRAIN_SOURCE_CONNECTION
CONSTRAINT_2_SORT_VDD_GND_TRACABILITY
CONSTRAINT_3_SHARE_GATE_TO_GATE_CONNECTION
CONSTRAINT_6_PLACE_VDD_DIFFERENT_COLUMN
CONSTRAINT_7_DONT_PLACE_TOO_CLOSE_TO_BOUNDARIES
CONSTRAINT_8_PLACE_CAPACITORS_MIDDLE
CONSTRAINT_10_PLACE_OUTPUT_PORTS_RIGHT
CONSTRAINT_11_PLACE_BIASING_PORTS_LEFT
CONSTRAINT_12_PLACE_VDD_PORTS_TOP_RIGHT
CONSTRAINT_4_SHARE_SOURCE_TO_SOURCE_CONNECTION
CONSTRAINT_5_PLACE_SEPARATELY_2
```

**Terminals**: `ibias`, `in1`, `in2`, `outp`, `outn`, `vdd!`, `gnd!`

</details>

---

### example-9 — Two-stage single-ended MOS op-amp

Single netlist + single constraint set.

**Metrics** — devices: 19 · bends: **16** · crossings: **8** · HPWL: **103** · routing cost: 6307

![example-9 schematic](example-9/docgen/schematic_result_0_6307_16_8_103.png)

<details><summary><b>Netlist</b> — <code>example-9/netlist.ckt</code> (19 components)</summary>

```spice
m1 net1 in1 net2 net2 nmos
m2 net3 in2 net2 net2 nmos
m3 net1 net1 vdd! vdd! pmos
m4 net3 net1 vdd! vdd! pmos
r1 net2 gnd!
m5 ibias ibias gnd! gnd! nmos
m6 net4 ibias gnd! gnd! nmos
m7 net4 net4 vdd! vdd! pmos
m8 net5 ibias gnd! gnd! nmos
m9 net5 net5 vdd! vdd! pmos
m10 net6 net3 vdd! vdd! pmos
m11 net7 net6 gnd! gnd! nmos
m12 net6 net6 gnd! gnd! nmos
m13 net7 net4 vdd! vdd! pmos
m14 out net7 gnd! gnd! nmos
m15 out net5 vdd! vdd! pmos
c1 net3 out
r2 net7 net8
c2 net8 out
```
</details>

<details><summary><b>Constraints</b></summary>

Constraint file: [`constraint.json`](example-9/constraint.json)

**LLM-generated constraints**
```json
[
  [
    "left_of",
    "m1",
    "m2"
  ],
  [
    "left_of",
    "m3",
    "m4"
  ],
  [
    "below",
    "r1",
    "m1"
  ],
  [
    "left_of",
    "m4",
    "m10"
  ],
  [
    "left_of",
    "m12",
    "m11"
  ],
  [
    "left_of",
    "m11",
    "m14"
  ],
  [
    "left_of",
    "m5",
    "m1"
  ],
  [
    "column_proximity",
    2,
    "r1",
    "m1"
  ],
  [
    "column_proximity",
    2,
    "r1",
    "m2"
  ],
  [
    "same_row",
    "m1",
    "m2"
  ],
  [
    "same_row",
    "m3",
    "m4"
  ],
  [
    "same_row",
    "m11",
    "m12"
  ],
  [
    "same_row",
    "m5",
    "m6"
  ],
  [
    "same_row",
    "m6",
    "m8"
  ],
  [
    "same_column_above",
    "m3",
    "m1"
  ],
  [
    "same_column_above",
    "m4",
    "m2"
  ],
  [
    "same_column_above",
    "m10",
    "m12"
  ],
  [
    "same_column_above",
    "m13",
    "m11"
  ],
  [
    "same_column_above",
    "m15",
    "m14"
  ],
  [
    "same_column_above",
    "m7",
    "m6"
  ],
  [
    "same_column_above",
    "m9",
    "m8"
  ],
  [
    "same_row",
    "terminal_in1",
    "m1"
  ],
  [
    "left_of",
    "terminal_in1",
    "m1"
  ],
  [
    "column_proximity",
    2,
    "terminal_in1",
    "m1"
  ],
  [
    "same_row",
    "terminal_in2",
    "m2"
  ],
  [
    "right_of",
    "terminal_in2",
    "m2"
  ],
  [
    "column_proximity",
    2,
    "terminal_in2",
    "m2"
  ]
]
```

**Orientation constraints**
```json
{
  "m1": 1,
  "m2": 0
}
```

**Path-based constraints**
```
CONSTRAINT_1_SHARE_DRAIN_SOURCE_CONNECTION
CONSTRAINT_2_SORT_VDD_GND_TRACABILITY
CONSTRAINT_3_SHARE_GATE_TO_GATE_CONNECTION
CONSTRAINT_6_PLACE_VDD_DIFFERENT_COLUMN
CONSTRAINT_7_DONT_PLACE_TOO_CLOSE_TO_BOUNDARIES
CONSTRAINT_8_PLACE_CAPACITORS_MIDDLE
CONSTRAINT_10_PLACE_OUTPUT_PORTS_RIGHT
CONSTRAINT_11_PLACE_BIASING_PORTS_LEFT
CONSTRAINT_12_PLACE_VDD_PORTS_TOP_RIGHT
CONSTRAINT_4_SHARE_SOURCE_TO_SOURCE_CONNECTION
CONSTRAINT_5_PLACE_SEPARATELY_2
```

**Terminals**: `ibias`, `in1`, `in2`, `out`, `vdd!`, `gnd!`

</details>

---

### example-10 — Two-stage fully-differential MOS op-amp with CMFB

Largest example.

**Metrics** — devices: 44 · bends: **75** · crossings: **64** · HPWL: **317** · routing cost: 52313

![example-10 schematic](example-10/docgen/schematic_result_0_52313_75_64_317.png)

<details><summary><b>Netlist</b> — <code>example-10/netlist.ckt</code> (44 components)</summary>

```spice
m1 net1 in1 net2 net2 pmos
m2 net3 in2 net2 net2 pmos
m3 net1 net4 gnd! gnd! nmos
m4 net3 net4 gnd! gnd! nmos
m5 net5 net5 vdd! vdd! pmos
m6 net2 net5 vdd! vdd! pmos
m7 ibias ibias gnd! gnd! nmos
m8 net6 ibias gnd! gnd! nmos
m9 net6 net6 vdd! vdd! pmos
m10 net7 net6 vdd! vdd! pmos
m11 net7 net7 gnd! gnd! nmos
m12 net8 ibias gnd! gnd! nmos
m13 net9 net7 net8 gnd! nmos
m14 net9 net9 vdd! vdd! pmos
m15 net10 net9 vdd! vdd! pmos
m16 net10 net10 gnd! gnd! nmos
m17 net11 net9 vdd! vdd! pmos
m18 net11 net11 gnd! gnd! nmos
m19 net12 ibias gnd! gnd! nmos
m20 net12 net12 vdd! vdd! pmos
m21 net5 ibias gnd! gnd! nmos
r1 outp net13
r2 outn net13
m22 net14 vcm_ref net15 gnd! nmos
m23 net4 net13 net15 gnd! nmos
m24 net14 net14 vdd! vdd! pmos
m25 net4 net14 vdd! vdd! pmos
m26 net15 net10 gnd! gnd! nmos
m27 net16 net3 gnd! gnd! nmos
m28 net17 net16 vdd! vdd! pmos
m29 net16 net16 vdd! vdd! pmos
m30 net17 net11 gnd! gnd! nmos
m31 outp net17 gnd! gnd! nmos
m32 outp net12 vdd! vdd! pmos
c1 net3 outp
c2 net17 outp
m33 net18 net1 gnd! gnd! nmos
m34 net19 net18 vdd! vdd! pmos
m35 net18 net18 vdd! vdd! pmos
m36 net19 net11 gnd! gnd! nmos
m37 outn net19 gnd! gnd! nmos
m38 outn net12 vdd! vdd! pmos
c3 net1 outn
c4 net19 outn
```
</details>

<details><summary><b>Constraints</b></summary>

Constraint file: [`constraint.json`](example-10/constraint.json)

**LLM-generated constraints**
```json
[
  [
    "left_of",
    "m1",
    "m2"
  ],
  [
    "left_of",
    "m3",
    "m4"
  ],
  [
    "above",
    "m6",
    "m1"
  ],
  [
    "above",
    "m6",
    "m2"
  ],
  [
    "left_of",
    "m5",
    "m6"
  ],
  [
    "column_proximity",
    3,
    "m6",
    "m2"
  ],
  [
    "left_of",
    "m4",
    "m27"
  ],
  [
    "left_of",
    "m29",
    "m28"
  ],
  [
    "left_of",
    "m28",
    "m31"
  ],
  [
    "left_of",
    "m4",
    "m33"
  ],
  [
    "left_of",
    "m35",
    "m34"
  ],
  [
    "left_of",
    "m34",
    "m37"
  ],
  [
    "left_of",
    "m7",
    "m1"
  ],
  [
    "left_of",
    "m22",
    "m23"
  ],
  [
    "below",
    "m26",
    "m22"
  ],
  [
    "column_proximity",
    2,
    "m26",
    "m22"
  ],
  [
    "same_row",
    "m1",
    "m2"
  ],
  [
    "same_row",
    "m3",
    "m4"
  ],
  [
    "same_row",
    "m5",
    "m6"
  ],
  [
    "same_column_above",
    "m1",
    "m3"
  ],
  [
    "same_column_above",
    "m2",
    "m4"
  ],
  [
    "same_row",
    "m28",
    "m29"
  ],
  [
    "same_column_above",
    "m29",
    "m27"
  ],
  [
    "same_column_above",
    "m28",
    "m30"
  ],
  [
    "same_row",
    "m34",
    "m35"
  ],
  [
    "same_column_above",
    "m35",
    "m33"
  ],
  [
    "same_column_above",
    "m34",
    "m36"
  ],
  [
    "same_column_above",
    "m32",
    "m31"
  ],
  [
    "same_column_above",
    "m38",
    "m37"
  ],
  [
    "same_row",
    "m27",
    "m33"
  ],
  [
    "same_row",
    "m28",
    "m34"
  ],
  [
    "same_row",
    "m31",
    "m37"
  ],
  [
    "same_row",
    "m32",
    "m38"
  ],
  [
    "same_row",
    "m24",
    "m25"
  ],
  [
    "same_column_above",
    "m24",
    "m22"
  ],
  [
    "same_column_above",
    "m25",
    "m23"
  ],
  [
    "same_column_above",
    "m9",
    "m8"
  ],
  [
    "same_column_above",
    "m10",
    "m11"
  ],
  [
    "same_column_above",
    "m14",
    "m13"
  ],
  [
    "same_column_above",
    "m15",
    "m16"
  ],
  [
    "same_column_above",
    "m17",
    "m18"
  ],
  [
    "same_column_above",
    "m20",
    "m19"
  ],
  [
    "same_row",
    "m7",
    "m8"
  ],
  [
    "same_row",
    "m8",
    "m12"
  ],
  [
    "same_row",
    "terminal_in1",
    "m1"
  ],
  [
    "left_of",
    "terminal_in1",
    "m1"
  ],
  [
    "column_proximity",
    2,
    "terminal_in1",
    "m1"
  ],
  [
    "same_row",
    "terminal_in2",
    "m2"
  ],
  [
    "right_of",
    "terminal_in2",
    "m2"
  ],
  [
    "column_proximity",
    2,
    "terminal_in2",
    "m2"
  ]
]
```

**Orientation constraints**
```json
{
  "m1": 1,
  "m2": 0
}
```

**Path-based constraints**
```
CONSTRAINT_1_SHARE_DRAIN_SOURCE_CONNECTION
CONSTRAINT_2_SORT_VDD_GND_TRACABILITY
CONSTRAINT_3_SHARE_GATE_TO_GATE_CONNECTION
CONSTRAINT_6_PLACE_VDD_DIFFERENT_COLUMN
CONSTRAINT_7_DONT_PLACE_TOO_CLOSE_TO_BOUNDARIES
CONSTRAINT_8_PLACE_CAPACITORS_MIDDLE
CONSTRAINT_10_PLACE_OUTPUT_PORTS_RIGHT
CONSTRAINT_11_PLACE_BIASING_PORTS_LEFT
CONSTRAINT_12_PLACE_VDD_PORTS_TOP_RIGHT
CONSTRAINT_4_SHARE_SOURCE_TO_SOURCE_CONNECTION
CONSTRAINT_5_PLACE_SEPARATELY_2
```

**Terminals**: `ibias`, `vcm_ref`, `in1`, `in2`, `outp`, `outn`, `vdd!`, `gnd!`

</details>

---

### example-11 — Two-stage single-ended MOS op-amp

Single netlist + single constraint set.

**Metrics** — devices: 25 · bends: **20** · crossings: **7** · HPWL: **140** · routing cost: 10607

![example-11 schematic](example-11/docgen/schematic_result_0_10607_20_7_140.png)

<details><summary><b>Netlist</b> — <code>example-11/netlist.ckt</code> (25 components)</summary>

```spice
m1 net1 in1 net2 net2 nmos
m2 net3 in2 net2 net2 nmos
m3 net1 net1 vdd! vdd! pmos
m4 net3 net1 vdd! vdd! pmos
r1 net2 gnd!
m5 ibias ibias gnd! gnd! nmos
m6 net4 ibias gnd! gnd! nmos
m7 net4 net4 vdd! vdd! pmos
m8 net5 net4 vdd! vdd! pmos
m9 net5 net5 gnd! gnd! nmos
m10 net6 ibias gnd! gnd! nmos
m11 net7 net5 net6 gnd! nmos
m12 net7 net7 vdd! vdd! pmos
m13 net8 net7 vdd! vdd! pmos
m14 net8 net8 gnd! gnd! nmos
m15 net9 net7 vdd! vdd! pmos
m16 net9 net9 gnd! gnd! nmos
m17 net10 net3 vdd! vdd! pmos
m18 net10 net8 gnd! gnd! nmos
m19 out net10 vdd! vdd! pmos
m20 out net9 gnd! gnd! nmos
r2 net10 net11
c1 net11 out
c2 net3 net12
r3 net12 net10
```
</details>

<details><summary><b>Constraints</b></summary>

Constraint file: [`constraint.json`](example-11/constraint.json)

**LLM-generated constraints**
```json
[
  [
    "left_of",
    "m1",
    "m2"
  ],
  [
    "left_of",
    "m3",
    "m4"
  ],
  [
    "below",
    "r1",
    "m1"
  ],
  [
    "left_of",
    "m4",
    "m17"
  ],
  [
    "left_of",
    "m17",
    "m19"
  ],
  [
    "left_of",
    "m5",
    "m1"
  ],
  [
    "column_proximity",
    2,
    "r1",
    "m1"
  ],
  [
    "column_proximity",
    2,
    "r1",
    "m2"
  ],
  [
    "same_row",
    "m1",
    "m2"
  ],
  [
    "same_row",
    "m3",
    "m4"
  ],
  [
    "same_row",
    "m5",
    "m6"
  ],
  [
    "same_row",
    "m6",
    "m10"
  ],
  [
    "same_column_above",
    "m3",
    "m1"
  ],
  [
    "same_column_above",
    "m4",
    "m2"
  ],
  [
    "same_column_above",
    "m17",
    "m18"
  ],
  [
    "same_column_above",
    "m19",
    "m20"
  ],
  [
    "same_column_above",
    "m7",
    "m6"
  ],
  [
    "same_column_above",
    "m8",
    "m9"
  ],
  [
    "same_column_above",
    "m12",
    "m11"
  ],
  [
    "same_column_above",
    "m13",
    "m14"
  ],
  [
    "same_column_above",
    "m15",
    "m16"
  ],
  [
    "same_row",
    "terminal_in1",
    "m1"
  ],
  [
    "left_of",
    "terminal_in1",
    "m1"
  ],
  [
    "column_proximity",
    2,
    "terminal_in1",
    "m1"
  ],
  [
    "same_row",
    "terminal_in2",
    "m2"
  ],
  [
    "right_of",
    "terminal_in2",
    "m2"
  ],
  [
    "column_proximity",
    2,
    "terminal_in2",
    "m2"
  ]
]
```

**Orientation constraints**
```json
{
  "m1": 1,
  "m2": 0
}
```

**Path-based constraints**
```
CONSTRAINT_1_SHARE_DRAIN_SOURCE_CONNECTION
CONSTRAINT_2_SORT_VDD_GND_TRACABILITY
CONSTRAINT_3_SHARE_GATE_TO_GATE_CONNECTION
CONSTRAINT_6_PLACE_VDD_DIFFERENT_COLUMN
CONSTRAINT_7_DONT_PLACE_TOO_CLOSE_TO_BOUNDARIES
CONSTRAINT_8_PLACE_CAPACITORS_MIDDLE
CONSTRAINT_10_PLACE_OUTPUT_PORTS_RIGHT
CONSTRAINT_11_PLACE_BIASING_PORTS_LEFT
CONSTRAINT_12_PLACE_VDD_PORTS_TOP_RIGHT
CONSTRAINT_4_SHARE_SOURCE_TO_SOURCE_CONNECTION
CONSTRAINT_5_PLACE_SEPARATELY_2
```

**Terminals**: `ibias`, `in1`, `in2`, `out`, `vdd!`, `gnd!`

</details>

---

### example-12 — Three-stage NMC single-ended MOS op-amp

Nested-Miller-compensated (NMC) three-stage single-ended op-amp synthesized with CircuitGenome (`three_stage_opamp_nmc_single_ended`). Baseline path-based constraints only.

**Metrics** — devices: 27 · bends: **34** · crossings: **19** · HPWL: **137** · routing cost: 19713

![example-12 schematic](example-12/docgen/schematic_result_0_19713_34_19_137.png)

<details><summary><b>Netlist</b> — <code>example-12/netlist.ckt</code> (27 components)</summary>

```spice
m1 net_diff1 in1 net_tail net_tail pmos
m2 net_mid1 in2 net_tail net_tail pmos
r1 net_diff1 gnd!
r2 net_mid1 gnd!
m3 net_bias7 net_bias7 vdd! vdd! pmos
m4 net_tail net_bias7 vdd! vdd! pmos
m5 ibias ibias gnd! gnd! nmos
m6 bias_gen_feed_pref ibias gnd! gnd! nmos
m7 bias_gen_feed_pref bias_gen_feed_pref vdd! vdd! pmos
m8 bias_gen_ncasc bias_gen_feed_pref vdd! vdd! pmos
m9 bias_gen_ncasc bias_gen_ncasc gnd! gnd! nmos
m10 bias_gen_prefsrc ibias gnd! gnd! nmos
m11 bias_gen_pref bias_gen_ncasc bias_gen_prefsrc gnd! nmos
m12 bias_gen_pref bias_gen_pref vdd! vdd! pmos
m13 net_bias5 bias_gen_pref vdd! vdd! pmos
m14 net_bias5 net_bias5 gnd! gnd! nmos
m15 net_bias6 ibias gnd! gnd! nmos
m16 net_bias6 net_bias6 vdd! vdd! pmos
m17 net_bias7 ibias gnd! gnd! nmos
m18 second_stage_nmir net_mid1 gnd! gnd! nmos
m19 net_mid2 second_stage_nmir vdd! vdd! pmos
m20 second_stage_nmir second_stage_nmir vdd! vdd! pmos
m21 net_mid2 net_bias5 gnd! gnd! nmos
m22 out net_mid2 gnd! gnd! nmos
m23 out net_bias6 vdd! vdd! pmos
c1 net_mid1 out
c2 net_mid2 out
```
</details>

<details><summary><b>Constraints</b></summary>

Constraint file: [`constraint.json`](example-12/constraint.json)

**Path-based constraints**
```
CONSTRAINT_1_SHARE_DRAIN_SOURCE_CONNECTION
CONSTRAINT_2_SORT_VDD_GND_TRACABILITY
CONSTRAINT_3_SHARE_GATE_TO_GATE_CONNECTION
CONSTRAINT_6_PLACE_VDD_DIFFERENT_COLUMN
CONSTRAINT_7_DONT_PLACE_TOO_CLOSE_TO_BOUNDARIES
CONSTRAINT_8_PLACE_CAPACITORS_MIDDLE
CONSTRAINT_9_PLACE_INPUT_PORTS_LEFT
CONSTRAINT_10_PLACE_OUTPUT_PORTS_RIGHT
CONSTRAINT_11_PLACE_BIASING_PORTS_LEFT
CONSTRAINT_12_PLACE_VDD_PORTS_TOP_RIGHT
CONSTRAINT_4_SHARE_SOURCE_TO_SOURCE_CONNECTION
CONSTRAINT_5_PLACE_SEPARATELY_2
```

**Terminals**: `ibias`, `in1`, `in2`, `out`, `vdd!`, `gnd!`

</details>

---

### example-13 — Three-stage RNMC single-ended MOS op-amp

Reversed-nested-Miller-compensated (RNMC) three-stage single-ended op-amp from CircuitGenome (`three_stage_opamp_rnmc_single_ended`). Baseline path-based constraints only.

**Metrics** — devices: 18 · bends: **22** · crossings: **8** · HPWL: **80** · routing cost: 15144

![example-13 schematic](example-13/docgen/schematic_result_0_15144_22_8_80.png)

<details><summary><b>Netlist</b> — <code>example-13/netlist.ckt</code> (18 components)</summary>

```spice
m1 net_diff1 in1 net_tail net_tail pmos
m2 net_mid1 in2 net_tail net_tail pmos
r1 net_diff1 gnd!
r2 net_mid1 gnd!
m3 net_bias7 net_bias7 vdd! vdd! pmos
m4 net_tail net_bias7 vdd! vdd! pmos
m5 ibias ibias gnd! gnd! nmos
m6 net_bias5 ibias gnd! gnd! nmos
m7 net_bias5 net_bias5 vdd! vdd! pmos
m8 net_bias6 ibias gnd! gnd! nmos
m9 net_bias6 net_bias6 vdd! vdd! pmos
m10 net_bias7 ibias gnd! gnd! nmos
m11 net_mid2 net_mid1 gnd! gnd! nmos
m12 net_mid2 net_bias5 vdd! vdd! pmos
m13 out net_mid2 gnd! gnd! nmos
m14 out net_bias6 vdd! vdd! pmos
c1 net_mid2 out
c2 net_mid1 net_mid2
```
</details>

<details><summary><b>Constraints</b></summary>

Constraint file: [`constraint.json`](example-13/constraint.json)

**Path-based constraints**
```
CONSTRAINT_1_SHARE_DRAIN_SOURCE_CONNECTION
CONSTRAINT_2_SORT_VDD_GND_TRACABILITY
CONSTRAINT_3_SHARE_GATE_TO_GATE_CONNECTION
CONSTRAINT_6_PLACE_VDD_DIFFERENT_COLUMN
CONSTRAINT_7_DONT_PLACE_TOO_CLOSE_TO_BOUNDARIES
CONSTRAINT_8_PLACE_CAPACITORS_MIDDLE
CONSTRAINT_9_PLACE_INPUT_PORTS_LEFT
CONSTRAINT_10_PLACE_OUTPUT_PORTS_RIGHT
CONSTRAINT_11_PLACE_BIASING_PORTS_LEFT
CONSTRAINT_12_PLACE_VDD_PORTS_TOP_RIGHT
CONSTRAINT_4_SHARE_SOURCE_TO_SOURCE_CONNECTION
CONSTRAINT_5_PLACE_SEPARATELY_2
```

**Terminals**: `ibias`, `in1`, `in2`, `out`, `vdd!`, `gnd!`

</details>

---

### example-14 — Three-stage NMC fully-differential MOS op-amp

Nested-Miller-compensated (NMC) three-stage fully-differential op-amp (`outp`/`outn`) from CircuitGenome (`three_stage_opamp_nmc_fully_differential`). Baseline path-based constraints only.

**Metrics** — devices: 35 · bends: **56** · crossings: **46** · HPWL: **277** · routing cost: 41179

![example-14 schematic](example-14/docgen/schematic_result_0_41179_56_46_277.png)

<details><summary><b>Netlist</b> — <code>example-14/netlist.ckt</code> (35 components)</summary>

```spice
m1 net_loadout1 in1 net_tail net_tail pmos
m2 net_loadout2 in2 net_tail net_tail pmos
r1 net_loadout1 gnd!
r2 net_loadout2 gnd!
m3 net_bias7 net_bias7 vdd! vdd! pmos
m4 net_tail net_bias7 vdd! vdd! pmos
m5 ibias ibias gnd! gnd! nmos
m6 bias_gen_feed_pref ibias gnd! gnd! nmos
m7 bias_gen_feed_pref bias_gen_feed_pref vdd! vdd! pmos
m8 bias_gen_ncasc bias_gen_feed_pref vdd! vdd! pmos
m9 bias_gen_ncasc bias_gen_ncasc gnd! gnd! nmos
m10 bias_gen_prefsrc ibias gnd! gnd! nmos
m11 bias_gen_pref bias_gen_ncasc bias_gen_prefsrc gnd! nmos
m12 bias_gen_pref bias_gen_pref vdd! vdd! pmos
m13 net_bias5 bias_gen_pref vdd! vdd! pmos
m14 net_bias5 net_bias5 gnd! gnd! nmos
m15 net_bias6 ibias gnd! gnd! nmos
m16 net_bias6 net_bias6 vdd! vdd! pmos
m17 net_bias7 ibias gnd! gnd! nmos
m18 second_stage_p_nmir net_loadout2 gnd! gnd! nmos
m19 net_mid2_p second_stage_p_nmir vdd! vdd! pmos
m20 second_stage_p_nmir second_stage_p_nmir vdd! vdd! pmos
m21 net_mid2_p net_bias5 gnd! gnd! nmos
m22 outp net_mid2_p gnd! gnd! nmos
m23 outp net_bias6 vdd! vdd! pmos
c1 net_loadout2 outp
c2 net_mid2_p outp
m24 second_stage_n_nmir net_loadout1 gnd! gnd! nmos
m25 net_mid2_n second_stage_n_nmir vdd! vdd! pmos
m26 second_stage_n_nmir second_stage_n_nmir vdd! vdd! pmos
m27 net_mid2_n net_bias5 gnd! gnd! nmos
m28 outn net_mid2_n gnd! gnd! nmos
m29 outn net_bias6 vdd! vdd! pmos
c3 net_loadout1 outn
c4 net_mid2_n outn
```
</details>

<details><summary><b>Constraints</b></summary>

Constraint file: [`constraint.json`](example-14/constraint.json)

**Path-based constraints**
```
CONSTRAINT_1_SHARE_DRAIN_SOURCE_CONNECTION
CONSTRAINT_2_SORT_VDD_GND_TRACABILITY
CONSTRAINT_3_SHARE_GATE_TO_GATE_CONNECTION
CONSTRAINT_6_PLACE_VDD_DIFFERENT_COLUMN
CONSTRAINT_7_DONT_PLACE_TOO_CLOSE_TO_BOUNDARIES
CONSTRAINT_8_PLACE_CAPACITORS_MIDDLE
CONSTRAINT_9_PLACE_INPUT_PORTS_LEFT
CONSTRAINT_10_PLACE_OUTPUT_PORTS_RIGHT
CONSTRAINT_11_PLACE_BIASING_PORTS_LEFT
CONSTRAINT_12_PLACE_VDD_PORTS_TOP_RIGHT
CONSTRAINT_4_SHARE_SOURCE_TO_SOURCE_CONNECTION
CONSTRAINT_5_PLACE_SEPARATELY_2
```

**Terminals**: `ibias`, `in1`, `in2`, `outp`, `outn`, `vdd!`, `gnd!`

</details>

---

### example-15 — Three-stage RNMC fully-differential MOS op-amp

Reversed-nested-Miller-compensated (RNMC) three-stage fully-differential op-amp from CircuitGenome (`three_stage_opamp_rnmc_fully_differential`). Baseline path-based constraints only.

**Metrics** — devices: 24 · bends: **35** · crossings: **16** · HPWL: **142** · routing cost: 21901

![example-15 schematic](example-15/docgen/schematic_result_0_21901_35_16_142.png)

<details><summary><b>Netlist</b> — <code>example-15/netlist.ckt</code> (24 components)</summary>

```spice
m1 net_loadout1 in1 net_tail net_tail pmos
m2 net_loadout2 in2 net_tail net_tail pmos
r1 net_loadout1 gnd!
r2 net_loadout2 gnd!
m3 net_bias7 net_bias7 vdd! vdd! pmos
m4 net_tail net_bias7 vdd! vdd! pmos
m5 ibias ibias gnd! gnd! nmos
m6 net_bias5 ibias gnd! gnd! nmos
m7 net_bias5 net_bias5 vdd! vdd! pmos
m8 net_bias6 ibias gnd! gnd! nmos
m9 net_bias6 net_bias6 vdd! vdd! pmos
m10 net_bias7 ibias gnd! gnd! nmos
m11 net_mid2_p net_loadout2 gnd! gnd! nmos
m12 net_mid2_p net_bias5 vdd! vdd! pmos
m13 outp net_mid2_p gnd! gnd! nmos
m14 outp net_bias6 vdd! vdd! pmos
c1 net_mid2_p outp
c2 net_loadout2 net_mid2_p
m15 net_mid2_n net_loadout1 gnd! gnd! nmos
m16 net_mid2_n net_bias5 vdd! vdd! pmos
m17 outn net_mid2_n gnd! gnd! nmos
m18 outn net_bias6 vdd! vdd! pmos
c3 net_mid2_n outn
c4 net_loadout1 net_mid2_n
```
</details>

<details><summary><b>Constraints</b></summary>

Constraint file: [`constraint.json`](example-15/constraint.json)

**Path-based constraints**
```
CONSTRAINT_1_SHARE_DRAIN_SOURCE_CONNECTION
CONSTRAINT_2_SORT_VDD_GND_TRACABILITY
CONSTRAINT_3_SHARE_GATE_TO_GATE_CONNECTION
CONSTRAINT_6_PLACE_VDD_DIFFERENT_COLUMN
CONSTRAINT_7_DONT_PLACE_TOO_CLOSE_TO_BOUNDARIES
CONSTRAINT_8_PLACE_CAPACITORS_MIDDLE
CONSTRAINT_9_PLACE_INPUT_PORTS_LEFT
CONSTRAINT_10_PLACE_OUTPUT_PORTS_RIGHT
CONSTRAINT_11_PLACE_BIASING_PORTS_LEFT
CONSTRAINT_12_PLACE_VDD_PORTS_TOP_RIGHT
CONSTRAINT_4_SHARE_SOURCE_TO_SOURCE_CONNECTION
CONSTRAINT_5_PLACE_SEPARATELY_2
```

**Terminals**: `ibias`, `in1`, `in2`, `outp`, `outn`, `vdd!`, `gnd!`

</details>

