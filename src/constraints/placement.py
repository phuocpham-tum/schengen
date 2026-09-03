from src.utils.netlist_analyzer import NetlistAnalyzer
from collections import defaultdict
from dataclasses import dataclass
from ortools.sat.python import cp_model
from src.tracing import trace_vdd_gnd

from typing import Callable, List, Tuple
from loguru import logger


def share_drain_source(self, analyzer: NetlistAnalyzer) -> None:
    # key is the component, value is the list of components that share drain/source connection with the key component
    shared_connections = analyzer.get_drain_source_connection()

    reversed_connections = defaultdict(list)
    for k, v in shared_connections.items():
        if len(v) == 1:
            reversed_connections[v[0]].append(k)

    for k, v in shared_connections.items():
        _, t1_col_var = self.model_vars[k]
        if len(v) == 1 and len(reversed_connections[v[0]]) == 1:
            _, t2_col_var = self.model_vars[v[0]]
            self.model.Add(t1_col_var == t2_col_var)
            logger.debug(f"{k} and {v[0]} should be in the same column")
        elif len(v) == 2:
            between_columns(self, target=k, components=v)
            logger.debug(f"{k}'s column should be in the middle of {v}")


def share_drain_drain(self, analyzer: NetlistAnalyzer) -> None:
    shared_connections = analyzer.get_drain_drain_connection()

    reversed_connections = defaultdict(list)
    for k, v in shared_connections.items():
        if len(v) == 1:
            reversed_connections[v[0]].append(k)

    for k, v in shared_connections.items():
        _, t1_col_var = self.model_vars[k]
        if len(v) == 1 and len(reversed_connections[v[0]]) == 1:
            _, t2_col_var = self.model_vars[v[0]]
            self.model.Add(t1_col_var == t2_col_var)
            logger.debug(f"{k} and {v[0]} should be in the same column")
        elif len(v) == 2:
            between_columns(self, target=k, components=v)
            logger.debug(f"{k}'s column should be in the middle of {v}")


def share_gate(self, analyzer: NetlistAnalyzer, clear_columns: bool = True, exclude=None) -> None:
    """Automatically set constraints to place components that share gate-to-gate connections close to each other.

    `exclude` names components to leave out of the same-row grouping (e.g. a differential-pair
    tail leg that should sit under its pair, not row-locked to the bias mirror it shares a gate with)."""
    exclude = exclude or set()
    shared_gate_connections = analyzer.get_shared_gate_connections()
    for net, connected_components in shared_gate_connections.items():
        components = [c for c in connected_components if c not in exclude]

        # these components should be placed in same row to facilitate gate-to-gate connections
        for i in range(len(components)):
            for j in range(i + 1, len(components)):
                comp1 = components[i]
                comp2 = components[j]
                same_row(self, comp1, comp2)
        if clear_columns:
            clear_column_in_between_multi(self, components)


def clear_drain_source_drain_connections(
    self,
    analyzer: NetlistAnalyzer,
    include_drain_drain: bool = True,
    include_drain_source: bool = True,
) -> None:
    shared_connections: dict[str, list[str]] = {}
    if include_drain_source:
        shared_connections = shared_connections | analyzer.get_drain_source_connection()
    if include_drain_drain:
        shared_connections = shared_connections | analyzer.get_drain_drain_connection()

    for src, connected_components in shared_connections.items():
        cols = []
        rows = []
        if len(connected_components) != 1:
            continue

        logger.debug(
            f"Setting drain/source sharing constraint for component: {src} -> with components: {connected_components}"
        )

        for component_name in connected_components + [src]:
            r, c = self.model_vars[component_name]
            cols.append(c)
            rows.append(r)

        max_col = self.model.NewIntVar(
            0,
            self.num_cols,
            f"max_col_share_ds{'*'.join(connected_components + [src])}",
        )
        min_col = self.model.NewIntVar(
            0,
            self.num_cols,
            f"min_col_share_ds{'*'.join(connected_components + [src])}",
        )
        self.model.AddMinEquality(min_col, cols)
        self.model.AddMaxEquality(max_col, cols)

        max_row = self.model.NewIntVar(
            0,
            self.num_rows,
            f"max_row_share_ds{'*'.join(connected_components + [src])}",
        )
        min_row = self.model.NewIntVar(
            0,
            self.num_rows,
            f"min_row_share_ds{'*'.join(connected_components + [src])}",
        )
        self.model.AddMinEquality(min_row, rows)
        self.model.AddMaxEquality(max_row, rows)

        for component in self.components:
            row, col = self.comp_vars[component.name]

            if component.name not in connected_components + [src]:
                # no overlap
                # for other components, if they are in the same row range, they must be outside the col range
                logger.debug(
                    f"Adding no-overlap constraint for component: {component.name} with drain/source shared group: {connected_components + [src]}"
                )
                # Boolean: row is inside the row interval
                row_ge_min = self.model.NewBoolVar(f"{component.name}_row_ge_min_{src}")
                row_le_max = self.model.NewBoolVar(f"{component.name}_row_le_max_{src}")
                row_inside = self.model.NewBoolVar(f"{component.name}_row_inside_{src}")

                # Link row >= min_row
                self.model.Add(row >= min_row).OnlyEnforceIf(row_ge_min)
                self.model.Add(row < min_row).OnlyEnforceIf(row_ge_min.Not())

                # Link row <= max_row
                self.model.Add(row <= max_row).OnlyEnforceIf(row_le_max)
                self.model.Add(row > max_row).OnlyEnforceIf(row_le_max.Not())

                # row_inside = row_ge_min AND row_le_max
                self.model.AddBoolAnd([row_ge_min, row_le_max]).OnlyEnforceIf(
                    row_inside
                )
                self.model.AddBoolOr(
                    [row_ge_min.Not(), row_le_max.Not()]
                ).OnlyEnforceIf(row_inside.Not())

                # # Column outside booleans
                # col_left = self.model.NewBoolVar(
                #     f"{component.name}_left_of_group_{net}"
                # )
                # col_right = self.model.NewBoolVar(
                #     f"{component.name}_right_of_group_{net}"
                # )

                # self.model.Add(col < min_col).OnlyEnforceIf(col_left)
                # self.model.Add(col >= min_col).OnlyEnforceIf(col_left.Not())

                # self.model.Add(col > max_col).OnlyEnforceIf(col_right)
                # self.model.Add(col <= max_col).OnlyEnforceIf(col_right.Not())

                # # If row_inside → (col_left OR col_right)
                # self.model.AddBoolOr([col_left, col_right]).OnlyEnforceIf(row_inside)

                # as we only care about the case when two components are in the same row range (checking condition: len(connected_components) != 1),
                # thus in that case, the min_col and max_col must be the same.
                # we can simply enforce the col != min_col and col != max_col when row_inside is true.
                self.model.Add(col != min_col).OnlyEnforceIf(row_inside)
                self.model.Add(col != max_col).OnlyEnforceIf(row_inside)


def share_source_source_2(self, analyzer: NetlistAnalyzer) -> None:
    """Automatically set constraints to place components that share source-to-source connections (same type) should be in the same row to facilitate source-to-source connections"""
    shared_source_connections = analyzer.get_shared_source_connections_same_types()
    for _, shared_source_nets in shared_source_connections.items():
        for net, connected_components in shared_source_nets.items():
            for i in range(len(connected_components)):
                for j in range(i + 1, len(connected_components)):
                    comp1 = connected_components[i]
                    comp2 = connected_components[j]
                    same_row(self, comp1, comp2)
            clear_column_in_between_multi(self, connected_components)


def share_source(
    self,
    analyzer: NetlistAnalyzer,
    impose_max_column_separation: bool = False,
) -> None:
    shared_connections = analyzer.get_shared_source_connections()
    for net, list_components in shared_connections.items():
        t1_row_var, t1_col_var = self.model_vars[list_components[0]]
        for component_name in list_components[1:]:
            t2_row_var, t2_col_var = self.model_vars[component_name]
            self.model.Add(t1_row_var == t2_row_var)

            logger.debug(
                f"*** {list_components[0]} and {component_name} should be on the same row"
            )

            if impose_max_column_separation:

                max_col = self.model.NewIntVar(
                    0, self.num_cols, f"max_col_{list_components[0]}_{component_name}"
                )
                min_col = self.model.NewIntVar(
                    0, self.num_cols, f"min_col_{list_components[0]}_{component_name}"
                )
                self.model.AddMinEquality(min_col, [t1_col_var, t2_col_var])
                self.model.AddMaxEquality(max_col, [t1_col_var, t2_col_var])
                self.model.Add(max_col - min_col <= 3)


def separate_components(self, space: int) -> None:
    """
    Add constraints to enforce all components to be separated by at least certain space (in terms of rows and columns).

    Args:
        space (int): the minimum number of rows and columns that should separate any two components.
        For example, if space=2, it means there should be at least 2 row and 2 column between any two components.
    """

    # HC: seperate components at least 1 grid cell
    for i in range(len(self.components)):
        for j in range(i + 1, len(self.components)):
            comp1 = self.components[i]
            comp2 = self.components[j]
            if comp1.comp_type in ["gnd"] or comp2.comp_type in ["gnd"]:
                continue

            if hasattr(comp1, "ignored_seperation_constraint") and hasattr(
                comp2, "ignored_seperation_constraint"
            ):
                if (
                    comp1.ignored_seperation_constraint
                    and comp2.ignored_seperation_constraint
                ):
                    continue

            c1_r, c1_c = self.model_vars[comp1.name]
            c2_r, c2_c = self.model_vars[comp2.name]

            # Column separation
            col_pos = self.model.NewBoolVar(f"col_pos_{i}_{j}")
            col_neg = self.model.NewBoolVar(f"col_neg_{i}_{j}")
            self.model.Add(c2_c - c1_c >= space).OnlyEnforceIf(col_pos)
            self.model.Add(c1_c - c2_c >= space).OnlyEnforceIf(col_neg)

            # ignored_ports = ["terminal_in", "terminal_ibias"]
            ignored_ports = ["terminal_ibias"]
            ignored_ = False
            for port in ignored_ports:
                if comp1.name.startswith(port) or comp2.name.startswith(port):
                    ignored_ = True
                    break
            if ignored_:
                continue

            logger.debug(
                f"Adding separation constraint between {comp1.name} and {comp2.name}"
            )

            # Row separation
            row_pos = self.model.NewBoolVar(f"row_pos_{i}_{j}")
            row_neg = self.model.NewBoolVar(f"row_neg_{i}_{j}")
            self.model.Add(c2_r - c1_r >= space).OnlyEnforceIf(row_pos)
            self.model.Add(c1_r - c2_r >= space).OnlyEnforceIf(row_neg)

            # Enforce at least ONE separation
            self.model.AddBoolOr([col_pos, col_neg, row_pos, row_neg])


def top_down_vdd_gnd(self, simplified_netlist: str) -> None:
    vdd_gnd_paths = trace_vdd_gnd(simplified_netlist, targets=["vdd!", "gnd!"])
    for i, path in enumerate(vdd_gnd_paths):
        print(f"Path {i + 1}:")
        devices_in_path = [dev for net, dev in path if dev != None]
        print(" Devices in path: ", devices_in_path)

        for i in range(len(devices_in_path)):
            for j in range(i + 1, len(devices_in_path)):
                dev1 = devices_in_path[i]
                dev2 = devices_in_path[j]
                print("adding separation constraint between ", dev1, dev2)
                r1, c1 = self.model_vars[dev1]
                r2, c2 = self.model_vars[dev2]
                self.model.Add(r1 - r2 >= 0)


def skip_boundaries(self) -> None:
    for component in self.components:
        comp_r, comp_c = self.model_vars[component.name]
        self.model.Add(comp_r >= 3)
        self.model.Add(comp_r < self.num_rows - 1)
        self.model.Add(comp_c >= 2)
        self.model.Add(comp_c < self.num_cols - 1)


def set_input_ports(
    self,
    input_ports: list[str],
    analyzer: NetlistAnalyzer,
) -> None:
    """For input ports, we want to place them on the left side of the connected components, and vertically aligned with the connected components"""

    for port in input_ports:
        component_names = analyzer.get_single_net_connections(port)
        assert (
            len(component_names) == 1
        ), f"Expected only one component connected to {port}"

        connected_component_name, _ = component_names[0]
        connected_component_r, connected_component_c = self.model_vars[
            connected_component_name
        ]
        port_r, port_c = self.model_vars["terminal_" + port]
        self.model.Add(port_r == connected_component_r)  # same row
        component = self.find_component(connected_component_name)

        if component.orientation == 1:
            self.model.Add(port_c == connected_component_c - 2)
        else:
            self.model.Add(port_c == connected_component_c + 2)

        self.find_component("terminal_" + port).ignored_seperation_constraint = True
        self.find_component(connected_component_name).ignored_seperation_constraint = (
            True
        )


def set_biasing_ports(
    self, biasing_ports: list[str], analyzer: NetlistAnalyzer
) -> None:
    for port in biasing_ports:
        # usually, ibias is connected to multiple components, we just connect to the first one for simplicity (the most left)
        r1, c1 = self.model_vars["terminal_" + port]
        for component_name, _ in analyzer.get_single_net_connections(port):
            r0, c0 = self.model_vars[component_name]
            self.model.Add(c1 < c0)

        rows, cols = [], []
        for component_name, _ in analyzer.get_single_net_connections(port):
            r0, c0 = self.model_vars[component_name]
            rows.append(r0)
            cols.append(c0)

        min_row = self.model.NewIntVar(0, self.num_rows, f"min_row_{port}")
        max_row = self.model.NewIntVar(0, self.num_rows, f"max_row_{port}")
        min_col = self.model.NewIntVar(0, self.num_cols, "min_col")
        max_col = self.model.NewIntVar(0, self.num_cols, "max_col")
        self.model.AddMinEquality(min_row, rows)
        self.model.AddMaxEquality(max_row, rows)
        self.model.AddMinEquality(min_col, cols)
        self.model.AddMaxEquality(max_col, cols)

        self.model.Add(c1 == min_col - 1)
        self.model.Add(r1 >= min_row)
        self.model.Add(r1 <= max_row)


def set_output_ports(self, output_ports, analyzer: NetlistAnalyzer) -> None:
    """
    For output ports, we want to place them on the right side of the connected components,
    and horizontally aligned with the middle point of the connected components
    """

    for port in output_ports:

        output_port_r, output_port_c = self.model_vars["terminal_" + port]
        rows = []
        cols = []
        for comp_name, _ in analyzer.get_single_net_connections(port):
            r0, c0 = self.model_vars[comp_name]
            rows.append(r0)
            cols.append(c0)

        # fmt: off
        min_row = self.model.NewIntVar(0, self.num_rows, f"relative_output_{port}_min_row")
        max_row = self.model.NewIntVar(0, self.num_rows, f"relative_output_{port}_max_row")
        self.model.AddMinEquality(min_row, rows)
        self.model.AddMaxEquality(max_row, rows)

        min_col = self.model.NewIntVar(0, self.num_cols, f"relative_output_{port}_min_col")
        max_col = self.model.NewIntVar(0, self.num_cols, f"relative_output_{port}_max_col")
        self.model.AddMinEquality(min_col, cols)
        self.model.AddMaxEquality(max_col, cols)

        self.model.Add(output_port_c > max_col)
        self.model.Add(output_port_c == max_col + 1)

        # compute output_port_r as midpoint
        sum_row = self.model.NewIntVar(0, 2 * self.num_rows, f"relative_output_{port}_sum_row")
        self.model.Add(sum_row == max_row + min_row)
        self.model.Add(2 * output_port_r <= sum_row)
        self.model.Add(sum_row <= 2 * output_port_r + 1)
        # fmt: on


def set_gnd_ports(self, analyzer: NetlistAnalyzer) -> None:
    """For gnd ports, we want to place them below the connected components"""
    for component_name, _ in analyzer.get_single_net_connections("gnd!"):
        r0, c0 = self.model_vars[component_name]
        r1, c1 = self.model_vars["terminal_gnd!" + str(component_name)]
        self.model.Add(c1 == c0)
        self.model.Add(r1 == r0 - 1)


def set_vdd_ports(self, analyzer: NetlistAnalyzer) -> None:
    """Add constraints that components connected to vdd should be placed in different columns to avoid routing congestion"""
    component_with_vdd_connections = set()
    for component_name, _ in analyzer.get_single_net_connections("vdd!"):
        component_with_vdd_connections.add(component_name)

    for c1_name in component_with_vdd_connections:  # leave one vdd terminal for the top
        for c2_name in component_with_vdd_connections:
            if c1_name == c2_name:
                continue

            r1, c1 = self.model_vars[c1_name]
            r2, c2 = self.model_vars[c2_name]
            self.model.Add(c1 != c2)


def set_vdd_terminal_location(self) -> None:
    max_col = -1
    min_col = 100
    max_row = -1
    min_row = 100
    for component in self.components:
        if component.comp_type != "port":
            r, c = component.row, component.col
            max_col = max(max_col, c)
            min_col = min(min_col, c)
            max_row = max(max_row, r)
            min_row = min(min_row, r)

    logger.debug("max_col: ", max_col, " min_col: ", min_col)
    logger.debug("max_row: ", max_row, " min_row: ", min_row)
    self.find_component("terminal_vdd!").col = max_col
    self.find_component("terminal_vdd!").row = max_row + 2


def set_capacitor_positions(
    self,
    analyzer: NetlistAnalyzer,
) -> None:
    """Place capacitors in the middle of the connected components"""
    for i, cap in enumerate(analyzer.caps):
        r1, c1 = self.model_vars[cap.name]
        all_nets = cap.get_all_connected_nets()
        rows = []  # collection of IntVars (rows of connected components)
        cols = []
        for net in all_nets:
            if net == "gnd!":
                continue
            for component_name, _ in analyzer.get_single_net_connections(net):
                if component_name.startswith("c"):
                    continue
                r0, c0 = self.model_vars[component_name]
                rows.append(r0)
                cols.append(c0)

        min_row = self.model.NewIntVar(0, self.num_rows, f"cap_{i}_" + "min_row")
        max_row = self.model.NewIntVar(0, self.num_rows, f"cap_{i}_" + "max_row")
        self.model.AddMinEquality(min_row, rows)
        self.model.AddMaxEquality(max_row, rows)

        min_col = self.model.NewIntVar(0, self.num_cols, f"cap_{i}_" + "min_col")
        max_col = self.model.NewIntVar(0, self.num_cols, f"cap_{i}_" + "max_col")
        self.model.AddMinEquality(min_col, cols)
        self.model.AddMaxEquality(max_col, cols)

        # strict constraints
        self.model.Add(r1 > min_row + 1)
        self.model.Add(r1 < max_row - 1)
        # self.model.Add(c1 > min_col)


def set_surround_for_nets_connected_to_two_components_only(
    self, analyzer: NetlistAnalyzer, max_boundary_size=5
) -> None:
    for net, connected_components in analyzer.get_all_net_connections().items():
        if len(connected_components) == 2:
            comp1, comp2 = connected_components
            surround_by_a_component(
                self,
                target=comp1[0],
                related_component=comp2[0],
                boundary_size=max_boundary_size,
            )
            surround_by_a_component(
                self,
                target=comp2[0],
                related_component=comp1[0],
                boundary_size=max_boundary_size,
            )


def set_connected_components_close_and_same_row_clear_column(
    self, analyzer: NetlistAnalyzer, target_terminals: list[str] = ["source"]
) -> None:
    """
    Place components that are connected by the same net (and via terminals in target_terminals) close to each other.
    Only consider cases with two components connected by the same net. (For example, if two components share the same source connection, we want to place them close to each other)
    In addition, constraints about clear column in between are added to avoid routing congestion.

    Args:
        analyzer (NetlistAnalyzer): the netlist analyzer object that contains the netlist information and can be used to get the connected components for each net.
        target_terminals (list[str]): the list of terminal types that we want to consider for this constraint.
    """

    for _, connected_components in analyzer.get_all_net_connections().items():
        for target_terminal in target_terminals:
            share_components = set()
            for c1 in connected_components:
                for c2 in connected_components:
                    if c1 == c2:
                        continue
                    if c1[0].startswith("terminal_") or c2[0].startswith("terminal_"):
                        continue
                    if c1[0].startswith("c") or c2[0].startswith("c"):
                        continue
                    if c1[0].startswith("r") or c2[0].startswith("r"):
                        continue

                    # for components connected by the same net, we want to place them close to each other
                    c1_obj = self.find_component(c1[0])
                    c2_obj = self.find_component(c2[0])

                    if c1_obj.comp_type == c2_obj.comp_type and c1_obj.comp_type.split(
                        "_"
                    )[0] in [
                        "nmos",
                        "pmos",
                        "pnp",
                        "npn",
                    ]:
                        if c1[1] == c2[1] and c1[1] == target_terminal:
                            share_components.add(c1[0])
                            share_components.add(c2[0])

            if len(share_components) == 2:
                m1, m2 = list(share_components)[0], list(share_components)[1]
                same_row(self, m1, m2)
                clear_column_between(self, m1, m2)
                logger.debug(
                    f"+ place {m1} and {m2} in the same row and clear column in between"
                )


# -------------------------------
# PUBLIC CONSTRAINT INTERFACES (for LLMs/users to call directly)
# -------------------------------


def same_row(self, comp1_name: str, comp2_name: str) -> None:
    r1, _ = self.comp_vars[comp1_name]
    r2, _ = self.comp_vars[comp2_name]
    self.model.Add(r1 == r2)


def same_column(self, comp1_name: str, comp2_name: str) -> None:
    r1, c1 = self.comp_vars[comp1_name]
    r2, c2 = self.comp_vars[comp2_name]
    self.model.Add(c1 == c2)


def below(self, comp1_name: str, comp2_name: str, spacing: int = 0) -> None:
    # below means higher row number (inverted y-axis)
    row1, col1 = self.name2var(comp1_name)
    row2, col2 = self.name2var(comp2_name)
    self.model.Add(row1 + spacing < row2)


def above(self, comp1_name: str, comp2_name: str, spacing: int = 0) -> None:
    # above means lower row number (inverted y-axis)
    row1, col1 = self.name2var(comp1_name)
    row2, col2 = self.name2var(comp2_name)
    self.model.Add(row1 + spacing > row2)


def left_of(self, comp1_name: str, comp2_name: str, spacing: int = 0) -> None:
    row1, col1 = self.name2var(comp1_name)
    row2, col2 = self.name2var(comp2_name)
    self.model.Add(col1 + spacing < col2)


def right_of(self, comp1_name: str, comp2_name: str, spacing: int = 0) -> None:
    row1, col1 = self.name2var(comp1_name)
    row2, col2 = self.name2var(comp2_name)
    self.model.Add(col1 + spacing > col2)


def between_columns(
    self,
    target: str,
    components: list[str],
    impose_space_limit: bool = True,
) -> None:
    cols = []
    for component_name in components:
        _, c2_col = self.model_vars[component_name]
        cols.append(c2_col)

    max_col = self.model.NewIntVar(
        0, self.num_cols, f"max_col_{'_'.join(components)}_{target}"
    )
    min_col = self.model.NewIntVar(
        0, self.num_cols, f"min_col_{'_'.join(components)}_{target}"
    )
    self.model.AddMinEquality(min_col, cols)
    self.model.AddMaxEquality(max_col, cols)

    _, c1_col = self.model_vars[target]
    if impose_space_limit:
        self.model.Add(max_col - min_col <= 5)
    self.model.Add(c1_col > min_col)
    self.model.Add(c1_col < max_col)


def between_rows(
    self,
    target: str,
    components: list[str],
    impose_space_limit: bool = True,
) -> None:
    rows = []
    for component_name in components:
        r2_row, _ = self.model_vars[component_name]
        rows.append(r2_row)

    max_row = self.model.NewIntVar(
        0, self.num_rows, f"max_row_{'_'.join(components)}_{target}"
    )
    min_row = self.model.NewIntVar(
        0, self.num_rows, f"min_row_{'_'.join(components)}_{target}"
    )
    self.model.AddMinEquality(min_row, rows)
    self.model.AddMaxEquality(max_row, rows)

    r1_row, _ = self.model_vars[target]
    if impose_space_limit:
        self.model.Add(max_row - min_row <= 5)
    self.model.Add(r1_row > min_row)
    self.model.Add(r1_row < max_row)


def clear_column_between(
    self,
    target1: str,
    target2: str,
    ignored_list: list[str] = [],
) -> None:
    """Set constraint to ensure that there is no components placed in the columns between target1 and target2 (if they are in the same row), to create routing space"""
    r1, c1 = self.model_vars[target1]
    r2, c2 = self.model_vars[target2]

    # min_col/max_col are per target-pair, not per component — create once
    min_col = self.model.NewIntVar(0, self.num_cols, f"min_col_{target1}_{target2}")
    max_col = self.model.NewIntVar(0, self.num_cols, f"max_col_{target1}_{target2}")
    self.model.AddMinEquality(min_col, [c1, c2])
    self.model.AddMaxEquality(max_col, [c1, c2])

    for component in self.components:
        if component.name in [target1, target2]:
            continue
        if component.name in ignored_list:
            continue
        r, c = self.model_vars[component.name]

        # Bool: is this component in the same row as both targets?
        same_row_as_t1 = self.model.NewBoolVar(
            f"same_row_t1_{component.name}_{target1}_{target2}"
        )
        same_row_as_t2 = self.model.NewBoolVar(
            f"same_row_t2_{component.name}_{target1}_{target2}"
        )
        same_row = self.model.NewBoolVar(
            f"same_row_{component.name}_{target1}_{target2}"
        )

        self.model.Add(r == r1).OnlyEnforceIf(same_row_as_t1)
        self.model.Add(r != r1).OnlyEnforceIf(same_row_as_t1.Not())
        self.model.Add(r == r2).OnlyEnforceIf(same_row_as_t2)
        self.model.Add(r != r2).OnlyEnforceIf(same_row_as_t2.Not())

        # same_row is True only if both r==r1 and r==r2 (i.e. r1==r2 and r matches)
        self.model.AddBoolAnd([same_row_as_t1, same_row_as_t2]).OnlyEnforceIf(same_row)
        self.model.AddBoolOr(
            [same_row_as_t1.Not(), same_row_as_t2.Not()]
        ).OnlyEnforceIf(same_row.Not())

        # c must be outside (min_col, max_col) — use reifiable bool vars
        c_lt_min = self.model.NewBoolVar(
            f"c_lt_min_{component.name}_{target1}_{target2}"
        )
        c_gt_max = self.model.NewBoolVar(
            f"c_gt_max_{component.name}_{target1}_{target2}"
        )

        self.model.Add(c < min_col).OnlyEnforceIf(c_lt_min)
        self.model.Add(c >= min_col).OnlyEnforceIf(c_lt_min.Not())
        self.model.Add(c > max_col).OnlyEnforceIf(c_gt_max)
        self.model.Add(c <= max_col).OnlyEnforceIf(c_gt_max.Not())

        # If in the same row, component must be outside the column range
        self.model.AddBoolOr([c_lt_min, c_gt_max]).OnlyEnforceIf(same_row)


def clear_column_in_between_multi(self, components: list[str]) -> None:
    """Set constraint to ensure that there is no components placed in the columns between any two components in the list (if they are in the same row), to create routing space"""
    for i in range(len(components)):
        for j in range(i + 1, len(components)):
            clear_column_between(
                self, components[i], components[j], ignored_list=components
            )


def clear_row_between(
    self,
    target1: str,
    target2: str,
    ignored_list: list[str] = [],
) -> None:
    """Set constraint to ensure that there is no components placed in the rows between target1 and target2 (if they are in the same column), to create routing space"""
    r1, c1 = self.model_vars[target1]
    r2, c2 = self.model_vars[target2]

    # min_row/max_row are per target-pair, not per component — create once
    min_row = self.model.NewIntVar(0, self.num_rows, f"min_row_{target1}_{target2}")
    max_row = self.model.NewIntVar(0, self.num_rows, f"max_row_{target1}_{target2}")
    self.model.AddMinEquality(min_row, [r1, r2])
    self.model.AddMaxEquality(max_row, [r1, r2])

    for component in self.components:
        if component.name in [target1, target2]:
            continue
        if component.name in ignored_list:
            continue
        r, c = self.model_vars[component.name]

        # Bool: is this component in the same column as both targets?
        same_col_as_t1 = self.model.NewBoolVar(
            f"same_col_t1_{component.name}_{target1}_{target2}"
        )
        same_col_as_t2 = self.model.NewBoolVar(
            f"same_col_t2_{component.name}_{target1}_{target2}"
        )
        same_col = self.model.NewBoolVar(
            f"same_col_{component.name}_{target1}_{target2}"
        )

        self.model.Add(c == c1).OnlyEnforceIf(same_col_as_t1)
        self.model.Add(c != c1).OnlyEnforceIf(same_col_as_t1.Not())
        self.model.Add(c == c2).OnlyEnforceIf(same_col_as_t2)
        self.model.Add(c != c2).OnlyEnforceIf(same_col_as_t2.Not())

        # same_col is True only if both c==c1 and c==c2 (i.e. c1==c2 and c matches)
        self.model.AddBoolAnd([same_col_as_t1, same_col_as_t2]).OnlyEnforceIf(same_col)
        self.model.AddBoolOr(
            [same_col_as_t1.Not(), same_col_as_t2.Not()]
        ).OnlyEnforceIf(same_col.Not())

        # r must be outside (min_row, max_row) — use reifiable bool vars
        r_lt_min = self.model.NewBoolVar(
            f"r_lt_min_{component.name}_{target1}_{target2}"
        )
        r_gt_max = self.model.NewBoolVar(
            f"r_gt_max_{component.name}_{target1}_{target2}"
        )
        self.model.Add(r < min_row).OnlyEnforceIf(r_lt_min)
        self.model.Add(r >= min_row).OnlyEnforceIf(r_lt_min.Not())
        self.model.Add(r > max_row).OnlyEnforceIf(r_gt_max)
        self.model.Add(r <= max_row).OnlyEnforceIf(r_gt_max.Not())
        # If in the same column, component must be outside the row range
        self.model.AddBoolOr([r_lt_min, r_gt_max]).OnlyEnforceIf(same_col)


def row_proximity(self, target1: str, target2: str, max_distance=5) -> None:
    """Set constraint to ensure that target1 and target2 are placed in rows close to each other
    (the absolute distance less than max_distance), to create proximity for routing"""

    r1, _ = self.comp_vars[target1]
    r2, _ = self.comp_vars[target2]

    diff = self.model.NewIntVar(
        -self.num_rows, self.num_rows, f"row_diff_{target1}_{target2}"
    )
    abs_diff = self.model.NewIntVar(
        0, self.num_rows, f"row_abs_diff_{target1}_{target2}"
    )

    self.model.Add(diff == r1 - r2)
    self.model.AddAbsEquality(abs_diff, diff)
    self.model.Add(abs_diff <= max_distance)


def column_proximity(self, target1: str, target2: str, max_distance=5) -> None:
    """Set constraint to ensure that target1 and target2 are placed in columns close to each other
    (the absolute distance less than max_distance), to create proximity for routing"""

    _, c1 = self.comp_vars[target1]
    _, c2 = self.comp_vars[target2]

    diff = self.model.NewIntVar(
        -self.num_cols, self.num_cols, f"col_diff_{target1}_{target2}"
    )
    abs_diff = self.model.NewIntVar(
        0, self.num_cols, f"col_abs_diff_{target1}_{target2}"
    )

    self.model.Add(diff == c1 - c2)
    self.model.AddAbsEquality(abs_diff, diff)
    self.model.Add(abs_diff <= max_distance)


def cluster_proximity(self, targets: list[str], max_distance=7) -> None:
    """Set constraint to ensure that all components in targets are placed close to each other (the absolute distance less than max_distance), to create proximity for routing"""
    for i in range(len(targets)):
        for j in range(i + 1, len(targets)):
            row_proximity(self, targets[i], targets[j], max_distance)
            column_proximity(self, targets[i], targets[j], max_distance)


def cluster_proximity_by_net(
    self, net: str, analyzer: NetlistAnalyzer, max_distance=7
) -> None:
    """Set constraint to ensure that all components connected to the same net are placed close to each other (the absolute distance less than max_distance), to create proximity for routing"""
    connected_components = analyzer.get_single_net_connections(net)
    component_names = [comp for comp, _ in connected_components]
    cluster_proximity(self, component_names, max_distance)


def pmos_above_nmos_below(self, analyzer: NetlistAnalyzer) -> None:
    """Automatically set constraints to place PMOS components above NMOS components"""
    for t1 in analyzer.transistors:
        for t2 in analyzer.transistors:
            if t1 != t2:
                r1, _ = self.comp_vars[t1.name]
                r2, _ = self.comp_vars[t2.name]
                if (t1.mos_type == "pmos" and t2.mos_type == "nmos") or (
                    t1.mos_type == "pnp" and t2.mos_type == "npn"
                ):
                    self.model.Add(r1 >= r2)


def T_junction(self, target: str, comp1: str, comp2: str) -> None:
    """Place `target` as the stem of a T-junction whose crossbar is the
    row-aligned pair (comp1, comp2): the pair shares a row and sits close
    together, and `target` sits at the pair's centre column in a nearby,
    distinct row (a vertical drop from the crossbar).

    Order-agnostic in (comp1, comp2), and robust to the pair being in adjacent
    columns: the centre then rounds to one of the two columns, and the distinct
    row keeps `target` from overlapping an anchor. The old form required a
    strictly-interior integer column, so an adjacent pair (gap 1) had no valid
    column and the constraint was dropped as infeasible."""
    r_target, c_target = self.comp_vars[target]
    r_comp1, c_comp1 = self.comp_vars[comp1]
    r_comp2, c_comp2 = self.comp_vars[comp2]

    # Crossbar: the pair shares a row and stays close (order-agnostic via min/max).
    self.model.Add(r_comp1 == r_comp2)
    min_c = self.model.NewIntVar(0, self.num_cols, f"tj_min_c_{target}")
    max_c = self.model.NewIntVar(0, self.num_cols, f"tj_max_c_{target}")
    self.model.AddMinEquality(min_c, [c_comp1, c_comp2])
    self.model.AddMaxEquality(max_c, [c_comp1, c_comp2])
    self.model.Add(max_c - min_c <= 3)

    # Stem centred on the pair: 2*c_target == (min_c + max_c) +/- 1, i.e. the
    # rounded midpoint (exact when the span is even).
    self.model.Add(2 * c_target >= min_c + max_c - 1)
    self.model.Add(2 * c_target <= min_c + max_c + 1)

    # Stem sits in a distinct, nearby row (vertical drop from the crossbar).
    row_gap = self.model.NewIntVar(-self.num_rows, self.num_rows, f"tj_rowgap_{target}")
    abs_row_gap = self.model.NewIntVar(0, self.num_rows, f"tj_absrowgap_{target}")
    self.model.Add(row_gap == r_comp1 - r_target)
    self.model.AddAbsEquality(abs_row_gap, row_gap)
    self.model.Add(abs_row_gap >= 1)
    self.model.Add(abs_row_gap <= 5)


def row_close(self, target: str, related_component: str, max_distance=5) -> None:
    r_target, _ = self.comp_vars[target]
    r_related, _ = self.comp_vars[related_component]

    # Ensure target is within max_distance rows of related_component
    self.model.Add(r_target >= r_related - max_distance)
    self.model.Add(r_target <= r_related + max_distance)


def surround_by_a_component(
    self, target: str, related_component: str, boundary_size=5
) -> None:
    r_target, c_target = self.comp_vars[target]
    r_related, c_related = self.comp_vars[related_component]

    # Ensure target is within boundary_size rows and boundary_size columns of related_component
    self.model.Add(r_target >= r_related - boundary_size)
    self.model.Add(r_target <= r_related + boundary_size)
    self.model.Add(c_target >= c_related - boundary_size)
    self.model.Add(c_target <= c_related + boundary_size)


def above_all(self, target: str, spacing: int = 1) -> None:
    r_target, c_target = self.comp_vars[target]
    for component in self.components:
        if component.name == target or component.name.startswith("terminal_"):
            continue
        r, _ = self.model_vars[component.name]
        self.model.Add(r_target > r + spacing)

    # set c_target to be the leftmost to create more routing space on the right side
    min_col = self.model.NewIntVar(0, self.num_cols, f"min_col_all_{target}")
    cols = []
    for component in self.components:
        if component.name == target or component.name.startswith("terminal_"):
            continue
        _, c = self.model_vars[component.name]
        cols.append(c)
    self.model.AddMinEquality(min_col, cols)
    self.model.Add(c_target < min_col)


def below_all(self, target: str, spacing: int = 1) -> None:
    r_target, c_target = self.comp_vars[target]
    for component in self.components:
        if component.name == target or component.name.startswith("terminal_"):
            continue
        r, _ = self.model_vars[component.name]
        self.model.Add(r_target < r - spacing)

    # set c_target to be the leftmost to create more routing space on the right side
    min_col = self.model.NewIntVar(0, self.num_cols, f"min_col_all_{target}")
    cols = []
    for component in self.components:
        if component.name == target or component.name.startswith("terminal_"):
            continue
        _, c = self.model_vars[component.name]
        cols.append(c)
    self.model.AddMinEquality(min_col, cols)
    self.model.Add(c_target < min_col)


def middle_all(self, target: str) -> None:
    """Place the target in the middle row of the canvas, with all other components above or below it"""
    r_target, _ = self.comp_vars[target]
    other_rows = []
    for component in self.components:
        if component.name == target or component.name.startswith("terminal_"):
            continue
        r, _ = self.model_vars[component.name]
        other_rows.append(r)

    min_row = self.model.NewIntVar(0, self.num_rows, f"min_row_others_{target}")
    max_row = self.model.NewIntVar(0, self.num_rows, f"max_row_others_{target}")
    self.model.AddMinEquality(min_row, other_rows)
    self.model.AddMaxEquality(max_row, other_rows)

    # for r_target to be in the middle (symmetrical) of other rows, the distance to min_row and max_row should be the same
    diff_min = self.model.NewIntVar(0, self.num_rows, f"diff_min_{target}")
    diff_max = self.model.NewIntVar(0, self.num_rows, f"diff_max_{target}")
    self.model.Add(diff_min == r_target - min_row)
    self.model.Add(diff_max == max_row - r_target)
    self.model.AddAbsEquality(diff_min, diff_max)

    # also set c_target to be the leftmost to create more routing space on the right side
    min_col = self.model.NewIntVar(0, self.num_cols, f"min_col_all_{target}")
    cols = []
    for component in self.components:
        if component.name == target or component.name.startswith("terminal_"):
            continue
        _, c = self.model_vars[component.name]
        cols.append(c)
    self.model.AddMinEquality(min_col, cols)
    self.model.Add(self.model_vars[target][1] < min_col)


# -------------------------------
# CONSTRAINT REGISTRY (single source of truth)
# -------------------------------
#
# Each LLM/user-facing constraint relation is declared exactly once here. The
# registry drives BOTH the dispatch in SchematicGenerator.compute_component_positions
# and the {{CONSTRAINT_PRIMITIVES}} vocabulary handed to the LLM (see
# render_primitives_doc), so the two can never drift apart.
#
# A constraint is emitted as a list whose first element is the relation name,
# e.g. ["left_of", "m1", "m2"] or ["row_proximity", 5, "m1", "m2"]. `args` below
# is that list minus the relation name (constraint[1:]).


@dataclass
class Primitive:
    """One LLM/user-facing constraint relation.

    apply:      (schematic, args) -> None. Adds the constraint to the CP model.
    components: (args) -> list[str]. The subset of args that are component names,
                used to validate names before applying. Declaring this explicitly
                (rather than guessing positions) is what lets numeric args sit
                anywhere in the tuple without being mistaken for component names.
    signature:  human-readable call form shown to the LLM, e.g. "left_of(A, B)".
    description: one-line meaning shown to the LLM.
    strictness: relative ordering (lower = fewer feasible placements ruled out).
                Only affects the order primitives appear in the generated doc.
    """

    name: str
    apply: Callable
    components: Callable
    signature: str
    description: str
    strictness: int


PRIMITIVES: List[Primitive] = [
    Primitive(
        "right_of",
        lambda s, a: right_of(s, a[0], a[1]),
        lambda a: [a[0], a[1]],
        "right_of(A, B)",
        "Place A in a column to the right of B.",
        10,
    ),
    Primitive(
        "left_of",
        lambda s, a: left_of(s, a[0], a[1]),
        lambda a: [a[0], a[1]],
        "left_of(A, B)",
        "Place A in a column to the left of B.",
        10,
    ),
    Primitive(
        "above",
        lambda s, a: above(s, a[0], a[1]),
        lambda a: [a[0], a[1]],
        "above(A, B)",
        "Place A in a row above B.",
        10,
    ),
    Primitive(
        "below",
        lambda s, a: below(s, a[0], a[1]),
        lambda a: [a[0], a[1]],
        "below(A, B)",
        "Place A in a row below B.",
        10,
    ),
    Primitive(
        "row_proximity",
        lambda s, a: row_proximity(s, a[1], a[2], max_distance=a[0]),
        lambda a: [a[1], a[2]],
        "row_proximity(D, A, B)",
        "Keep A and B within D rows of each other.",
        20,
    ),
    Primitive(
        "column_proximity",
        lambda s, a: column_proximity(s, a[1], a[2], max_distance=a[0]),
        lambda a: [a[1], a[2]],
        "column_proximity(D, A, B)",
        "Keep A and B within D columns of each other.",
        20,
    ),
    Primitive(
        "close_row",
        lambda s, a: row_close(s, a[0], a[1], max_distance=a[2]),
        lambda a: [a[0], a[1]],
        "close_row(A, B, D)",
        "Keep A within D rows of B.",
        20,
    ),
    Primitive(
        "cluster_proximity",
        lambda s, a: cluster_proximity(s, list(a[1:]), max_distance=a[0]),
        lambda a: list(a[1:]),
        "cluster_proximity(D, A, B, ...)",
        "Keep all listed components within D rows and columns of each other.",
        25,
    ),
    Primitive(
        "above_all",
        lambda s, a: above_all(s, a[1], a[0]),
        lambda a: [a[1]],
        "above_all(S, A)",
        "Place A above every other component, with spacing S.",
        30,
    ),
    Primitive(
        "below_all",
        lambda s, a: below_all(s, a[1], a[0]),
        lambda a: [a[1]],
        "below_all(S, A)",
        "Place A below every other component, with spacing S.",
        30,
    ),
    Primitive(
        "middle_all",
        lambda s, a: middle_all(s, a[0]),
        lambda a: [a[0]],
        "middle_all(A)",
        "Place A in the middle row, all other components above or below it.",
        30,
    ),
    Primitive(
        "same_row",
        lambda s, a: same_row(s, a[0], a[1]),
        lambda a: [a[0], a[1]],
        "same_row(A, B)",
        "Align A and B on the same row.",
        40,
    ),
    Primitive(
        "same_column",
        lambda s, a: same_column(s, a[0], a[1]),
        lambda a: [a[0], a[1]],
        "same_column(A, B)",
        "Align A and B in the same column.",
        40,
    ),
    Primitive(
        "same_column_above",
        lambda s, a: (same_column(s, a[0], a[1]), above(s, a[0], a[1])),
        lambda a: [a[0], a[1]],
        "same_column_above(A, B)",
        "Align A and B in the same column, with A above B.",
        45,
    ),
    Primitive(
        "same_column_below",
        lambda s, a: (same_column(s, a[0], a[1]), below(s, a[0], a[1])),
        lambda a: [a[0], a[1]],
        "same_column_below(A, B)",
        "Align A and B in the same column, with A below B.",
        45,
    ),
    Primitive(
        "between_columns",
        lambda s, a: between_columns(s, target=a[0], components=list(a[1:])),
        lambda a: list(a),
        "between_columns(T, A, B, ...)",
        "Place T in a column between the listed components.",
        50,
    ),
    Primitive(
        "between_rows",
        lambda s, a: between_rows(s, target=a[0], components=list(a[1:])),
        lambda a: list(a),
        "between_rows(T, A, B, ...)",
        "Place T in a row between the listed components.",
        50,
    ),
    Primitive(
        "clear_row_between",
        lambda s, a: clear_row_between(s, a[0], a[1], []),
        lambda a: [a[0], a[1]],
        "clear_row_between(A, B)",
        "Keep the rows between A and B (when column-aligned) clear of other components.",
        55,
    ),
    Primitive(
        "clear_column_between",
        lambda s, a: clear_column_between(s, a[0], a[1], []),
        lambda a: [a[0], a[1]],
        "clear_column_between(A, B)",
        "Keep the columns between A and B (when row-aligned) clear of other components.",
        55,
    ),
    Primitive(
        "t_junction",
        lambda s, a: T_junction(s, a[0], a[1], a[2]),
        lambda a: [a[0], a[1], a[2]],
        "t_junction(T, A, B)",
        "Place T between row-aligned A and B, forming a T-junction.",
        60,
    ),
]

# name -> Primitive, for O(1) dispatch lookup.
PRIMITIVE_REGISTRY = {p.name: p for p in PRIMITIVES}


def render_primitives_doc() -> str:
    """Render the {{CONSTRAINT_PRIMITIVES}} block for the LLM prompt from the
    registry, ordered from lowest to highest strictness (as the prompt expects)."""
    lines = ["Constraint primitives (ordered from least to most strict):", ""]
    for i, p in enumerate(sorted(PRIMITIVES, key=lambda p: p.strictness), start=1):
        lines.append(f"{i}. `{p.signature}` — {p.description}")
    return "\n".join(lines)


# -------------------------------
# SOFT (penalty-based) CONSTRAINTS
# -------------------------------
#
# A soft constraint is satisfied iff a penalty boolean is 1; when it is 0 the
# constraint is relaxed and (weight * not-satisfied) is added to the objective.
# This lets a constraint that would otherwise be *dropped* on conflict survive
# as a preference instead. Only the relational primitives with a single-linear
# core are supported; the rest fall back to being dropped (the caller logs it).

SOFT_SUPPORTED = {
    "above",
    "below",
    "left_of",
    "right_of",
    "same_row",
    "same_column",
    "same_column_above",
    "same_column_below",
    "close_row",
    "row_proximity",
    "column_proximity",
    "cluster_proximity",
}


def _soft_abs_within(self, v1, v2, max_distance, penalty_bool, label, axis) -> None:
    """Reify |v1 - v2| <= max_distance under penalty_bool (half-reified: the
    bound only applies when penalty_bool is 1)."""
    span = self.num_rows if axis == "row" else self.num_cols
    diff = self.model.NewIntVar(-span, span, f"soft_{axis}diff_{label}")
    absd = self.model.NewIntVar(0, span, f"soft_{axis}absdiff_{label}")
    self.model.Add(diff == v1 - v2)
    self.model.AddAbsEquality(absd, diff)
    self.model.Add(absd <= max_distance).OnlyEnforceIf(penalty_bool)


def apply_soft(self, relation: str, args, weight: int) -> bool:
    """Apply a supported relational primitive as a soft constraint. On success,
    appends (weight, penalty_bool) to self._soft_penalties and returns True.
    Returns False (without touching the model) if the relation has no soft form,
    signalling the caller to drop it. Mirrors the hard adapters in PRIMITIVES."""
    if relation not in SOFT_SUPPORTED:
        return False

    b = self.model.NewBoolVar(f"soft_{relation}_{'_'.join(map(str, args))}")

    def enforce(expr):
        self.model.Add(expr).OnlyEnforceIf(b)

    if relation == "above":
        r1, _ = self.comp_vars[args[0]]
        r2, _ = self.comp_vars[args[1]]
        enforce(r1 > r2)
    elif relation == "below":
        r1, _ = self.comp_vars[args[0]]
        r2, _ = self.comp_vars[args[1]]
        enforce(r1 < r2)
    elif relation == "left_of":
        _, c1 = self.comp_vars[args[0]]
        _, c2 = self.comp_vars[args[1]]
        enforce(c1 < c2)
    elif relation == "right_of":
        _, c1 = self.comp_vars[args[0]]
        _, c2 = self.comp_vars[args[1]]
        enforce(c1 > c2)
    elif relation == "same_row":
        r1, _ = self.comp_vars[args[0]]
        r2, _ = self.comp_vars[args[1]]
        enforce(r1 == r2)
    elif relation == "same_column":
        _, c1 = self.comp_vars[args[0]]
        _, c2 = self.comp_vars[args[1]]
        enforce(c1 == c2)
    elif relation == "same_column_above":
        r1, c1 = self.comp_vars[args[0]]
        r2, c2 = self.comp_vars[args[1]]
        enforce(c1 == c2)
        enforce(r1 > r2)
    elif relation == "same_column_below":
        r1, c1 = self.comp_vars[args[0]]
        r2, c2 = self.comp_vars[args[1]]
        enforce(c1 == c2)
        enforce(r1 < r2)
    elif relation == "close_row":
        _soft_abs_within(self, self.comp_vars[args[0]][0], self.comp_vars[args[1]][0], args[2], b, f"{args[0]}_{args[1]}", "row")
    elif relation == "row_proximity":
        _soft_abs_within(self, self.comp_vars[args[1]][0], self.comp_vars[args[2]][0], args[0], b, f"{args[1]}_{args[2]}", "row")
    elif relation == "column_proximity":
        _soft_abs_within(self, self.comp_vars[args[1]][1], self.comp_vars[args[2]][1], args[0], b, f"{args[1]}_{args[2]}", "col")
    elif relation == "cluster_proximity":
        # args = [max_distance, c1, c2, ...]. Satisfied (b=1) iff every pair is
        # within max_distance in BOTH row and column. One penalty bool gates the
        # whole cluster, matching the hard cluster_proximity's all-or-nothing intent.
        max_distance, members = args[0], args[1:]
        for i in range(len(members)):
            for j in range(i + 1, len(members)):
                m1, m2 = members[i], members[j]
                _soft_abs_within(self, self.comp_vars[m1][0], self.comp_vars[m2][0], max_distance, b, f"{m1}_{m2}", "row")
                _soft_abs_within(self, self.comp_vars[m1][1], self.comp_vars[m2][1], max_distance, b, f"{m1}_{m2}", "col")

    self._soft_penalties.append((weight, b))
    return True
