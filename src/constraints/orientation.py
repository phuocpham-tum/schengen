from src.utils.netlist_analyzer import NetlistAnalyzer
from loguru import logger


def initialize_two_terminal_component_orientations(
    schematic, analyzer: NetlistAnalyzer
) -> None:
    """Initialize orientations of two-terminal components based on their connections."""

    for tc in analyzer.caps + analyzer.resistors:
        grid_tc = schematic.find_component(tc.name)
        grid_tc.orientation = None  # reset orientation to None before counting

    # traverse to all nets in the netlist, for each net, if it connects to a two-terminal component, count how many components are above and below it, and assign orientation based on majority
    for net in analyzer.nets:
        if net == "gnd!":
            continue

        orientation_counts = []
        for component_name, _ in analyzer.get_single_net_connections(net):
            if component_name[0].lower() in [
                "c",
                "r",
            ]:  # only consider connections to two-terminal components
                comp = schematic.find_component(component_name)
                orientation_counts.append(comp.orientation)

        # find the most common orientation among the connected components, and assign it to the two-terminal component if it is not None
        if orientation_counts:
            most_common_orientation = max(
                set(orientation_counts), key=orientation_counts.count
            )
            if most_common_orientation is not None:
                for component_name, _ in analyzer.get_single_net_connections(net):
                    if component_name[0].lower() in [
                        "c",
                        "r",
                    ]:  # only consider connections to two-terminal components
                        # comp = schematic.find_component(component_name)
                        # orientation_counts.append(comp.orientation)

                        comp = schematic.find_component(component_name)
                        if (
                            comp.orientation is None
                        ):  # only assign orientation to two-terminal components that haven't been assigned yet
                            comp.orientation = most_common_orientation
                        if comp.orientation != most_common_orientation:
                            logger.warning(
                                f"Component {comp.name} has orientation {comp.orientation} which is different from the majority orientation {most_common_orientation} of its connected components. This may indicate a potential issue in the schematic."
                            )
                            comp.orientation = most_common_orientation  # assign the majority orientation to this component to maintain consistency


def assign_two_terminal_component_orientation(
    schematic, analyzer: NetlistAnalyzer
) -> None:
    """Assign orientation to two-terminal components based on their connections."""

    for tc in analyzer.caps + analyzer.resistors:
        tc_name = tc.name

        all_nets = tc.get_all_connected_nets()
        num_pos = 0
        num_neg = 0

        grid_tc = schematic.find_component(tc_name)
        for net in all_nets:
            if net == "gnd!":
                continue
            for component_name, _ in analyzer.get_single_net_connections(net):
                comp = schematic.find_component(component_name)
                if comp.row >= 0:
                    if comp.row > grid_tc.row:
                        num_pos += 1
                    else:
                        num_neg += 1

        if num_pos > num_neg:
            logger.debug(
                f"(grid) two-terminal component: {tc_name}, num_pos: {num_pos}, num_neg: {num_neg}, orientation: 0"
            )
            grid_tc.orientation = 1
        else:
            logger.debug(
                f"(grid) two-terminal component: {tc_name}, num_pos: {num_pos}, num_neg: {num_neg}, orientation: 1"
            )
            grid_tc.orientation = 0
