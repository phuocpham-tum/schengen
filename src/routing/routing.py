import heapq
from collections import defaultdict
from enum import Enum
import matplotlib.pyplot as plt
import numpy as np
import random
from copy import deepcopy
from typing import Tuple
from collections import namedtuple
from src.placements.placer import CellType, Pin

from loguru import logger

DIRS = {(1, 0): "H", (-1, 0): "H", (0, 1): "V", (0, -1): "V"}


def proximity_penalty(grid, x, y, net_id, radius=2, weight=10):
    """
    Penalize routing close to wires of other nets.
    """
    penalty = 0

    for dx in range(-radius, radius + 1):
        for dy in range(-radius, radius + 1):
            if dx == 0 and dy == 0:
                continue

            nx, ny = x + dx, y + dy
            if not grid.in_bounds(nx, ny):
                continue

            cell = grid.cells[nx][ny]
            if cell.type == CellType.WIRE and cell.net_id != net_id:
                dist = abs(dx) + abs(dy)
                if dist > 0:
                    penalty += weight / dist

    return penalty


def astar_route(
    grid,
    start,
    goal,
    net_id,
    bend_penalty=5,
    crossing_penalty=20,
    congestion_weight=1,
    same_net_overlap_reward=0.35,
):
    """
    Returns list of (x,y) from start to goal or None
    """

    if grid.is_blocked(start[0], start[1], net_id):
        logger.warning(f"Start point {start} is blocked for net {net_id}")
    if grid.is_blocked(goal[0], goal[1], net_id):
        logger.warning(f"Goal point {goal} is blocked for net {net_id}")

    def heuristic(a, b):
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    pq = [(0, start, None)]  # (priority, (x, y), direction_from_parent)
    came_from = {}
    cost_so_far = {start: 0}
    bend_so_far = {start: 0}
    crossing_so_far = {start: 0}

    while pq:
        _, current, prev_dir = heapq.heappop(pq)

        if current == goal:
            m_path, turning_points = reconstruct_path(came_from, start, goal)
            return (
                m_path,
                turning_points,
                cost_so_far[current],
                bend_so_far[current],
                crossing_so_far[current],
            )

        cx, cy = current

        for dx, dy in DIRS:
            nx, ny = cx + dx, cy + dy

            if not grid.in_bounds(nx, ny):
                continue

            if grid.is_blocked(nx, ny, net_id):
                continue

            new_dir = DIRS[(dx, dy)]
            step_cost = 1

            num_bends = 0
            num_crossings = 0

            if prev_dir and new_dir != prev_dir:
                step_cost += bend_penalty
                num_bends += 1

            cell = grid.cells[nx][ny]
            if cell.type == CellType.WIRE and cell.net_id == net_id:
                step_cost -= same_net_overlap_reward

            if cell.type == CellType.WIRE and cell.net_id != net_id:
                step_cost += congestion_weight * grid.get_edge_congestion(
                    current, (nx, ny)
                )

            if cell.type == CellType.WIRE and len(cell.net_ids - {net_id}) > 0:
                step_cost += crossing_penalty
                num_crossings += 1

            step_cost += (
                grid.calculate_surrounding_congestion(nx, ny, net_id=net_id, net_halo=2)
                * congestion_weight
            )

            if step_cost < 0.05:
                step_cost = 0.05

            new_cost = cost_so_far[current] + step_cost
            next_node = (nx, ny)

            if next_node not in cost_so_far or (
                new_cost < cost_so_far[next_node]
                and (
                    (
                        bend_so_far[next_node] == 0
                        or num_bends + bend_so_far[current] <= bend_so_far[next_node]
                    )
                    and (
                        crossing_so_far[next_node] == 0
                        or num_crossings + crossing_so_far[current]
                        <= crossing_so_far[next_node]
                    )
                )
            ):
                cost_so_far[next_node] = new_cost
                bend_so_far[next_node] = bend_so_far[current] + num_bends
                crossing_so_far[next_node] = crossing_so_far[current] + num_crossings

                priority = new_cost + heuristic(next_node, goal)
                heapq.heappush(pq, (priority, next_node, new_dir))
                came_from[next_node] = current

    logger.warning(f"Routing failed for net {net_id} from {start} to {goal}")
    return None, None, None, None, None


def reconstruct_path(came_from, start, goal):
    path = []
    cur = goal

    # get turning points in the path, which are the points where the direction changes, and add intermediate points between turning points to make the path more smooth
    turning_points = []
    while cur != start:
        if len(path) > 0:
            # add intermediate points between curr and path[-1] to make the path more smooth
            if cur[0] == path[-1][0]:  # vertical line
                for j in range(min(cur[1], path[-1][1]), max(cur[1], path[-1][1])):
                    path.append((cur[0], j))
            elif cur[1] == path[-1][1]:  # horizontal line
                for j in range(min(cur[0], path[-1][0]), max(cur[0], path[-1][0])):
                    path.append((j, cur[1]))

        if len(path) > 1:
            prev_dir = (path[-1][0] - path[-2][0], path[-1][1] - path[-2][1])
            new_dir = (cur[0] - path[-1][0], cur[1] - path[-1][1])
            if prev_dir != new_dir:
                turning_points.append(path[-1])

        path.append(cur)
        cur = came_from[cur]
    path.append(start)
    path.reverse()
    return path, turning_points


def nearest_point(src, points):
    sx, sy = src
    return min(points, key=lambda p: abs(p[0] - sx) + abs(p[1] - sy))


def _sorted_target_candidates(
    terminal: Tuple[int, int],
    routed_points: set,
    bend_penalty: float,
    max_candidates: int = 64,
) -> list[Tuple[float, Tuple[int, int]]]:
    """Return candidate target points sorted by distance + bend estimate, with a small bonus for branching points."""
    if len(routed_points) == 0:
        return []

    tx, ty = terminal
    nearest = sorted(
        routed_points,
        key=lambda p: abs(p[0] - tx) + abs(p[1] - ty),
    )[:max_candidates]

    def score_target(target):
        x, y = target
        manhattan_dist = abs(x - tx) + abs(y - ty)
        bend_estimate = 0 if (x == tx or y == ty) else 1

        local_degree = 0
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            if (x + dx, y + dy) in routed_points:
                local_degree += 1

        return manhattan_dist + 0.8 * bend_penalty * bend_estimate - 0.35 * local_degree

    scored = [(score_target(target), target) for target in nearest]
    scored.sort(key=lambda item: item[0])
    return scored


def steiner_topology(terminals):
    """Build a Steiner-like topology by computing MST edges on Manhattan distance."""
    if len(terminals) < 2:
        return []

    visited = {terminals[0]}
    unvisited = set(terminals[1:])
    mst_edges = []

    while unvisited:
        best_edge = None
        best_dist = None

        for u in visited:
            for v in unvisited:
                dist = abs(u[0] - v[0]) + abs(u[1] - v[1])
                if best_dist is None or dist < best_dist:
                    best_dist = dist
                    best_edge = (u, v)

        mst_edges.append(best_edge)
        visited.add(best_edge[1])
        unvisited.remove(best_edge[1])

    return mst_edges


def route_net(grid, net_id, pins, bend_penalty=5, crossing_penalty=20):
    """
    Route a net connecting the given pins on the grid.

    :param grid: the Grid object representing the routing area
    :param net_id: the identifier of the net being routed
    :param pins: a list of (x, y) tuples representing the pin locations to connect
    :param bend_penalty: the cost added for each bend in the route
    :param crossing_penalty: the cost added for crossing existing wires of other nets
    :return: a tuple of (total_cost, routed_paths) where total_cost is the total routing cost, and routed_paths is a dictionary containing the set of routed points and list of routed segments.
    """

    unique_pins = []
    seen = set()
    for pin in pins:
        if pin not in seen:
            unique_pins.append(pin)
            seen.add(pin)

    if len(unique_pins) == 0:
        routed_paths = {
            "routed_points": set(),
            "routed_segments": [],
            "total_bend_cost": 0,
            "total_crossing_cost": 0,
        }
        return 0, routed_paths

    if len(unique_pins) == 1:
        routed_paths = {
            "routed_points": {unique_pins[0]},
            "routed_segments": [],
            "total_bend_cost": 0,
            "total_crossing_cost": 0,
        }
        return 0, routed_paths

    seed_terminal = unique_pins[0]
    routed_points = {seed_terminal}
    turning_points = set()
    routed_segments = []
    total_cost = 0
    total_bend_cost = 0
    total_crossing_cost = 0

    remaining_terminals = set(unique_pins[1:])

    while len(remaining_terminals) > 0:
        terminal_plans = []
        for terminal in remaining_terminals:
            candidates = _sorted_target_candidates(
                terminal,
                routed_points,
                bend_penalty=bend_penalty,
                max_candidates=64,
            )
            if len(candidates) == 0:
                continue
            terminal_plans.append((candidates[0][0], terminal, candidates))

        if len(terminal_plans) == 0:
            routed_paths = {
                "routed_points": routed_points,
                "routed_segments": routed_segments,
                "total_bend_cost": total_bend_cost,
                "total_crossing_cost": total_crossing_cost,
            }
            return -1, routed_paths

        routed_this_round = False

        for _, terminal, candidates in sorted(terminal_plans, key=lambda item: item[0]):
            for _, target in candidates[:10]:
                if target == terminal:
                    continue

                path, x_turning_points, cost, bend_cost, crossing_cost = astar_route(
                    grid,
                    terminal,
                    target,
                    net_id,
                    bend_penalty,
                    crossing_penalty,
                )

                if path is None:
                    continue

                total_cost += cost
                total_bend_cost += bend_cost
                total_crossing_cost += crossing_cost
                grid.mark_wire(path, net_id)
                routed_points.update(path)
                turning_points.update(set(x_turning_points))
                routed_segments.append(path)
                remaining_terminals.remove(terminal)
                routed_this_round = True
                break

            if routed_this_round:
                break

        if not routed_this_round:
            routed_paths = {
                "routed_points": routed_points,
                "routed_segments": routed_segments,
                "total_bend_cost": total_bend_cost,
                "total_crossing_cost": total_crossing_cost,
            }
            return -1, routed_paths

    routed_paths = {
        "routed_points": routed_points,
        "routed_segments": routed_segments,
        "total_bend_cost": total_bend_cost,
        "total_crossing_cost": total_crossing_cost,
    }

    return total_cost, routed_paths


def route_net_parallel_priory(grid, net_id, pins, bend_penalty=5, crossing_penalty=20):
    """
    Routing the net with same the same x or y coordinates first, which can help to reduce the congestion and improve the routability.
    Remove routed pins from the pins list, and route the remaining pins with route_net.
    """
    _pins = deepcopy(pins)
    routed_points = set()
    total_cost = 0
    total_bend_cost = 0
    total_crossing_cost = 0

    keep_pins = []
    routed_segments = []
    # for i in range(len(_pins)):
    #     for j in range(i + 1, len(_pins)):
    #         if _pins[i][0] == _pins[j][0] or _pins[i][1] == _pins[j][1]:
    #             path, _, cost = astar_route(
    #                 grid,
    #                 _pins[i],
    #                 _pins[j],
    #                 net_id,
    #                 bend_penalty,
    #                 crossing_penalty,
    #             )
    #             if path is not None:
    #                 grid.mark_wire(path, net_id)
    #                 routed_points.update(path)
    #                 total_cost += cost
    #                 _pins.pop(j)
    #                 a = _pins.pop(i)
    #                 keep_pins.append(a)
    #                 routed_segments.append(path)
    #                 break

    _pins = keep_pins + _pins
    additional_cost, additional_routed_paths = route_net(
        grid, net_id, _pins, bend_penalty, crossing_penalty
    )

    additional_routed_paths["routed_segments"] += routed_segments

    # expend additional_routed_paths["routed_points"] with routed_segments
    for segment in routed_segments:
        additional_routed_paths["routed_points"].update(segment)

    return total_cost + additional_cost, additional_routed_paths


def routing_net_multiple_priory(
    grid, net_id, pins, sorted_pin_locations, bend_penalty=5, crossing_penalty=20
):
    _pins = deepcopy(pins)
    name2pin = defaultdict(list)
    total_cost = 0
    routed_points = set()
    for pin in sorted_pin_locations[net_id]:
        if pin.component.comp_type.endswith("diode"):
            name2pin[pin.component.name].append(pin.name)

    for component_name, pin_names in name2pin.items():
        if "gate" in pin_names and "drain" in pin_names:

            index1 = None
            for ip, p in enumerate(sorted_pin_locations[net_id]):
                if p.component.name == component_name and p.name == "gate":
                    index1 = ip
                    break

            index2 = None
            for ip, p in enumerate(sorted_pin_locations[net_id]):
                if p.component.name == component_name and p.name == "drain":
                    index2 = ip
                    break

            if index1 is None or index2 is None:
                continue

            initial_pin = _pins[index1]
            routed_points = {initial_pin}
            total_cost = 0

            pin = _pins[index2]

            target = nearest_point(pin, routed_points)
            path, _, cost = astar_route(
                grid, pin, target, net_id, bend_penalty, crossing_penalty
            )
            if path is None:
                # return 1_000_000, routed_points
                print(f"routing failed for net {net_id} at diode gate-drain connection")
            total_cost += cost
            grid.mark_wire(path, net_id)
            routed_points.update(path)

            # _pins.pop(index2)
            _pins.pop(index1)
            break

    additional_cost, additional_routed_points = route_net_parallel_priory(
        grid, net_id, _pins, bend_penalty, crossing_penalty
    )

    return total_cost + additional_cost, routed_points.union(additional_routed_points)
