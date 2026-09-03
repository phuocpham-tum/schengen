from ortools.sat.python import cp_model

import src.constraints.placement as pc
from src.schengen import Component, SchematicGenerator


# Representative args (constraint[1:]) for every registered primitive.
SAMPLE_ARGS = {
    "right_of": ["t1", "t2"],
    "left_of": ["t1", "t2"],
    "above": ["t1", "t2"],
    "below": ["t1", "t2"],
    "row_proximity": [5, "t1", "t2"],
    "column_proximity": [5, "t1", "t2"],
    "close_row": ["t1", "t2", 5],
    "cluster_proximity": [7, "t1", "t2", "t3"],
    "above_all": [1, "t1"],
    "below_all": [1, "t1"],
    "middle_all": ["t1"],
    "same_row": ["t1", "t2"],
    "same_column": ["t1", "t2"],
    "same_column_above": ["t1", "t2"],
    "same_column_below": ["t1", "t2"],
    "between_columns": ["t1", "t2", "t3"],
    "between_rows": ["t1", "t2", "t3"],
    "clear_row_between": ["t1", "t2"],
    "clear_column_between": ["t1", "t2"],
    "t_junction": ["t1", "t2", "t3"],
}


def _fresh_schematic():
    s = SchematicGenerator(num_rows=12, num_cols=12)
    for name in ["t1", "t2", "t3", "t4"]:
        s.add_component(Component(name=name, comp_type="nmos"))
    s.initial_cp_model()
    return s


def test_every_primitive_has_sample_args():
    # Guards against adding a registry entry without covering it here.
    assert set(SAMPLE_ARGS) == set(pc.PRIMITIVE_REGISTRY)


def test_each_primitive_applies_and_is_feasible():
    for name, args in SAMPLE_ARGS.items():
        s = _fresh_schematic()
        primitive = pc.PRIMITIVE_REGISTRY[name]

        # Declared component args must all be real components (never a numeric param).
        for comp_name in primitive.components(args):
            assert comp_name in s.comp_vars, f"{name}: {comp_name} not a component"

        primitive.apply(s, args)

        status = cp_model.CpSolver().Solve(s.model)
        assert status in (cp_model.OPTIMAL, cp_model.FEASIBLE), f"{name} infeasible"


def test_close_row_excludes_numeric_distance():
    # Regression: close_row's distance sits LAST (["close_row", A, B, D]); the old
    # positional decoder validated D as a component name and silently skipped it.
    args = ["t1", "t2", 5]
    assert pc.PRIMITIVE_REGISTRY["close_row"].components(args) == ["t1", "t2"]


def test_numeric_first_primitives_exclude_distance():
    for name in ["row_proximity", "column_proximity", "cluster_proximity"]:
        comps = pc.PRIMITIVE_REGISTRY[name].components(SAMPLE_ARGS[name])
        assert all(isinstance(c, str) for c in comps), name


def test_render_primitives_doc_lists_all():
    doc = pc.render_primitives_doc()
    for p in pc.PRIMITIVES:
        assert p.signature in doc


def test_prompt_primitives_filled_from_registry():
    from src.prompts import render_constraint_prompt

    prompt = render_constraint_prompt()
    # Placeholder is replaced, and the vocabulary comes from the registry.
    assert "{{CONSTRAINT_PRIMITIVES}}" not in prompt
    for p in pc.PRIMITIVES:
        assert p.signature in prompt


# ---- soft (penalty-based) LLM constraints ----


def _solve(s):
    solver = cp_model.CpSolver()
    status = solver.Solve(s.model)
    assert status in (cp_model.OPTIMAL, cp_model.FEASIBLE)
    return solver


def test_apply_soft_returns_false_for_unsupported():
    s = _fresh_schematic()
    # t_junction has no soft form.
    assert pc.apply_soft(s, "t_junction", ["t1", "t2", "t3"], 100) is False
    assert s._soft_penalties == []


def test_apply_soft_records_penalty_for_supported():
    s = _fresh_schematic()
    assert pc.apply_soft(s, "left_of", ["t1", "t2"], 100) is True
    assert len(s._soft_penalties) == 1
    weight, _ = s._soft_penalties[0]
    assert weight == 100


def test_soft_constraint_satisfied_when_feasible():
    # With nothing opposing it, a soft left_of should be satisfied (penalty bool = 1).
    s = _fresh_schematic()
    pc.apply_soft(s, "left_of", ["t1", "t2"], 100)
    weight, b = s._soft_penalties[0]
    s.model.Minimize(sum(w * (1 - bb) for w, bb in s._soft_penalties))
    solver = _solve(s)
    assert solver.Value(b) == 1
    assert solver.Value(s.comp_vars["t1"][1]) < solver.Value(s.comp_vars["t2"][1])


def test_soft_constraint_relaxes_under_conflict():
    # Hard: t1 right of t2. Soft: t1 left of t2. The soft one must relax (bool = 0),
    # and the model stays feasible instead of being infeasible.
    s = _fresh_schematic()
    pc.right_of(s, "t1", "t2")  # hard
    pc.apply_soft(s, "left_of", ["t1", "t2"], 100)  # soft, conflicting
    weight, b = s._soft_penalties[0]
    s.model.Minimize(sum(w * (1 - bb) for w, bb in s._soft_penalties))
    solver = _solve(s)
    assert solver.Value(b) == 0  # relaxed, not infeasible
    assert solver.Value(s.comp_vars["t1"][1]) > solver.Value(s.comp_vars["t2"][1])


def test_cluster_proximity_soft_form():
    # cluster_proximity is soft-supported: satisfiable, records one penalty bool
    # for the whole cluster, and holds when the members can sit close together.
    s = _fresh_schematic()
    assert pc.apply_soft(s, "cluster_proximity", [3, "t1", "t2", "t3"], 100) is True
    assert len(s._soft_penalties) == 1
    weight, b = s._soft_penalties[0]
    s.model.Minimize(sum(w * (1 - bb) for w, bb in s._soft_penalties))
    solver = _solve(s)
    assert solver.Value(b) == 1
    pos = {n: (solver.Value(s.comp_vars[n][0]), solver.Value(s.comp_vars[n][1])) for n in ["t1", "t2", "t3"]}
    for m1 in pos:
        for m2 in pos:
            assert abs(pos[m1][0] - pos[m2][0]) <= 3
            assert abs(pos[m1][1] - pos[m2][1]) <= 3


def test_t_junction_centers_target_and_uses_distinct_row():
    # target sits at the pair's centre column, the pair shares a row, and the
    # target drops into a distinct nearby row (the T stem).
    s = _fresh_schematic()
    pc.T_junction(s, "t1", "t2", "t3")
    solver = _solve(s)
    r1, c1 = (solver.Value(v) for v in s.comp_vars["t1"])
    r2, c2 = (solver.Value(v) for v in s.comp_vars["t2"])
    r3, c3 = (solver.Value(v) for v in s.comp_vars["t3"])
    assert r2 == r3                       # crossbar shares a row
    assert abs(2 * c1 - (c2 + c3)) <= 1   # target at the rounded midpoint
    assert 1 <= abs(r1 - r2) <= 5         # stem in a distinct, nearby row


def test_t_junction_robust_to_adjacent_pair_and_arg_order():
    # Anchors pinned to ADJACENT columns and passed in REVERSED order (t3 before
    # t2). The old form required a strictly-interior integer column with comp1
    # left of comp2, so this was infeasible; the new form stays feasible and
    # still centres the target.
    s = _fresh_schematic()
    s.model.Add(s.comp_vars["t3"][1] == 6)  # right anchor
    s.model.Add(s.comp_vars["t2"][1] == 5)  # left anchor, adjacent
    pc.T_junction(s, "t1", "t3", "t2")      # reversed arg order
    solver = _solve(s)                      # asserts feasibility
    c1 = solver.Value(s.comp_vars["t1"][1])
    assert c1 in (5, 6)                     # rounded midpoint of an adjacent pair


def test_higher_weight_wins_between_conflicting_soft():
    # Two mutually exclusive soft constraints; the solver satisfies the heavier one.
    # This is the core of all-llm-soft: conflict resolved by weight, not by dropping.
    s = _fresh_schematic()
    pc.apply_soft(s, "left_of", ["t1", "t2"], 10)   # light
    pc.apply_soft(s, "right_of", ["t1", "t2"], 100)  # heavy, conflicts
    s.model.Minimize(sum(w * (1 - bb) for w, bb in s._soft_penalties))
    solver = _solve(s)
    # heavy right_of satisfied -> t1 right of t2
    assert solver.Value(s.comp_vars["t1"][1]) > solver.Value(s.comp_vars["t2"][1])
