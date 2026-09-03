# fmt: off
from dataclasses import dataclass
from copy import deepcopy
from datetime import datetime
from typing import Union, Any, Tuple
from collections import defaultdict
from ortools.sat.python import cp_model
import json
import os
import time

from src.utils.netlist_analyzer import NetlistAnalyzer
from src.routing.routing_2 import *
from src.placements.placer import *
import src.constraints.placement as pc
import src.constraints.orientation as oc
import src.constraints.library as lib

from loguru import logger

ENABLE_ROUTING = True
ENABLE_VDD_ROUTING = True
NUM_GENERATED_SCHEMATICS = 1
LOG_LEVEL = "DEBUG"

# When True, LLM-generated placement constraints are applied as SOFT objective
# penalties rather than hard constraints. The solver then keeps the max-weight
# satisfiable LLM subset jointly with routing, instead of the admission bisect's
# hard drop/keep decision. Subcircuit / user / path-based constraints stay hard,
# and the subcircuit de-confliction still runs (bad groups are still dropped).
#
# OPT-IN (default off): on small circuits soft placement satisfies more
# constraints with better routing, but on large circuits the bigger soft model
# (one penalty boolean per soft constraint) does not optimize as well under the
# fixed CP-SAT solve budget and can regress (see README "Placement Results").
# Enable per-run with SCHENGEN_ALL_LLM_SOFT=1.
ALL_LLM_SOFT = os.environ.get("SCHENGEN_ALL_LLM_SOFT", "0") == "1"

# Per-violation penalty for a soft LLM constraint. Sized (via the weight sweep in
# the PR) to sit above typical HPWL/bends objective terms so soft constraints are
# satisfied whenever feasible, while still yielding to hard-constraint feasibility.
# Env override for further tuning.
SOFT_CONSTRAINT_WEIGHT = int(os.environ.get("SCHENGEN_SOFT_WEIGHT", "100"))


@dataclass
class Component:
    name: str
    comp_type: str
    orientation: Union[int, None] = None
    row: int = -1
    col: int = -1

    connected_halo_id = 0
    _unconnected_halo_id = 0

    @property
    def unconnected_halo_id(self):
        if self.comp_type.startswith("pmos") or self.comp_type.startswith("pnp") or self.comp_type.startswith("nmos") or self.comp_type.startswith("npn"):
            if self._unconnected_halo_id == 0:
                self._unconnected_halo_id = 3
        if self.comp_type.startswith("resistor") or self.comp_type.startswith("capacitor"):
            if self._unconnected_halo_id == 0:
                self._unconnected_halo_id = 2
        return self._unconnected_halo_id
    
    def get_connected_halo_id(self):
        id = self.connected_halo_id
        self.connected_halo_id += 1
        return min(id, 4)
        
    
    def get_unconnected_halo_id(self):
        id = self.unconnected_halo_id
        self._unconnected_halo_id += 1
        return min(id, 4)


    def __repr__(self):
        return f"{self.name}: {self.comp_type} at r={self.row}, c={self.col}, o={self.orientation}"


class SchematicGenerator:
    def __init__(self, num_rows=10, num_cols=20, cell_size=100):

        self.num_rows = num_rows
        self.num_cols = num_cols
        self.cell_size = cell_size

        self.components: list[Component] = []
        self.constraints = []
        # Soft constraints: list of (constraint_tuple, weight). Applied as
        # objective penalties instead of hard constraints.
        self.soft_constraints = []
        self.comp_vars = {}
        
    @property
    def model_vars(self):
        return self.comp_vars
    
    def add_component(self, component: Component):
        self.components.append(component)

    def get_components(self) -> list[Component]:
        assert len(self.components) > 0, "No components added yet!"
        return self.components

    def find_component(self, component_name: str) -> Component:
        for comp in self.components:
            if comp.name == component_name:
                return comp
        raise ValueError(f"Component {component_name} not found!")

    def add_constrants(self, constraints):
        self.constraints.extend(constraints)

    def add_soft_constraints(self, constraints, weight):
        """Register constraints to be applied as objective penalties (soft constraints)."""
        self.soft_constraints.extend((c, weight) for c in constraints)

    def initial_cp_model(self):
        # Create the CP-SAT model
        self.model = cp_model.CpModel()

        # (weight, penalty_bool) pairs accumulated while applying soft
        # constraints; folded into the objective. Reset per model.
        self._soft_penalties = []

        # Create variables for each component's position
        self.comp_vars = {}
        for comp in self.components:
            # Each component has a row and column variable
            row_var = self.model.NewIntVar(0, self.num_rows - 1, f"{comp.name}_row")
            col_var = self.model.NewIntVar(0, self.num_cols - 1, f"{comp.name}_col")
            self.comp_vars[comp.name] = (row_var, col_var)

    def validate_component_names(self, names) -> bool:
        for name in names:
            if name not in self.comp_vars:
                logger.warning(f"Component {name} not found in schematic")
                return False
        return True
    
    def name2var(self, name) -> Tuple[cp_model.IntVar, cp_model.IntVar]:
        # Helper function to get the variable tuple (row_var, col_var) for a given component name
        if name not in self.comp_vars:
            raise ValueError(f"Component {name} not found in schematic")
        return self.comp_vars[name]

    def compute_component_positions(self, analyzer, feasibility_only: bool = False) -> bool:
        """
        Compute component positions based on constraints using OR-Tools CP-SAT solver.
        This is more efficient and robust than backtracking for constraint satisfaction.

        :param feasibility_only: if True, skip the placement-quality objective and stop at the
            first feasible solution. Used by the constraint admission loop, which only needs a
            yes/no feasibility answer and discards the solution (see docs/adr/0001).
        """
        model = self.model
        comp_vars = self.comp_vars

        # Add constraint: No two components can occupy the same cell
        # Two components are in different cells if row1 != row2 OR col1 != col2
        for i, comp1 in enumerate(self.components):
            for comp2 in self.components[i + 1 :]:
                row1, col1 = comp_vars[comp1.name]
                row2, col2 = comp_vars[comp2.name]
                # They must differ in at least one coordinate
                # Create boolean variables for each condition
                b_diff_row = model.NewBoolVar(f"{comp1.name}_{comp2.name}_diff_row")
                b_diff_col = model.NewBoolVar(f"{comp1.name}_{comp2.name}_diff_col")

                # b_diff_row is true if row1 != row2
                model.Add(row1 != row2).OnlyEnforceIf(b_diff_row)
                model.Add(row1 == row2).OnlyEnforceIf(b_diff_row.Not())

                # b_diff_col is true if col1 != col2
                model.Add(col1 != col2).OnlyEnforceIf(b_diff_col)
                model.Add(col1 == col2).OnlyEnforceIf(b_diff_col.Not())

                # At least one must be true (different row OR different column)
                model.AddBoolOr([b_diff_row, b_diff_col])


        for constraint in self.constraints:
            relation = constraint[0]
            args = constraint[1:]

            primitive = pc.PRIMITIVE_REGISTRY.get(relation)
            if primitive is None:
                logger.warning(f"Unknown constraint type '{relation}'")
                continue

            component_names = primitive.components(args)
            if not self.validate_component_names(component_names):
                logger.warning(f"Skipping constraint {constraint} due to invalid component names.")
                continue

            primitive.apply(self, args)

        # Soft constraints: apply as objective penalties. A relation
        # with no soft form is dropped here (the hard path already tried it).
        for constraint, weight in self.soft_constraints:
            relation = constraint[0]
            args = constraint[1:]

            primitive = pc.PRIMITIVE_REGISTRY.get(relation)
            if primitive is None:
                logger.warning(f"Unknown soft constraint type '{relation}'")
                continue
            if not self.validate_component_names(primitive.components(args)):
                logger.warning(f"Skipping soft constraint {constraint} due to invalid component names.")
                continue
            if not pc.apply_soft(self, relation, args, weight):
                logger.info(f"Relation '{relation}' has no soft form; dropping soft constraint {constraint}")

        # Create a solver and solve
        solver = cp_model.CpSolver()
        
        # Sets a time limit of 10 second.
        solver.parameters.max_time_in_seconds = 10
        # Optional deterministic placement for A/B testing (SCHENGEN_SEED=<int>).
        if os.environ.get("SCHENGEN_SEED"):
            solver.parameters.random_seed = int(os.environ["SCHENGEN_SEED"])
            solver.parameters.num_search_workers = 1

        # Optional: minimize the maximum row used to encourage compact layouts
        def add_row_compactness_objective(model, comp_vars):
            rows = []
            for component in self.components:
                row_var, col_var = comp_vars[component.name]
                rows.append(row_var)
            max_row = model.NewIntVar(0, self.num_rows, "schematic_max_row")
            model.AddMaxEquality(max_row, rows)
            return max_row  



        def add_routing_cost_objective(model, comp_vars, analyzer):
            # Get the estimated routing cost from the constraints, and use it to find a better solution.
            total_distances = []
            num_rows = self.num_rows
            num_cols = self.num_cols
            for net in analyzer.get_all_net_connections().keys():
                connected_components = analyzer.get_single_net_connections(net)

                # For simplicity, we use the Manhattan distance between connected components as a proxy for routing cost in the objective function.
                # For nets with more than 2 components, we sum the distances between consecutive pairs as an approximation.
                net_routing_cost = []
                for i in range(len(connected_components) - 1):
                    comp1_name, _ = connected_components[i]
                    comp2_name, _ = connected_components[i + 1]
                    row_var1, col_var1 = comp_vars[comp1_name]
                    row_var2, col_var2 = comp_vars[comp2_name]

                    row_diff     = model.NewIntVar(-num_rows, num_rows, f"row_diff_{net}_{i}")
                    col_diff     = model.NewIntVar(-num_cols, num_cols, f"col_diff_{net}_{i}")
                    abs_row_diff = model.NewIntVar(0, num_rows,         f"abs_row_diff_{net}_{i}")
                    abs_col_diff = model.NewIntVar(0, num_cols,         f"abs_col_diff_{net}_{i}")
                    manhattan    = model.NewIntVar(0, num_rows + num_cols, f"manhattan_{net}_{i}")

                    model.Add(row_diff == row_var1 - row_var2)
                    model.Add(col_diff == col_var1 - col_var2)
                    model.AddAbsEquality(abs_row_diff, row_diff)
                    model.AddAbsEquality(abs_col_diff, col_diff)
                    model.Add(manhattan == abs_row_diff + abs_col_diff)

                    net_routing_cost.append(manhattan)

                if net_routing_cost:
                    net_total = model.NewIntVar(0, len(net_routing_cost) * (num_rows + num_cols), f"net_total_{net}")
                    model.Add(net_total == sum(net_routing_cost))
                    total_distances.append(net_total)

            return sum(total_distances) if total_distances else 0
        
        def add_HPWL_cost_objective(model, comp_vars, analyzer):
            # get the estimated HPWL routing cost based on the bounding box of connected components for each net, and use it to find a better solution.
            total_cost = []
            num_rows = self.num_rows
            num_cols = self.num_cols
            for net in analyzer.get_all_net_connections().keys():
                connected_components = analyzer.get_single_net_connections(net)

                if len(connected_components) < 2:
                    continue

                row_vars = []
                col_vars = []
                for comp_name, _ in connected_components:
                    row_var, col_var = comp_vars[comp_name]
                    row_vars.append(row_var)
                    col_vars.append(col_var)

                min_row = model.NewIntVar(0, num_rows, f"min_row_{net}")
                max_row = model.NewIntVar(0, num_rows, f"max_row_{net}")
                min_col = model.NewIntVar(0, num_cols, f"min_col_{net}")
                max_col = model.NewIntVar(0, num_cols, f"max_col_{net}")

                model.AddMinEquality(min_row, row_vars)
                model.AddMaxEquality(max_row, row_vars)
                model.AddMinEquality(min_col, col_vars)
                model.AddMaxEquality(max_col, col_vars)

                hpwl = model.NewIntVar(0, num_rows + num_cols, f"hpwl_{net}")
                model.Add(hpwl == (max_row - min_row) + (max_col - min_col))
                total_cost.append(hpwl)
            
            return sum(total_cost) if total_cost else 0
        
        def add_bends_cost_objective(model, comp_vars, analyzer):
            num_rows, num_cols = self.num_rows, self.num_cols
            # Get the estimated number of bends in the routing based on the relative positions
            # of connected components for each net, and use it to find a better solution.
            total_bends = []
            for net in analyzer.get_all_net_connections().keys():
                connected_components = analyzer.get_single_net_connections(net)

                if len(connected_components) < 3:
                    continue

                bends_for_net = []
                for i in range(len(connected_components) - 2):
                    comp1_name, _ = connected_components[i]
                    comp2_name, _ = connected_components[i + 1]
                    comp3_name, _ = connected_components[i + 2]

                    row_var1, col_var1 = comp_vars[comp1_name]
                    row_var2, col_var2 = comp_vars[comp2_name]
                    row_var3, col_var3 = comp_vars[comp3_name]

                    # Reifiable bools for each alignment check
                    r1_eq_r2 = model.NewBoolVar(f"r1_eq_r2_{net}_{i}")
                    r2_eq_r3 = model.NewBoolVar(f"r2_eq_r3_{net}_{i}")
                    c1_eq_c2 = model.NewBoolVar(f"c1_eq_c2_{net}_{i}")
                    c2_eq_c3 = model.NewBoolVar(f"c2_eq_c3_{net}_{i}")

                    model.Add(row_var1 == row_var2).OnlyEnforceIf(r1_eq_r2)
                    model.Add(row_var1 != row_var2).OnlyEnforceIf(r1_eq_r2.Not())
                    model.Add(row_var2 == row_var3).OnlyEnforceIf(r2_eq_r3)
                    model.Add(row_var2 != row_var3).OnlyEnforceIf(r2_eq_r3.Not())
                    model.Add(col_var1 == col_var2).OnlyEnforceIf(c1_eq_c2)
                    model.Add(col_var1 != col_var2).OnlyEnforceIf(c1_eq_c2.Not())
                    model.Add(col_var2 == col_var3).OnlyEnforceIf(c2_eq_c3)
                    model.Add(col_var2 != col_var3).OnlyEnforceIf(c2_eq_c3.Not())

                    # No bend if any consecutive pair is row-aligned or col-aligned
                    # i.e. is_bend = NOT(r1==r2 OR r2==r3 OR c1==c2 OR c2==c3)
                    any_aligned = model.NewBoolVar(f"any_aligned_{net}_{i}")
                    model.AddBoolOr([r1_eq_r2, r2_eq_r3, c1_eq_c2, c2_eq_c3]).OnlyEnforceIf(any_aligned)
                    model.AddBoolAnd([r1_eq_r2.Not(), r2_eq_r3.Not(), c1_eq_c2.Not(), c2_eq_c3.Not()]).OnlyEnforceIf(any_aligned.Not())

                    is_bend = model.NewBoolVar(f"is_bend_{net}_{i}")
                    model.AddBoolXOr([is_bend, any_aligned])

                    bends_for_net.append(is_bend)

                if bends_for_net:
                    net_bends = model.NewIntVar(0, len(bends_for_net), f"net_bends_{net}")
                    model.Add(net_bends == sum(bends_for_net))
                    total_bends.append(net_bends)

            return sum(total_bends) if total_bends else 0



        # model.Minimize(add_routing_cost_objective(model, comp_vars, analyzer) + add_row_compactness_objective(model, comp_vars) * 100)  # weight the compactness objective to encourage more compact layouts, while primarily optimizing for routing cost
        if not feasibility_only:
            # Penalty for each violated soft constraint. weight * (1 - b)
            # is 0 when the constraint holds and weight when it is relaxed.
            soft_penalty = sum(weight * (1 - b) for weight, b in self._soft_penalties)
            model.Minimize(add_row_compactness_objective(model, comp_vars) * 100 + add_bends_cost_objective(model, comp_vars, analyzer) + add_HPWL_cost_objective(model, comp_vars, analyzer) + soft_penalty)
        status = solver.Solve(model)

        # Process the solution
        if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
            print("Successfully placed all components using OR-Tools!")
            for comp in self.components:
                row_var, col_var = comp_vars[comp.name]
                comp.row = solver.Value(row_var)
                comp.col = solver.Value(col_var)
                print(f"{comp.name}: row={comp.row}, col={comp.col}")

            if status == cp_model.OPTIMAL:
                print("Solution is optimal.")
            else:
                print("Solution is feasible but may not be optimal.")
            return True

        else:
            print("No solution found! The constraints may be unsatisfiable.")
            print(f"Solver status: {solver.StatusName(status)}")
            return False



    def add_bounding_box(self, bb_id=1, components: list[str] = []) -> list:
        bx1 = self.model.NewIntVar(0, self.num_cols, f"bx{bb_id}")
        by1 = self.model.NewIntVar(0, self.num_rows, f"by{bb_id}")
        bx1_w = self.model.NewIntVar(3, self.num_cols, f"bx{bb_id}_w")
        bx1_h = self.model.NewIntVar(0, self.num_rows, f"bx{bb_id}_h")

        for component in components:
            row_var, col_var = self.comp_vars[component]
            self.model.Add(col_var >= bx1)
            self.model.Add(row_var >= by1)
            self.model.Add(col_var + 2 <= bx1 + bx1_w)
            self.model.Add(row_var + 2 <= by1 + bx1_h)

        return [bx1, by1, bx1_w, bx1_h]

    def redraw_components(
        self,
        gird,
        scale,
        target_components: list[str],
        connected_components: list[Tuple[str, str]],
    ):
        for component in self.components:
            drill_thr = True if component.name in target_components else False
            # keep_out = 3

            vertical_barrier = False if component.comp_type == "port" else True
            horizontal_barrier = True
            if component.comp_type.startswith("port"):
                horizontal_barrier = False

            if component.comp_type.startswith("cap"):
                drill_thr = True
                vertical_barrier = True
                horizontal_barrier = True
                # keep_out = 3
            
            if component.name in target_components:
                # keep_out = 1
                keep_out = component.get_connected_halo_id()

                if (component.name, "gate") in connected_components:
                    horizontal_barrier = False
            else:
                keep_out = component.get_unconnected_halo_id()

            if "gnd" in component.name:
                place_component(
                    gird,
                    component.col * scale,
                    component.row * scale,
                    10,
                    10,
                    keepout=0,  # gnd stays routable (a boxed-in pin may need to escape
                    drill_through=drill_thr,  # through a gnd cell); tunneling is instead
                    vertical_barrier=vertical_barrier,  # discouraged by a soft A* penalty on
                    horizontal_barrier=horizontal_barrier,  # gnd cells (see grid.gnd_cells).
                    y_offset="middle",
                    max_keepout=0,
                )
            elif component.comp_type.startswith("port"):
                place_port(
                    gird,
                    component.col * scale,
                    component.row * scale,
                    10,
                    10,
                    open_for_routing = (component.name in target_components),
                )
            else:
                place_component(
                    gird,
                    component.col * scale,
                    component.row * scale,
                    10,
                    10,
                    keepout=keep_out,
                    drill_through=drill_thr,
                    vertical_barrier=vertical_barrier,
                    horizontal_barrier=horizontal_barrier,
                    y_offset="bottom",
                )

    def set_floorplaning(self, partioning_results: dict[str, list[str]]) -> None:
        assert "firstStage" in partioning_results
        assert "secondStage" in partioning_results
        assert "loads" in partioning_results
        assert "stageBias" in partioning_results

        model = self.model
        bx1, by1, bx1_w, bx1_h = self.add_bounding_box(
            1, partioning_results["firstStage"]
        )
        bx2, by2, bx2_w, bx2_h = self.add_bounding_box(
            2, partioning_results["secondStage"]
        )
        bx4, by4, bx4_w, bx4_h = self.add_bounding_box(4, partioning_results["stageBias"])
        model.Add(bx2 >= bx1 + bx1_w)

        # add non-overlapping constraints between blocks
        # 2D no-overlap constraints
        # --------------------------------------------------
        x_intervals = []
        y_intervals = []

        # get interval var for block 1 (firstStage)
        c1 = model.NewIntVar(0, self.num_cols, f"block1_end_x")
        model.Add(c1 == bx1 + bx1_w)
        x_int = model.NewIntervalVar(
            bx1, bx1_w, c1, f"x_int_b1"
        )  # start  # size  # end

        c2 = model.NewIntVar(0, self.num_rows, f"block1_end_y")
        model.Add(c2 == by1 + bx1_h)
        y_int = model.NewIntervalVar(by1, bx1_h, c2, "y_int_b1")
        x_intervals.append(x_int)
        y_intervals.append(y_int)

        # get interval var for block 4 (bias)
        c3 = model.NewIntVar(0, self.num_cols, f"block4_end_x")
        model.Add(c3 == bx4 + bx4_w)
        x_int = model.NewIntervalVar(bx4, bx4_w, c3, f"x_int_b4")

        c4 = model.NewIntVar(0, self.num_rows, f"block4_end_y")
        model.Add(c4 == by4 + bx4_h)
        y_int = model.NewIntervalVar(by4, bx4_h, c4, "y_int_b4")

        x_intervals.append(x_int)
        y_intervals.append(y_int)

        # currently disabled !
        # model.AddNoOverlap2D(x_intervals, y_intervals)


    # TODO: manually set orientation for components based on type and placement
    # here we use simple rules for demonstration
    # later, this should be based on LLM recommendations or more sophisticated logic
    def initialize_component_orientations(self) -> None:
        for comp in self.components:
            if comp.row >= 0 and comp.col >= 0:
                if comp.orientation is not None:
                    orientation = comp.orientation
                else:
                    if comp.comp_type.startswith("pmos") or comp.comp_type.startswith("pnp"):
                        orientation = 0  # "right"

                    elif comp.comp_type.startswith("nmos") or comp.comp_type.startswith("npn"):
                        if comp.comp_type.startswith("nmos_diode") or comp.comp_type.startswith("npn_diode"):
                            orientation = 0  ##"right"
                        else:
                            orientation = 1  # "left"
                    else:
                        orientation = 1
                        # orientation = "__unknown__"
                comp.orientation = orientation
            else:
                logger.debug(
                    f"component: {comp.name} has not assigned a proper position."
                )
                comp.orientation = 1

    def optimize_gate_orientations(self, analyzer: NetlistAnalyzer, locked_names: set) -> None:
        """Face each free transistor's gate toward the side where its gate net's
        other pins sit, shortening the gate wire (cheap column-based proxy, no
        routing). Runs after initialize_component_orientations().

        Symmetry is preserved: transistors whose orientation was fixed by a
        subcircuit primitive (e.g. a differential pair) are in ``locked_names``
        and skipped, diode-connected devices (gate shorted to drain) are left as
        drawn, and transistors sharing a gate net (current mirrors) are decided
        as a single group so matched devices keep a consistent facing.
        """
        # Group free, non-diode transistors by their gate net.
        groups = defaultdict(list)
        for t in analyzer.transistors:
            if t.name in locked_names:
                continue
            if t.gate == t.drain:  # diode-connected: gate faces drain, cosmetic
                continue
            comp = self.find_component(t.name)
            if comp.row < 0 or comp.col < 0:
                continue
            groups[t.gate].append(t)

        for gate_net, members in groups.items():
            member_names = {t.name for t in members}

            # Columns of the other pins on this gate net (the group's own gate
            # pins are excluded so shared-gate siblings don't pull each other).
            neighbour_cols = []
            try:
                connections = analyzer.get_single_net_connections(gate_net)
            except ValueError:
                connections = []
            for comp_name, pin_name in connections:
                if comp_name in member_names and pin_name == "gate":
                    continue
                try:
                    other = self.find_component(comp_name)
                except ValueError:
                    continue
                if other.col >= 0:
                    neighbour_cols.append(other.col)
            # A top-level port on this net also pulls the gate toward it.
            try:
                port = self.find_component("terminal_" + gate_net)
                if port.col >= 0:
                    neighbour_cols.append(port.col)
            except ValueError:
                pass

            if not neighbour_cols:
                continue  # nothing to face toward; keep the heuristic default

            neighbour_centroid = sum(neighbour_cols) / len(neighbour_cols)
            group_centroid = sum(
                self.find_component(t.name).col for t in members
            ) / len(members)

            if neighbour_centroid < group_centroid:
                orientation = 1  # neighbours are left -> gate faces left (X0)
            elif neighbour_centroid > group_centroid:
                orientation = 0  # neighbours are right -> gate faces right (X2)
            else:
                continue  # tie -> keep the heuristic default

            for t in members:
                self.find_component(t.name).orientation = orientation

    def set_component_orientations(self, data):
        for component_name, orientation in data.items():
            self.find_component(component_name).orientation = orientation

    def initialize_gnd_ports(self, analyzer: NetlistAnalyzer) -> None:
        components_with_gnd_connections = set()

        for component_name, _ in analyzer.get_single_net_connections("gnd!"):
            components_with_gnd_connections.add(component_name)

        for component_name in components_with_gnd_connections:
            self.add_component(
                Component(
                    "terminal_gnd!" + str(component_name),
                    "gnd",
                    None,
                    -1,
                    -1,
                )
            )

def include_constraints(
    schematic: SchematicGenerator,
    analyzer: NetlistAnalyzer,
    constraints: list[str],
    subcircuit_data: dict[str, list],
    partioning_data: dict[str, list],
    simplified_netlist: str,
    terminals: list[str],
    pathbased_constraints: list[str] = [],
    feasibility_only: bool = False,
    soft_constraints: list = [],
    tail_legs=None,
) -> bool:
    """Include constraints into the schematic and compute component positions.
    Return True if successful (i.e., found a valid solution), False otherwise.

    :param feasibility_only: if True, only check feasibility without optimizing placement
        quality (used for constraint admission probes, see docs/adr/0001).
    :param soft_constraints: LLM constraints to apply as objective penalties rather
        than hard constraints (see ALL_LLM_SOFT).
    """

    schematic.add_constrants(constraints)
    if soft_constraints:
        schematic.add_soft_constraints(soft_constraints, SOFT_CONSTRAINT_WEIGHT)
    if "gnd!" in terminals:
        schematic.initialize_gnd_ports(analyzer)
    schematic.initial_cp_model()
    


    if "firstStage" in partioning_data:
        # schematic.set_floorplaning(partioning_data)
        pass
    

    if len(subcircuit_data.keys()) == 0:
        logger.info("No subcircuit-specific constraints to apply.")

    for subckt, components in subcircuit_data.items():
        fn = subckt[:subckt.find("[")]
        if hasattr(lib, fn):
            getattr(lib, fn)(schematic, components)
            logger.info(f"Applied library function for subcircuit '{fn}' to components {components}.")
        else:
            logger.warning(f"Library function for subcircuit '{fn}' not found. Skipping subcircuit-specific constraints for components {components}.")

    if "CONSTRAINT_1_SHARE_DRAIN_SOURCE_CONNECTION" in pathbased_constraints:
        pc.share_drain_source(schematic, analyzer)
        pc.clear_drain_source_drain_connections(schematic, analyzer, include_drain_drain=False, include_drain_source=True)

    if "CONSTRAINT_1_SHARE_DRAIN_DRAIN_CONNECTION" in pathbased_constraints:
        pc.share_drain_drain(schematic, analyzer)
        pc.clear_drain_source_drain_connections(schematic, analyzer, include_drain_drain=True, include_drain_source=False)


    if "CONSTRAINT_2_SORT_VDD_GND_TRACABILITY" in pathbased_constraints:
        pc.top_down_vdd_gnd(schematic, simplified_netlist)
    
    if "CONSTRAINT_3_SHARE_GATE_TO_GATE_CONNECTION" in pathbased_constraints:
        pc.share_gate(schematic, analyzer, clear_columns=True, exclude=tail_legs)

    if "CONSTRAINT_3_1_SHARE_GATE_TO_GATE_CONNECTION_NO_CLEAR_COLUMNS" in pathbased_constraints:
        pc.share_gate(schematic, analyzer, clear_columns=False, exclude=tail_legs)

    if "CONSTRAINT_4_SHARE_SOURCE_TO_SOURCE_CONNECTION" in pathbased_constraints:
        pc.share_source(schematic, analyzer, impose_max_column_separation=False)
    
    if "CONSTRAINT_4_SHARE_SOURCE_TO_SOURCE_CONNECTION_MAX_COLUMN_3" in pathbased_constraints:
        pc.share_source(schematic, analyzer, impose_max_column_separation=True)

    if "CONSTRAINT_5_PLACE_SEPARATELY_2" in pathbased_constraints:
        pc.separate_components(schematic, space=2)
    
    if "CONSTRAINT_5_PLACE_SEPARATELY_3" in pathbased_constraints:
        pc.separate_components(schematic, space=3)

    # Compute positions based on constraints
    if "CONSTRAINT_6_PLACE_VDD_DIFFERENT_COLUMN" in pathbased_constraints:
        if "vdd!" in terminals: 
            pc.set_vdd_ports(schematic, analyzer)
    
    if "CONSTRAINT_7_DONT_PLACE_TOO_CLOSE_TO_BOUNDARIES" in pathbased_constraints:
        pc.skip_boundaries(schematic)

    if "CONSTRAINT_8_PLACE_CAPACITORS_MIDDLE" in pathbased_constraints:
        pc.set_capacitor_positions(schematic, analyzer)

    if "CONSTRAINT_9_PLACE_INPUT_PORTS_LEFT" in pathbased_constraints:
        pc.set_input_ports(schematic, [p for p in terminals if p.startswith("in")], analyzer)

    if "CONSTRAINT_10_PLACE_OUTPUT_PORTS_RIGHT" in pathbased_constraints:
        pc.set_output_ports(schematic, [p for p in terminals if p.startswith("out")], analyzer)

    if "CONSTRAINT_11_PLACE_BIASING_PORTS_LEFT" in pathbased_constraints:
        if "ibias" in terminals:
            pc.set_biasing_ports(schematic, ["ibias"], analyzer)

    if "gnd!" in terminals:
        pc.set_gnd_ports(schematic, analyzer)

    pc.set_surround_for_nets_connected_to_two_components_only(schematic, analyzer, max_boundary_size=5)
    # pc.share_source_source_2(schematic, analyzer)

    if "CONSTRAINT_13_PLACE_SAME_NET_CONNECTED_TERMINAL_IN_SAME_ROW_AND_CLEAR_COLUMN" in pathbased_constraints:
        pc.set_connected_components_close_and_same_row_clear_column(schematic,analyzer)
    
    pc.pmos_above_nmos_below(schematic, analyzer)
    return schematic.compute_component_positions(analyzer, feasibility_only=feasibility_only)
    


def get_connected_component_terminals(schematic: SchematicGenerator, analyzer: NetlistAnalyzer, net:str, scale: int) -> Tuple[list[Tuple[int, int]], list[Tuple[str, str]]]:
    """
    Get the list of connected component terminals the given net.
    
    :param schematic: SchematicGenerator object containing the schematic information
    :param analyzer: NetlistAnalyzer object containing the netlist information
    :return: A list of tuples, where each tuple contains the column and row of a terminal connected to the net.
    """

    pins: list[Pin] = []
    try:
        terminal_component = schematic.find_component("terminal_" + net)
        pins.append(Pin(component=terminal_component, name="center_dot"))
    except ValueError as e:
        pass

    connections = list(analyzer.get_single_net_connections(net))
    pins_by_component = defaultdict(set)
    for component_name, connected_pin_name in connections:
        pins_by_component[component_name].add(connected_pin_name)
    for component_name, connected_pin_name in connections:
        component = schematic.find_component(component_name)
        pins.append(Pin(component, connected_pin_name))

    pins.sort(key=lambda p: p.component.row)
    pins.reverse()
    grid_positions = translate_to_grid_positions(pins, scale)
    pin_names = [(p.component.name, p.name, ) for p in pins]

    # A diode-connected device has its gate and drain on this net, tied by the rendered
    # gate->drain short. Return those two pins as a "pre-connected" pair so the router
    # treats them as already joined: each other net member connects to whichever of the
    # two terminals is nearest (drain-side devices to the drain, the mirror gate rail to
    # the gate) and no redundant wire is drawn between the pair.
    index = {(p.component.name, p.name): i for i, p in enumerate(pins)}
    preconnected = []
    for component_name, pinset in pins_by_component.items():
        if {"gate", "drain"} <= pinset:
            preconnected.append((grid_positions[index[(component_name, "gate")]],
                                 grid_positions[index[(component_name, "drain")]]))
    return grid_positions, pin_names, preconnected

def rescale_routed_paths(segments, scale) -> list[Tuple[int, int]]:
    """Rescale the routed paths from grid coordinates back to schematic coordinates."""

    new_points = []
    for segment in segments:
        for i in range(len(segment)-1):
            p1 = segment[i]
            p2 = segment[i+1]

            p1 = [p1[0] * scale, p1[1] * scale]
            p2 = [p2[0] * scale, p2[1] * scale]

            flag = False
            if p1[0] == p2[0]: # vertical segment˙
                flag = True
            elif p1[1] == p2[1]: # horizontal segment
                flag = True
            
            if not flag:
                logger.warning(f"Non-Manhattan routing segment detected between points {p1} and {p2}. This should not happen with A* routing. Please check the routing algorithm.")

            new_points.append(p1)
            if p1[0] == p2[0]:  # same column, add intermediate points in between
                for row in range(min(p1[1], p2[1]), max(p1[1], p2[1]), 1):
                    new_points.append([p1[0], row])
            elif p1[1] == p2[1]:  # same row, add intermediate points in between
                for column in range(min(p1[0], p2[0]), max(p1[0], p2[0]), 1):
                    new_points.append([column, p1[1]])
    return new_points




def compute_structure_score(groups: dict[str, list], positions: dict[str, dict]) -> dict:
    """Score how well matched-device groups are laid out.

    For each group of >=2 placed devices, a group is 'aligned' if all its devices
    share a row or all share a column (the analog convention for matched devices),
    and its 'spread' is the bounding-box half-perimeter (row_span + col_span; lower
    is tighter). Returns per-group detail plus aggregates. Independent of which
    config declared the groups, so the same reference groups can be scored across
    layouts for comparison.
    """
    per_group = {}
    aligned = 0
    total_spread = 0
    scored = 0
    for name, devices in groups.items():
        rows = [positions[d]["row"] for d in devices if d in positions]
        cols = [positions[d]["col"] for d in devices if d in positions]
        if len(rows) < 2:
            continue
        scored += 1
        row_span = max(rows) - min(rows)
        col_span = max(cols) - min(cols)
        is_aligned = row_span == 0 or col_span == 0
        aligned += 1 if is_aligned else 0
        total_spread += row_span + col_span
        per_group[name] = {"row_span": row_span, "col_span": col_span, "aligned": is_aligned}
    return {
        "num_groups": scored,
        "aligned_groups": aligned,
        "alignment_ratio": round(aligned / scored, 3) if scored else None,
        "total_spread": total_spread,
        "per_group": per_group,
    }


def _llm_constraint_satisfied(schematic, c):
    """Evaluate a softenable LLM constraint against the final GRID positions
    (comp.row/comp.col). Returns True/False, or None if not evaluable (unknown
    relation or missing component). Used to report how many LLM constraints hold."""
    rel = c[0]
    if rel not in pc.SOFT_SUPPORTED:
        return None
    try:
        def r(n):
            return schematic.find_component(n).row

        def col(n):
            return schematic.find_component(n).col

        a = c[1:]
        if rel == "left_of":
            return col(a[0]) < col(a[1])
        if rel == "right_of":
            return col(a[0]) > col(a[1])
        if rel == "above":
            return r(a[0]) > r(a[1])  # above(A,B): row(A) > row(B), inverted y-axis
        if rel == "below":
            return r(a[0]) < r(a[1])
        if rel == "same_row":
            return r(a[0]) == r(a[1])
        if rel == "same_column":
            return col(a[0]) == col(a[1])
        if rel == "same_column_above":
            return col(a[0]) == col(a[1]) and r(a[0]) > r(a[1])
        if rel == "same_column_below":
            return col(a[0]) == col(a[1]) and r(a[0]) < r(a[1])
        if rel == "close_row":
            return abs(r(a[0]) - r(a[1])) <= a[2]
        if rel == "row_proximity":
            return abs(r(a[1]) - r(a[2])) <= a[0]
        if rel == "column_proximity":
            return abs(col(a[1]) - col(a[2])) <= a[0]
        if rel == "cluster_proximity":
            d, members = a[0], a[1:]
            return all(
                abs(r(m1) - r(m2)) <= d and abs(col(m1) - col(m2)) <= d
                for i, m1 in enumerate(members)
                for m2 in members[i + 1:]
            )
    except (ValueError, KeyError, IndexError):
        return None
    return None


def generate_schematic(
    netlist: str,
    user_defined_constraints: list,
    llm_generated_constraints: list,
    subcircuit_data: dict[str, list],
    partioning_data: dict[str, list],
    llm_generated_orientations: dict[str, int], 
    terminals: list[str] = ["ibias", "out", "vdd!", "in1", "in2"],
    user_defined_orientations: dict[str, int] = {},
    pathbased_constraints: list[str] = [],
    enable_routing_local_nets = False,
    component_placement_data = {}
) -> dict[str, Any]:
    """Generate schematic based on constraints and partitioning results."""

    _timing = defaultdict(float)  # stage -> seconds, logged at the end for performance analysis
    _t_start = time.perf_counter()

    analyzer = NetlistAnalyzer(netlist)

    cell_size = 100
    schematic = SchematicGenerator(num_rows=25, num_cols=40, cell_size=cell_size)

    # add component to canvas
    for t in analyzer.transistors:
        if t.name.lower().startswith("m")  or t.name.lower().startswith("q"):
            ext = "diode" if t.drain == t.gate else "normal"
            schematic.add_component(
                Component(t.name, f"{t.mos_type}_{ext}", None, -1, -1)
            )
        
    for c in analyzer.caps:
        schematic.add_component(Component(c.name, f"cap_vertical", None, -1, -1))
    
    for r in analyzer.resistors:
        schematic.add_component(Component(r.name, f"resistor", None, -1, -1))

    for tn in terminals:
        if not tn.startswith("gnd"):
            schematic.add_component(Component(f"terminal_{tn}", "port", None, -1, -1))

    # print ("****component placement data: ", component_placement_data)
    # add constraints
    valid_llm_constraints: list = []
    accepted_subcircuit = subcircuit_data  # subcircuit groups actually applied (may be de-conflicted below)
    # ----------------------------------------------
    if len(component_placement_data.keys()) > 0:
        logger.info(f"Applying component placement data for components: {list(component_placement_data.keys())}")
        if "gnd!" in terminals:
            schematic.initialize_gnd_ports(analyzer)
        for component_name, placement_info in component_placement_data.items():
            try:
                comp = schematic.find_component(component_name)
                comp.row = placement_info[1]
                comp.col = placement_info[0]
                comp.orientation = placement_info[2]
            except ValueError as e:
                logger.warning(f"Component {component_name} specified in component placement data not found in schematic. Skipping this component. Error: {e}")
    else:
        org_schematic = deepcopy(schematic)  # create a copy of the original schematic to apply constraints iteratively

        _t_admission = time.perf_counter()

        # Tail-aware placement: a current-mirror output leg that is also a differential pair's tail
        # (a t_junction stem whose two anchors are a recognized diff pair) is freed from its mirror
        # row-lock and from share_gate, and its STRICT t_junction -- which pins it to the single
        # column between an adjacent pair, often infeasible -- is replaced by a relaxed "below the
        # pair + near its column" placement so the tail current source sits under the pair as drawn.
        # On by default; SCHENGEN_NO_TAIL_EXCEPTION=1 disables it.
        tail_legs = set()
        if not os.environ.get("SCHENGEN_NO_TAIL_EXCEPTION"):
            _pairs = [set(v) for k, v in subcircuit_data.items() if k.startswith("MosfetDifferentialPair")]
            _relaxed, _drop_tj = [], []
            for _c in llm_generated_constraints:
                if _c[0] == "t_junction" and len(_c) >= 4 and {_c[2], _c[3]} in _pairs:
                    _tail, _a, _b = _c[1], _c[2], _c[3]
                    tail_legs.add(_tail)
                    _drop_tj.append(_c)
                    _relaxed += [["below", _tail, _a], ["below", _tail, _b],
                                 ["column_proximity", 2, _tail, _a], ["column_proximity", 2, _tail, _b]]
            if tail_legs:
                subcircuit_data = {
                    k: ([c for c in v if c not in tail_legs] if k.startswith("MosfetSimpleCurrentMirror") else v)
                    for k, v in subcircuit_data.items()
                }
                subcircuit_data = {k: v for k, v in subcircuit_data.items() if len(v) >= 2}
                # The relaxed replacements go through the LLM admission gate (like any
                # other LLM constraint) rather than being injected as hard user_defined
                # constraints: a strict t_junction that is infeasible with the base must
                # not be able to force the whole placement INFEASIBLE by the back door
                # (see #84). Feasible relaxations are still admitted and applied.
                llm_generated_constraints = [c for c in llm_generated_constraints if c not in _drop_tj] + _relaxed
                logger.info(f"[tail-exception] freeing tail legs {tail_legs}; replaced strict t_junction with relaxed below+near placement (admitted, not hard)")

        def _admit_llm_constraints(candidates: list, accepted: list, subckt: dict) -> list:
            """Batch+bisect admission (ADR-0001, option B): probe the whole batch with a
            single feasibility solve; on infeasibility, bisect to isolate the offending
            constraints. O(k*log n) solves for k bad constraints instead of one per constraint.

            `subckt` is the set of subcircuit groups applied during the probe; pass {} to admit
            LLM constraints on their own merits, or a group set to measure conflict against it."""
            if not candidates:
                return []
            probe_schematic = deepcopy(org_schematic)
            ret = include_constraints(probe_schematic, analyzer, accepted + candidates + user_defined_constraints, subckt, partioning_data, netlist, terminals, pathbased_constraints, feasibility_only=True, tail_legs=tail_legs)
            if ret:
                return candidates
            if len(candidates) == 1:
                return []
            mid = len(candidates) // 2
            left = _admit_llm_constraints(candidates[:mid], accepted, subckt)
            right = _admit_llm_constraints(candidates[mid:], accepted + left, subckt)
            return left + right

        # 1) Admit LLM constraints on their own merits (no subcircuit constraints applied). These
        #    are the high-value routing constraints the subcircuit groups must not silently override.
        valid_llm_constraints = _admit_llm_constraints(list(llm_generated_constraints), [], {})
        logger.info(f"Admitted {len(valid_llm_constraints)}/{len(llm_generated_constraints)} LLM-generated constraints via batch+bisect")

        # 2) Subcircuit de-confliction, prioritizing the block recognizer. Each recognized group
        #    (differential pair, current mirror, ...) is a trustworthy structural match, so when a
        #    group conflicts with the LLM's own placement relations we keep the group and drop the
        #    conflicting LLM relations -- e.g. the LLM stacks a shared-source pair (`above` +
        #    `same_column_above`) that the recognizer draws side-by-side (`same_row`); the two are
        #    infeasible together, so the recognizer wins. A group is dropped only if it cannot be
        #    placed at all against the user + path base (a genuinely bad / mislabeled group).
        def _feasible_with(subckt: dict) -> bool:
            probe = deepcopy(org_schematic)
            return include_constraints(probe, analyzer, valid_llm_constraints + user_defined_constraints, subckt, partioning_data, netlist, terminals, pathbased_constraints, feasibility_only=True, tail_legs=tail_legs)

        def _group_placeable(subckt: dict) -> bool:
            """Feasibility of the group set against the user + path base only (no LLM)."""
            probe = deepcopy(org_schematic)
            return include_constraints(probe, analyzer, user_defined_constraints, subckt, partioning_data, netlist, terminals, pathbased_constraints, feasibility_only=True, tail_legs=tail_legs)

        accepted_subcircuit = {}
        if subcircuit_data and _feasible_with(subcircuit_data):
            # Fast path: every group is jointly compatible with the admitted LLM set (no conflict),
            # so accept them all in a single probe instead of one per group.
            accepted_subcircuit = dict(subcircuit_data)
        else:
            for subckt, components in subcircuit_data.items():
                trial = {**accepted_subcircuit, subckt: components}
                if _feasible_with(trial):
                    accepted_subcircuit = trial  # no LLM displaced -> free to keep
                    continue
                # Conflict with the LLM set. Prioritize the recognizer: keep the group if it is
                # placeable on its own, dropping the LLM relations it displaces.
                if _group_placeable(trial):
                    dropped = len(valid_llm_constraints)
                    valid_llm_constraints = _admit_llm_constraints(valid_llm_constraints, [], trial)
                    dropped -= len(valid_llm_constraints)
                    accepted_subcircuit = trial
                    logger.info(f"De-conflict: kept subcircuit group '{subckt}' {components}, dropped {dropped} conflicting LLM constraint(s)")
                else:
                    logger.info(f"De-conflict: dropped subcircuit group '{subckt}' {components} (not placeable against user+path base)")
        if subcircuit_data:
            logger.info(f"Admitted {len(accepted_subcircuit)}/{len(subcircuit_data)} subcircuit groups after de-confliction; {len(valid_llm_constraints)} LLM constraints retained")

        _timing["placement:constraint_admission"] = time.perf_counter() - _t_admission

        # LLM constraints are applied as SOFT objective penalties (ALL_LLM_SOFT):
        # the hard set is user + subcircuit + path, and the solver keeps the
        # max-weight satisfiable LLM subset jointly with routing. This recovers
        # constraints the bisect would drop on LLM-vs-LLM conflict and, empirically,
        # lowers routing cost / bends versus the hard drop/keep decision. The
        # admission + subcircuit de-confliction above still runs, so bad subcircuit
        # groups are still dropped; only whether LLM constraints are hard changes.
        if ALL_LLM_SOFT:
            # Only relations that have a soft form go to the penalty path. The rest
            # (t_junction, between_columns, clear_*, above_all, ...) have no soft form,
            # so apply_soft would drop them entirely. Keep those HARD instead, but
            # admit them against the actual all-llm-soft hard base (user + accepted
            # subcircuit + path) so a non-softenable constraint that genuinely
            # conflicts is dropped rather than making the final solve infeasible.
            # This admission excludes the softenable LLM constraints (now penalties,
            # not hard), so a t_junction that lost the earlier all-LLM bisect can
            # still fit here — which is the whole point of moving the rest to soft.
            soft_constraints = [c for c in llm_generated_constraints if c[0] in pc.SOFT_SUPPORTED]
            non_softenable = [c for c in llm_generated_constraints if c[0] not in pc.SOFT_SUPPORTED]
            hard_llm_constraints = _admit_llm_constraints(non_softenable, [], accepted_subcircuit)
            combined_constraints = user_defined_constraints + hard_llm_constraints
            dropped_non_softenable = [c for c in non_softenable if c not in hard_llm_constraints]
            logger.info(f"[all-llm-soft] applying {len(soft_constraints)} LLM constraints as soft penalties (weight={SOFT_CONSTRAINT_WEIGHT}); {len(hard_llm_constraints)}/{len(non_softenable)} non-softenable LLM constraints kept hard; hard set = user + non-softenable-LLM + subcircuit + path")
            if dropped_non_softenable:
                logger.info(f"[all-llm-soft] dropped {len(dropped_non_softenable)} non-softenable LLM constraints (infeasible with hard base): {dropped_non_softenable}")
        else:
            combined_constraints = user_defined_constraints + valid_llm_constraints
            soft_constraints = []

        MAX_ATTEMPTS = 2
        schematic = deepcopy(org_schematic)
        _t_final_solve = time.perf_counter()
        for i in range(MAX_ATTEMPTS):
            ret = include_constraints(schematic, analyzer, combined_constraints, accepted_subcircuit, partioning_data, netlist, terminals, pathbased_constraints, soft_constraints=soft_constraints, tail_legs=tail_legs)
            if not ret:
                schematic = deepcopy(org_schematic)
                continue
            else:
                logger.info(f"Successfully found a valid component placement satisfying the constraints after {i+1} attempts.")
                break

        _timing["placement:final_solve"] = time.perf_counter() - _t_final_solve

        # Report how many softenable LLM constraints hold in the final grid.
        if ret:
            evals = [_llm_constraint_satisfied(schematic, c) for c in llm_generated_constraints]
            _sat = sum(1 for e in evals if e is True)
            _total = sum(1 for e in evals if e is not None)
            logger.info(f"LLM constraints satisfied in final placement: {_sat}/{_total}")

        if i == MAX_ATTEMPTS - 1 and not ret:
            logger.error(f"Failed to find a valid component placement satisfying the constraints after {MAX_ATTEMPTS} attempts. This may be due to conflicting constraints or the need for more sophisticated constraint handling. Please review the constraints and try again.")
            return {
                "success": False, 
                "message": "Failed to find a valid component placement satisfying the constraints. Please review the constraints and try again."}

        if "CONSTRAINT_12_PLACE_VDD_PORTS_TOP_RIGHT" in pathbased_constraints:
            if "vdd!" in terminals:
                pc.set_vdd_terminal_location(schematic)

        # assign orientation for two-terminal components before routing, to have better visualization during routing
        oc.assign_two_terminal_component_orientation(schematic, analyzer)
    
        # always fix the orientation of two-terminal components (tc) connected to gnd!
        for tc in analyzer.caps + analyzer.resistors:
            if "gnd!" in tc.get_all_connected_nets():
                schematic.find_component(tc.name).orientation = 0

        # assign orientations for the rest of the components based on LLM results if available, otherwise use-defined orientations.
        if len(llm_generated_orientations.keys()) > 0:
            schematic.initialize_component_orientations()
            schematic.set_component_orientations(llm_generated_orientations)
            logger.info("loaded component orientations from LLM results")
        else:
            # Snapshot transistors already orientation-locked by a subcircuit
            # primitive (e.g. a differential pair) BEFORE the heuristic fills in
            # defaults, so the wirelength pass leaves matched devices alone.
            locked = {c.name for c in schematic.components if c.orientation is not None}
            schematic.initialize_component_orientations()
            if os.environ.get("SCHENGEN_NO_ORIENT_OPT", "0") != "1":
                schematic.optimize_gate_orientations(analyzer, locked)
                logger.info("no LLM orientation data found, using wirelength-optimized heuristic orientations")
            else:
                logger.info("no LLM orientation data found, using heuristic orientations")

    # user-defined orientations (if any) will override LLM-generated orientations,
    # as user may have better knowledge of the design and can provide more accurate orientations.
    for component_name, orientation in user_defined_orientations.items():
        schematic.find_component(component_name).orientation = orientation


    # Routing
    # ----------------------------------------------
    routing_cost: dict[str, int] = defaultdict(int)

    routed_nets = {}
    routed_pins = {}
    turning_points_per_net = {}
    intersection_points = defaultdict(list)

    

    routing_info = {}
    if enable_routing_local_nets:
        _t_routing = time.perf_counter()
        scale = 10
        grid = Grid(width=schematic.num_cols * scale, height=schematic.num_rows * scale)

        for sc in schematic.components:
            if sc.comp_type == "port" or sc.name.startswith("terminal"):
                keep_out = 0
            else:
                keep_out = 1
            place_component(grid, sc.col * scale, sc.row * scale, 10, 10, keepout=keep_out)

        # Ground-symbol cells, for the A* soft penalty that keeps other nets from tunneling
        # through a ground symbol (gnd! is never routed, so no net legitimately ends there).
        grid.gnd_cells = set()
        for sc in schematic.components:
            if sc.comp_type == "gnd" or sc.name.startswith("terminal_gnd"):
                for _gx in range(sc.col * scale, sc.col * scale + scale):
                    for _gy in range(sc.row * scale, sc.row * scale + scale):
                        grid.gnd_cells.add((_gx, _gy))

        num_processed_nets = 0
        num_total_nets = len(analyzer.get_all_net_connections())


        # simple implementation of net ordering strategy: route nets with more connected components first, as they are usually more critical and harder to route. More sophisticated strategies can be implemented in the future.
        # net_counts = {net: len(connected_components) for net, connected_components in analyzer.get_all_net_connections().items()}
        # sorted_nets = sorted(net_counts.keys(), key=lambda net: net_counts[net], reverse=True)


        # sorted by HPWL estimation
        hpwl_estimation = {}
        for net, connected_components in analyzer.get_all_net_connections().items():
            row_positions = []
            col_positions = []
            for component_name, _ in connected_components:
                comp = schematic.find_component(component_name)
                if comp.row >= 0 and comp.col >= 0:
                    row_positions.append(comp.row)
                    col_positions.append(comp.col)
            if row_positions and col_positions:
                hpwl_estimation[net] = (max(row_positions) - min(row_positions)) + (max(col_positions) - min(col_positions))
            else:
                hpwl_estimation[net] = -1  # indicate that HPWL cannot be estimated due to missing component positions
                raise ValueError(f"Cannot estimate HPWL for net {net} due to missing component positions. Please check the component placement and constraints.")
        sorted_nets = sorted(hpwl_estimation.keys(), key=lambda net: hpwl_estimation[net], reverse=True)
        # Route the supply rail (vdd!) first and bias its trunk to the topmost track,
        # so it sits above every other rail (the analog "vdd on top" convention).
        sorted_nets = sorted(sorted_nets, key=lambda n: 0 if n.startswith("vdd") else 1)

        # T-junction nets: the shared signal net of each `t_junction(target, comp1, comp2)`
        # constraint, so the router can draw just those nets as a straight crossbar + stem (see
        # t_junction_topology). The placement constraint may have been dropped during admission,
        # but the net's role as a T-junction is still valid and only shapes the wire, not the
        # placement. Restricting to labelled nets avoids the crossbar/stem pattern mis-firing on
        # incidental 3-pin nets in circuits that have no T-junctions.
        _net_of_comp = defaultdict(set)
        for _net, _conns in analyzer.get_all_net_connections().items():
            for _cname, _pin in _conns:
                _net_of_comp[_cname].add(_net)
        tjunction_nets = set()
        for _c in llm_generated_constraints:
            if _c[0] != "t_junction" or len(_c) < 4:
                continue
            _shared = _net_of_comp.get(_c[1], set()) & _net_of_comp.get(_c[2], set()) & _net_of_comp.get(_c[3], set())
            tjunction_nets |= {n for n in _shared if not (n.startswith("gnd") or n.startswith("vdd"))}

        # Component-body cells (grid coords) for the post-route wire cleanup, so a
        # smoothed wire is never routed across a device.
        device_blocked = set()
        for sc in schematic.components:
            if sc.comp_type in ("port", "gnd") or sc.name.startswith("terminal"):
                continue
            for _bx in range(sc.col * scale + 1, sc.col * scale + scale):
                for _by in range(sc.row * scale + 1, sc.row * scale + scale):
                    device_blocked.add((_bx, _by))

        # Reserve each input port's pin (a 1-cell halo) and its straight stub to the
        # connected gate as keep-out for the cleanup. A* already routes other nets around
        # a port, but clean_net_wires only avoids device bodies (device_blocked, which
        # excludes ports), so without this it can straighten another net's wire straight
        # back over an input-port pin -- making the port read as shorted to that net.
        for _term in terminals:
            if not _term.startswith("in"):
                continue
            try:
                _port = schematic.find_component("terminal_" + _term)
            except ValueError:
                continue
            if _port.col < 0 or _port.row < 0:
                continue
            _px = _port.col * scale + scale // 2
            _py = _port.row * scale + scale // 2
            for _dx in (-1, 0, 1):
                for _dy in (-1, 0, 1):
                    device_blocked.add((_px + _dx, _py + _dy))
            _conns = analyzer.get_single_net_connections(_term)
            if len(_conns) == 1:
                try:
                    _gate = schematic.find_component(_conns[0][0])
                except ValueError:
                    _gate = None
                if _gate is not None and _gate.col >= 0:
                    # gate pin is on the left edge when the device faces left, else the right
                    _gx = _gate.col * scale if _gate.orientation == 1 else _gate.col * scale + scale
                    for _x in range(min(_px, _gx), max(_px, _gx) + 1):
                        device_blocked.add((_x, _py))

        # Ground symbols and two-terminal-device pins get the same cleanup keep-out. Both
        # are excluded above (gnd by comp_type; the cap/resistor pins sit on the cell
        # border, outside the interior body block), so cleanup can straighten a foreign
        # net straight across a ground symbol or over a cap/resistor pin -- reading as a
        # short to that symbol. gnd! is never routed, so blocking its body is always safe.
        for sc in schematic.components:
            if sc.comp_type == "gnd" or sc.name.startswith("terminal_gnd"):
                for _bx in range(sc.col * scale + 1, sc.col * scale + scale):
                    for _by in range(sc.row * scale + 1, sc.row * scale + scale):
                        device_blocked.add((_bx, _by))
            elif sc.comp_type in ("cap_vertical", "resistor") and sc.col >= 0:
                _cx = sc.col * scale + scale // 2
                for _py in (sc.row * scale, sc.row * scale + scale):  # top / bottom pins
                    for _dx in (-1, 0, 1):
                        device_blocked.add((_cx + _dx, _py))

        def _polys_cells(polys):
            cs = set()
            for poly in polys:
                for (x0, y0), (x1, y1) in zip(poly, poly[1:]):
                    if x0 == x1:
                        for y in range(min(y0, y1), max(y0, y1) + 1):
                            cs.add((x0, y))
                    elif y0 == y1:
                        for x in range(min(x0, x1), max(x0, x1) + 1):
                            cs.add((x, y0))
            return cs

        # Route every net first (raw), then clean them all. Cleaning never feeds back into
        # routing -- route_net marks each net's *raw* A* path on the grid, and cleanup does
        # not touch the grid -- so this two-pass split leaves the routing itself unchanged
        # and only widens what the cleanup can see. Cleanup straightens a wire only into
        # free space or across at most one crossing cell of another net; enforcing that
        # needs every OTHER net's cells. Cleaning inline (route+clean per net) only knew the
        # already-cleaned nets, so a net cleaned early could be straightened on top of a
        # later net's not-yet-cleaned wire (a collinear overlap). Collect all raw cells up
        # front and feed each cleanup the union of the other nets' cells.
        raw_by_net = {}
        pins_by_net = {}
        cost_by_net = {}
        raw_cells_by_net = {}
        all_raw_cells = set()
        for net in sorted_nets:
            if net in ["gnd!"]: continue

            connected_components = analyzer.get_single_net_connections(net)
            pins, pin_names, preconnected = get_connected_component_terminals(schematic,analyzer, net, scale)

            # set target components to redraw, which include the connected components and the terminal (if exists). This can help to have better readability.
            target_component_names = [c[0] for c in connected_components]
            if net in terminals:
                target_component_names += ["terminal_" + net]

            logger.debug(f"Routing Net: {net}, ({num_processed_nets}/{num_total_nets}) connected components: {target_component_names}, pins: {pins}")
            _t_net = time.perf_counter()
            schematic.redraw_components(grid, scale, target_component_names, connected_components)
            _t_redraw_done = time.perf_counter()
            _timing["routing:redraw_components"] += _t_redraw_done - _t_net
            logger.debug(f"Starting A* routing for net: {net} with pins: {pins}")
            # Supply rail on top: bias vdd!'s trunk to the topmost *source* pin
            # (excluding the far-off port terminal, which would drag the rail up to
            # the port row and leave long stubs). Other nets keep the median track.
            _trunk_prefer = "median"
            if net.startswith("vdd"):
                _src_ys = [p[1] for p, nm in zip(pins, pin_names) if not str(nm[0]).startswith("terminal")]
                _trunk_prefer = max(_src_ys) if _src_ys else "top"
            cost, routed_paths = route_net_parallel_priory(grid, net, pins, pin_names, is_tjunction=(net in tjunction_nets), preconnected=preconnected, trunk_prefer=_trunk_prefer)
            _timing["routing:astar"] += time.perf_counter() - _t_redraw_done
            raw_by_net[net] = routed_paths
            pins_by_net[net] = pins
            cost_by_net[net] = cost
            raw_cells_by_net[net] = _polys_cells(routed_paths["turning_points"])
            all_raw_cells |= raw_cells_by_net[net]

        routed_cells = set()  # cells of already-cleaned nets
        for net in sorted_nets:
            if net in ["gnd!"]: continue
            _t_clean = time.perf_counter()
            routed_paths = raw_by_net[net]
            pins = pins_by_net[net]
            cost = cost_by_net[net]
            # Router-level wire cleanup (guarded so it can never disconnect a pin): drop
            # redundant duplicate/loop segments and reduce bends, then derive routed_nets and
            # the intersection dots from this same clean geometry so wires, dots, and pin
            # connectivity all stay consistent. `other_cells` is every other net's cells
            # (raw for the not-yet-cleaned, cleaned for the rest) so a straightened wire is
            # never laid on top of another net.
            other_cells = routed_cells | (all_raw_cells - raw_cells_by_net[net])
            _clean = clean_net_wires(routed_paths["turning_points"], pins, device_blocked, other_cells)
            routed_paths["turning_points"] = _clean
            routed_paths["routed_segments"] = _clean
            routed_cells |= _polys_cells(_clean)  # remember this net's cells for later nets' cleanup
            routing_info[net] = routed_paths
            routing_cost[net] = cost
            segments = routed_paths["routed_segments"]
            turning_points_per_net[net] = routed_paths["turning_points"]
            points = rescale_routed_paths(segments, scale)
            routed_nets[net] = list(points)
            routed_pins[net] = pins

            # find intersection points (points that exist in more than one net's routed paths) for potential future use in design improvement and layout generation
            point_set = {tuple(p) for p in points}  # O(1) membership instead of O(P) list scans
            for p in points:
                north = (p[0], p[1] + 1)
                south = (p[0], p[1] - 1)
                east = (p[0] + 1, p[1])
                west = (p[0] - 1, p[1])

                count = 0
                if north in point_set:
                    count += 1
                if south in point_set:
                    count += 1

                if east in point_set:
                    count += 1

                if west in point_set:
                    count += 1

                if count >= 3:
                    intersection_points[net].append(tuple(p))

            _timing["routing:rescale_and_intersections"] += time.perf_counter() - _t_clean
            num_processed_nets += 1
            logger.debug(f"Finished cleanup for net: {net} with cost: {cost} , bend: {routed_paths['total_bend_cost']}, crossing: {routed_paths['total_crossing_cost']} in {time.perf_counter() - _t_net:.3f}s")


        _timing["routing:total"] = time.perf_counter() - _t_routing

    _timing["total"] = time.perf_counter() - _t_start
    logger.info("Timing summary (seconds):")
    for stage, seconds in _timing.items():
        logger.info(f"  {stage}: {seconds:.3f}")

    logger.info("Total routing cost: ", sum(routing_cost.values()), routing_cost)
    logger.info(f"Total bends: {sum([routed_paths['total_bend_cost'] for routed_paths in routing_info.values()])}")
    logger.info(f"Total crossings: {sum([routed_paths['total_crossing_cost'] for routed_paths in routing_info.values()])}")

    # cacluate HPWL for each net and log it for future improvement of routing algorithm
    hpwl_cost = {}
    for net, connected_components in analyzer.get_all_net_connections().items():
        row_positions = []
        col_positions = []
        for component_name, _ in connected_components:
            comp = schematic.find_component(component_name)
            if comp.row >= 0 and comp.col >= 0:
                row_positions.append(comp.row)
                col_positions.append(comp.col)
        if row_positions and col_positions:
            hpwl = (max(row_positions) - min(row_positions)) + (max(col_positions) - min(col_positions))
            hpwl_cost[net] = hpwl
        else:
            hpwl_cost[net] = -1  # indicate that HPWL cannot be calculated due to missing component positions
    logger.info("Total HPWL cost: ", sum(hpwl_cost.values()))


    # get the final component placement data after routing, which can be useful for future layout generation and design improvement.
    component_placement_data = {}
    for comp in schematic.components:
        if comp.row >= 0 and comp.col >= 0:
            component_placement_data[comp.name] = [comp.col, comp.row, int(comp.orientation) if comp.orientation is not None else 0, comp.comp_type ]


    # Get the list of unrouted nets for debugging and future improvement of routing algorithm
    # (net_id, connected_components, pin names)
    unrouted_nets = [net_id for net_id, cost in routing_cost.items() if cost == -1]
    unrouted_nets_data = defaultdict(list)
    for net_id in unrouted_nets:
        for component_name, pin_name in analyzer.get_single_net_connections(net_id):
            logger.info(f"Unrouted net: {net_id}, connected component: {component_name}, pin: {pin_name}")
            unrouted_nets_data[net_id].append([component_name, pin_name])

    logger.info(f"Valid LLM-generated constraints included\n: ")
    for c in valid_llm_constraints:
        print (f"{c},")
    
    _constraint_llms = []
    for c in llm_generated_constraints:
        if c in valid_llm_constraints:
            _constraint_llms.append([c, True])
        else:
            _constraint_llms.append([c, False])

    component_positions = {
        comp.name: {"row": comp.row, "col": comp.col, "orientation": comp.orientation, "comp_type": comp.comp_type}
        for comp in schematic.components
    }
    structure_score = compute_structure_score(subcircuit_data, component_positions)
    logger.info(f"Structure score: {structure_score['aligned_groups']}/{structure_score['num_groups']} groups aligned, total spread {structure_score['total_spread']}")

    data = {
        "success": True,
        "message": "P+R completed successfully.",

        "routing_cost": sum(routing_cost.values()) if -1 not in routing_cost.values() else -1,
        "num_bends": sum([routed_paths['total_bend_cost'] for routed_paths in routing_info.values()]),
        "num_crossings": sum([routed_paths['total_crossing_cost'] for routed_paths in routing_info.values()]),
        "hpwl_cost": sum(hpwl_cost.values()) if -1 not in hpwl_cost.values() else -1,
        "component_placement_data": component_placement_data,
        "routed_nets": routed_nets,
        "unrouted_nets": unrouted_nets,
        "unrouted_nets_data": dict(unrouted_nets_data),
        "routed_pins": routed_pins,
        "netlist": netlist,
        "intersection_points": dict(intersection_points),
        "turning_points": turning_points_per_net,
        "terminals": terminals,

        # constraint settings
        "constraint_pathbased": pathbased_constraints,
        "constraint_subcircuit": subcircuit_data,
        "constraint_subcircuit_accepted": accepted_subcircuit,
        "constraint_llm": _constraint_llms,
        "constraint_userdefined": user_defined_constraints,

        # structural quality
        "component_positions": component_positions,
        "structure_score": structure_score,
    }

    # save the schematic data to a json file for future use in layout generation and design improvement
    current_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = f"outputs/schematic_data_{current_timestamp}.json"
    with open(output_path, "w") as f:
        json.dump(data, f, indent=4)
    data["schengen_result_path"] = output_path

    return data
    # fmt: off


def main() -> None:
    pass


if __name__ == "__main__":
    main()
