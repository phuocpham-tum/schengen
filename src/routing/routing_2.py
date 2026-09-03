import heapq
import os
from collections import defaultdict
from enum import Enum
import matplotlib.pyplot as plt
import numpy as np
import random
from copy import deepcopy
from typing import Tuple
from collections import namedtuple
from src.placements.placer import CellType, Pin
from src.routing.cluster import ConnectedCluster, ClusterManager

from loguru import logger

DIRS = {(1, 0): "H", (-1, 0): "H", (0, 1): "V", (0, -1): "V"}


def astar_route(
    grid,
    start,
    goal,
    goal_candidates,
    net_id,
    bend_penalty=5,
    crossing_penalty=20,
    congestion_weight=1,
    same_net_overlap_reward=0.35,
):
    """
    Returns list of (x,y) from start to goal or None
    """
    goal_candidates = set(goal_candidates)  # points are immutable tuples, a shallow copy is enough
    try:
        goal_candidates.remove(start)
    except Exception:
        pass

    goal_in_candidates = goal in goal_candidates

    # Precompute the "one hop from a goal candidate" lookup: near_goal[p] is the goal
    # candidate reached from p by the first matching offset (same offset order as the
    # original 12-offset scan), so the per-popped-node lookahead is a single dict lookup.
    LOOKAHEAD_OFFSETS = [
        (1, 0), (-1, 0), (0, 1), (0, -1),
        (2, 0), (-2, 0), (0, 2), (0, -2),
        (3, 0), (-3, 0), (0, 3), (0, -3),
    ]
    near_goal = {}
    if goal_in_candidates:
        for dx, dy in LOOKAHEAD_OFFSETS:
            for gc in goal_candidates:
                near_goal.setdefault((gc[0] - dx, gc[1] - dy), gc)

    # The grid does not change during this search: compute the congestion of every cell
    # once instead of re-scanning the halo for every visited neighbor.
    congestion_map = grid.build_congestion_map(net_id, net_halo=2)

    # Ground-symbol cells: gnd! is never routed, so any other net crossing one reads as a
    # short to it. Discourage (don't block) traversing them -- a soft per-cell penalty lets
    # a boxed-in pin still escape through a gnd cell when it must, while making a trunk
    # route around rather than tunnel along the ground symbol.
    gnd_cells = getattr(grid, "gnd_cells", None) or frozenset()
    gnd_penalty = 3 * crossing_penalty

    if grid.is_blocked(start[0], start[1], net_id):
        logger.warning(f"Start point {start} is blocked for net {net_id}")
    if grid.is_blocked(goal[0], goal[1], net_id):
        logger.warning(f"Goal point {goal} is blocked for net {net_id}")

    def heuristic(a, b):
        # Euclidean distance
        euclidean = ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5
        hpwl = max(abs(a[0] - b[0]), abs(a[1] - b[1]))
        mahattan = abs(a[0] - b[0]) + abs(a[1] - b[1])
        if a[0] == b[0] or a[1] == b[1]:
            bends = 0
        else:
            bends = max(abs(a[0] - b[0]), abs(a[1] - b[1]))
        return euclidean + mahattan + hpwl + bends

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

        if current in goal_candidates and goal_in_candidates:
            m_path, turning_points = reconstruct_path(came_from, start, current)

            return (
                m_path,
                turning_points,
                cost_so_far[current],
                bend_so_far[current],
                crossing_so_far[current],
            )

        cx, cy = current

        next_node = near_goal.get(current)
        if next_node is not None:
            logger.debug(
                f"Next node {next_node} is a goal candidate for net {net_id}, setting priority to 0"
            )
            came_from[next_node] = current
            m_path, turning_points = reconstruct_path(came_from, start, next_node)
            assert start in m_path and next_node in m_path

            return (
                m_path,
                turning_points,
                cost_so_far[current],
                bend_so_far[current],
                crossing_so_far[current],
            )

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

            cell = grid.cells[nx][ny]
            if prev_dir and new_dir != prev_dir:
                step_cost += bend_penalty
                num_bends += 1

            if cell.type == CellType.WIRE and cell.net_id != net_id:
                step_cost += congestion_weight * grid.get_edge_congestion(
                    current, (nx, ny)
                )

            if cell.type == CellType.WIRE and len(cell.net_ids - {net_id}) > 0:
                step_cost += crossing_penalty
                num_crossings += 1

            step_cost += int(congestion_map[nx, ny]) * congestion_weight

            if cell.type == CellType.WIRE and cell.net_id == net_id:
                step_cost -= same_net_overlap_reward

            if (nx, ny) in gnd_cells:
                step_cost += gnd_penalty

            if step_cost < 0:
                step_cost = 0

            new_cost = cost_so_far[current] + step_cost
            next_node = (nx, ny)

            if next_node in goal_candidates and goal_in_candidates:
                logger.debug(
                    f"Next node {next_node} is a goal candidate for net {net_id}, setting priority to 0"
                )
                came_from[next_node] = current
                m_path, turning_points = reconstruct_path(came_from, start, next_node)
                return (
                    m_path,
                    turning_points,
                    cost_so_far[current],
                    bend_so_far[current],
                    crossing_so_far[current],
                )

            if next_node not in cost_so_far or (
                new_cost
                < cost_so_far[next_node]
                # and (
                #     (
                #         bend_so_far[next_node] == 0
                #         or num_bends + bend_so_far[current] <= bend_so_far[next_node]
                #     )
                #     and (
                #         crossing_so_far[next_node] == 0
                #         or num_crossings + crossing_so_far[current]
                #         <= crossing_so_far[next_node]
                #     )
                # )
            ):
                cost_so_far[next_node] = new_cost
                bend_so_far[next_node] = bend_so_far[current] + num_bends
                crossing_so_far[next_node] = crossing_so_far[current] + num_crossings

                priority = (
                    new_cost
                    + heuristic(next_node, goal)
                    + (bend_so_far[current] + num_bends)
                    + (crossing_so_far[current] + num_crossings)
                )

                heapq.heappush(pq, (priority, next_node, new_dir))
                came_from[next_node] = current

    logger.warning(f"Routing failed for net {net_id} from {start} to {goal}")
    return None, None, None, None, None


def densify_path(path):
    """Fill missing cells so consecutive points are grid-adjacent.

    The goal-candidate lookahead in astar_route can link two cells up to 3 apart
    (all moves are axis-aligned), so a reconstructed path may jump over intermediate
    cells. Downstream cell-adjacency logic (junction dots, dangling-wire pruning,
    connectivity) needs a contiguous path, so interpolate along each straight run.
    """
    if not path:
        return path
    out = [path[0]]
    for p in path[1:]:
        a = out[-1]
        if p == a:
            continue
        if a[0] == p[0]:                       # vertical run
            step = 1 if p[1] > a[1] else -1
            out.extend((a[0], y) for y in range(a[1] + step, p[1] + step, step))
        elif a[1] == p[1]:                     # horizontal run
            step = 1 if p[0] > a[0] else -1
            out.extend((x, a[1]) for x in range(a[0] + step, p[0] + step, step))
        else:                                  # non-collinear (shouldn't occur): keep
            out.append(p)
    return out


def reconstruct_path(came_from, start, goal):
    path = [goal]
    cur = goal

    # get turning points in the path, which are the points where the direction changes, and add intermediate points between turning points to make the path more smooth
    turning_points = [goal]
    while cur != start:
        if len(path) > 0:
            # add intermediate points between curr and path[-1] to make the path more smooth
            if cur[0] == path[-1][0]:  # vertical line
                for j in range(min(cur[1], path[-1][1]), max(cur[1], path[-1][1])):
                    path.append((cur[0], j))
            elif cur[1] == path[-1][1]:  # horizontal line
                for j in range(min(cur[0], path[-1][0]), max(cur[0], path[-1][0])):
                    path.append((j, cur[1]))

        path.append(cur)
        cur = came_from[cur]

    for idx, p in enumerate(path):
        cur_dir = [0, 0]  # (x, y) direction from current turning point to current point
        if p[0] > turning_points[-1][0]:
            cur_dir[0] = 1
        elif p[0] < turning_points[-1][0]:
            cur_dir[0] = -1

        if p[1] > turning_points[-1][1]:
            cur_dir[1] = 1
        elif p[1] < turning_points[-1][1]:
            cur_dir[1] = -1

        if 0 not in cur_dir:
            turning_points.append(path[idx - 1])
            turning_points.append(p)
            if idx + 1 < len(path):
                turning_points.append(path[idx + 1])

    path.append(start)
    path.reverse()

    diff = [
        abs(start[0] - turning_points[-1][0]),
        abs(start[1] - turning_points[-1][1]),
    ]

    if diff[0] < diff[1]:
        middle_point = (start[0], turning_points[-1][1])
    else:
        middle_point = (turning_points[-1][0], start[1])

    if middle_point != turning_points[-1]:
        turning_points.append(middle_point)

    turning_points.append(start)
    turning_points.reverse()
    return densify_path(path), turning_points


def steiner_topology(terminals, grid=None):
    """Build a Steiner-like topology by computing MST edges on Manhattan distance, HPWL, bends."""
    if len(terminals) < 2:
        return []

    terminals = [(int(t[0]), int(t[1])) for t in terminals]

    def _edge_score(u, v):
        manhattan = abs(u[0] - v[0]) + abs(u[1] - v[1])
        hpwl = max(abs(u[0] - v[0]), abs(u[1] - v[1]))
        if u[0] == v[0] or u[1] == v[1]:
            bends = 0
        else:
            bends = max(abs(u[0] - v[0]), abs(u[1] - v[1]))
        euclidean = ((u[0] - v[0]) ** 2 + (u[1] - v[1]) ** 2) ** 0.5
        return euclidean + hpwl + bends + manhattan

    visited = {terminals[0]}
    unvisited = set(terminals[1:])
    mst_edges = []

    while unvisited:
        best_edge = None
        best_score = None

        for u in visited:
            for v in unvisited:
                score = _edge_score(u, v)

                if best_score is None or score < best_score:
                    best_score = score
                    best_edge = (u, v)

        mst_edges.append(best_edge)
        visited.add(best_edge[1])
        unvisited.remove(best_edge[1])

    # sort edges based HPWL and bends, which are more critical for routing congestion and cost, to route those edges first and reduce the chance of routing failure due to congestion and lack of space
    mst_edges.sort(
        key=lambda edge: (
            max(abs(edge[0][0] - edge[1][0]), abs(edge[0][1] - edge[1][1])),  # HPWL
            0 if edge[0][0] == edge[1][0] or edge[0][1] == edge[1][1] else 1,  # bends
            abs(edge[0][0] - edge[1][0])
            + abs(edge[0][1] - edge[1][1]),  # Manhattan distance
        )
    )

    return mst_edges


def _clearest_track(grid, lo, hi, span_lo, span_hi, axis, max_block_frac=0.15, prefer="median"):
    """Pick the best track coordinate in [lo, hi] for a trunk spanning
    [span_lo, span_hi]. A component keep-out on the track is disqualifying above
    `max_block_frac`; among routable tracks, minimise a cost that penalises running
    parallel to *other* nets' wire (so rails spread onto distinct tracks instead of
    piling into one band) and a positional pull. `prefer` sets the pull: "median"
    (default) toward the pins' median, "top" toward the highest track (largest
    coord), "bottom" toward the lowest — used to keep the supply rail on top.
    Returns None if every candidate track is too obstructed by components."""
    median = (lo + hi) / 2
    width = span_hi - span_lo
    if width <= 0:
        return int(round(median))
    step = max(1, width // 200)  # sample the span for a cheap estimate
    best_t = best_cost = None
    for t in range(int(lo), int(hi) + 1):
        blocked = wired = total = 0
        for c in range(span_lo, span_hi + 1, step):
            x, y = (c, t) if axis == "h" else (t, c)
            total += 1
            if grid.is_blocked(x, y):
                blocked += 1
            elif grid.wire_mask[x, y]:  # another net already occupies this track
                wired += 1
        if not total or blocked / total > max_block_frac:
            continue
        if prefer == "top":
            pull = hi - t
        elif prefer == "bottom":
            pull = t - lo
        elif isinstance(prefer, (int, float)):
            pull = abs(t - prefer)  # bias toward a specific target track
        else:
            pull = abs(t - median)
        cost = 1000 * blocked + 10 * wired + pull
        if best_cost is None or cost < best_cost:
            best_cost, best_t = cost, t
    return best_t


def trunk_topology(pins, grid=None, min_pins=4, max_block_frac=0.15, prefer="median"):
    """Topology for a many-pin net (a rail): one straight trunk on a single clear
    track with a perpendicular stub per pin, instead of a wandering MST. The trunk
    axis is the wider spread; the track is the clearest line near the pins' median
    (or, per `prefer`, biased to the top/bottom — used to keep the supply rail on
    top).

    Returns (edges, trunk_points) where trunk_points[i] is pin i's projection onto
    the trunk, or None to fall back to steiner_topology (too few pins, or no clear
    trunk track exists)."""
    if grid is None or len(pins) < min_pins:
        return None
    if os.environ.get("SCHENGEN_NO_TRUNK"):  # kill-switch for A/B and tuning
        return None
    pts = [(int(p[0]), int(p[1])) for p in pins]
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    horizontal = (max(xs) - min(xs)) >= (max(ys) - min(ys))
    if horizontal:
        track = _clearest_track(grid, min(ys), max(ys), min(xs), max(xs), "h", max_block_frac, prefer)
        if track is None:
            return None
        proj = [(x, track) for x in xs]
        order = sorted(range(len(pts)), key=lambda i: xs[i])
    else:
        track = _clearest_track(grid, min(xs), max(xs), min(ys), max(ys), "v", max_block_frac)
        if track is None:
            return None
        proj = [(track, y) for y in ys]
        order = sorted(range(len(pts)), key=lambda i: ys[i])

    edges = []
    stub_keys = set()  # edges connecting a pin down to the trunk (routed with a
    # low bend penalty so they drop straight instead of doglegging to save a bend)
    ordered_proj = [proj[i] for i in order]
    for a, b in zip(ordered_proj, ordered_proj[1:]):  # trunk chain, in-order
        if a != b:
            edges.append((a, b))
    for i in range(len(pts)):  # perpendicular stubs
        if pts[i] != proj[i]:
            edges.append((pins[i], proj[i]))
            stub_keys.add(frozenset({(int(pins[i][0]), int(pins[i][1])),
                                     (int(proj[i][0]), int(proj[i][1]))}))
    return edges, proj, stub_keys


def t_junction_topology(pins):
    """Crossbar-and-stem wiring for a 3-pin T-junction net drawn the way designers
    do: two collinear pins (e.g. a differential pair's two tied source pins, or two
    tied drains) form one straight crossbar, and the third pin branches off it as a
    single perpendicular stem at its projection onto the crossbar. Placement is used
    as given -- this only fixes the wire shape, forcing the crossbar straight instead
    of letting congestion route the stem *through* an anchor. Returns
    (edges, extra_points) or None to fall back to steiner_topology."""
    if os.environ.get("SCHENGEN_NO_TJUNCTION"):  # kill-switch for A/B
        return None
    if len(pins) != 3:
        return None
    pts = [(int(p[0]), int(p[1])) for p in pins]
    for axis in ("h", "v"):
        coord = (lambda p: p[1]) if axis == "h" else (lambda p: p[0])
        other = (lambda p: p[0]) if axis == "h" else (lambda p: p[1])
        for i in range(3):  # pts[i] is the candidate stem; the other two are the crossbar
            a, b = [pts[j] for j in range(3) if j != i]
            if coord(a) != coord(b):
                continue  # not collinear -> no crossbar on this axis
            stem = pts[i]
            track = coord(a)
            lo, hi = sorted((other(a), other(b)))
            proj_o = min(max(other(stem), lo), hi)  # clamp branch point into the crossbar span
            proj = (proj_o, track) if axis == "h" else (track, proj_o)
            edges = [(a, b)]  # straight crossbar
            if stem != proj:
                edges.append((stem, proj))  # perpendicular stem to the crossbar
            return edges, [proj]
    return None


def nearest_point(src, points, grid=None):
    sx, sy = src

    parallel_points_x = [p for p in points if p[0] == sx]
    parallel_points_y = [p for p in points if p[1] == sy]
    if len(parallel_points_x) > 0 and len(parallel_points_y) > 0:
        # if there are points in the same row and column, prefer those that are in the same row or column without blockage
        min_x = min(parallel_points_x, key=lambda p: abs(p[1] - sy))
        min_y = min(parallel_points_y, key=lambda p: abs(p[0] - sx))
        if min_x < min_y:
            return min_x
        else:
            return min_y

    if len(parallel_points_x) > 0 and len(parallel_points_y) == 0:
        min_x = min(parallel_points_x, key=lambda p: abs(p[1] - sy))
        return min_x

    if len(parallel_points_y) > 0 and len(parallel_points_x) == 0:
        min_y = min(parallel_points_y, key=lambda p: abs(p[0] - sx))
        return min_y

    def get_distance(p):
        manhattan = abs(sx - p[0]) + abs(sy - p[1])
        euclidean = ((sx - p[0]) ** 2 + (sy - p[1]) ** 2) ** 0.5

        hpwl = max(abs(sx - p[0]), abs(sy - p[1]))
        if sx == p[0] or sy == p[1]:
            bends = 0
        else:
            bends = max(abs(sx - p[0]), abs(sy - p[1]))
        return euclidean + hpwl + bends + manhattan

    return min(points, key=get_distance)


def smooth_path(path):
    """
    Post-process: merge collinear segments and remove redundant waypoints.
    Turns a staircase into the minimum-bend equivalent path.
    """
    if len(path) < 3:
        return path

    def direction(a, b):
        return (b[0] - a[0], b[1] - a[1])

    smoothed = [path[0]]
    for i in range(1, len(path) - 1):
        prev_dir = direction(path[i - 1], path[i])
        next_dir = direction(path[i], path[i + 1])
        if prev_dir != next_dir:
            smoothed.append(path[i])  # keep only true bend points
    smoothed.append(path[-1])
    return smoothed


def prune_dangling_wire(pins, routed_segments, turning_points):
    """Remove wire that dead-ends at a non-pin cell.

    A rail's perpendicular stub can attach to the trunk a couple of cells short of
    its projected end when the exact cell is blocked (see trunk_topology). That
    leaves the trunk drawn past the last real attachment -- a dangling overhang --
    plus a second junction dot a cell away from the real one. Such a tail is
    redundant by construction (it connects nothing), so peel back every cell of
    degree <= 1 that is not a pin. Peeling a leaf never disconnects the rest and
    pins are never removed, so connectivity is preserved.

    Returns cleaned (routed_segments, turning_points), index-aligned as received.
    """
    pin_set = {(int(p[0]), int(p[1])) for p in pins}
    alive = set()
    for seg in routed_segments:
        for x, y in seg:
            alive.add((int(x), int(y)))

    # Anchor each pin to a real wire cell. A stub can attach to the trunk (or reach
    # a gate) a cell short of the exact pin coordinate; if the pin cell itself isn't
    # on any wire, protect the nearest alive cell instead. Without this the pin's
    # connecting wire has no protected endpoint and the leaf-peel below can eat it
    # back to nothing, leaving the terminal unconnected (the c1/c2, m8-gate bug).
    if alive:
        for p in list(pin_set):
            if p not in alive:
                pin_set.add(min(alive, key=lambda c: abs(c[0] - p[0]) + abs(c[1] - p[1])))

    def degree(c):
        x, y = c
        return sum(1 for n in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)) if n in alive)

    def strands_a_pin(c):
        # True if c is the sole surviving link of an adjacent pin -- removing it
        # would leave that pin with no wire (a floating terminal).
        x, y = c
        for n in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if n in pin_set and degree(n) <= 1:
                return True
        return False

    removed = set()
    changed = True
    while changed:
        changed = False
        for c in list(alive):
            if c in pin_set:
                continue
            if degree(c) <= 1 and not strands_a_pin(c):
                alive.discard(c)
                removed.add(c)
                changed = True

    if not removed:
        return routed_segments, turning_points

    new_segments, new_turning_points = [], []
    for seg, tp in zip(routed_segments, turning_points):
        cleaned = [c for c in seg if (int(c[0]), int(c[1])) not in removed]
        if len(cleaned) == len(seg):
            new_segments.append(seg)
            new_turning_points.append(tp)
        elif len(cleaned) >= 2:  # tail trimmed: re-collapse to bend points
            new_segments.append(cleaned)
            new_turning_points.append(smooth_path(cleaned))
        # else: the whole segment was dangling -> drop it
    return new_segments, new_turning_points


def _seg_cells(polys):
    """All grid cells covered by a list of axis-aligned polylines."""
    cells = set()
    for poly in polys:
        for (x0, y0), (x1, y1) in zip(poly, poly[1:]):
            if x0 == x1:
                lo, hi = sorted((y0, y1))
                cells.update((x0, y) for y in range(lo, hi + 1))
            elif y0 == y1:
                lo, hi = sorted((x0, x1))
                cells.update((x, y0) for x in range(lo, hi + 1))
    return cells


def _poly_cells(poly):
    return _seg_cells([poly])


def _min_pin_dist(pins, cells):
    return {(int(p[0]), int(p[1])): (min(abs(x - int(p[0])) + abs(y - int(p[1])) for x, y in cells) if cells else 10 ** 9)
            for p in pins}


def _pins_all_connected(cells, pins):
    """True if every pin's nearest wire cell is in one connected component."""
    if not cells:
        return not pins
    anchors = []
    for p in pins:
        pp = (int(p[0]), int(p[1]))
        anchors.append(pp if pp in cells else min(cells, key=lambda c: abs(c[0] - pp[0]) + abs(c[1] - pp[1])))
    if not anchors:
        return True
    seen = {anchors[0]}
    stack = [anchors[0]]
    while stack:
        x, y = stack.pop()
        for nb in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if nb in cells and nb not in seen:
                seen.add(nb)
                stack.append(nb)
    return all(a in seen for a in anchors)


def _dedupe_polys(segments, pins):
    """Rebuild a net's wire as the minimal tree over its pins: grid-adjacency graph of
    the covered cells, spanning forest (drops redundant cycle edges), then peel every
    degree-1 cell that isn't a pin (drops redundant dangling branches). Removes wire
    drawn twice where routed edges overlap, keeping only pin-to-pin geometry."""
    if not segments:
        return segments
    nodes = _seg_cells(segments)
    for seg in segments:  # keep bare bend endpoints of non-axis segments, if any
        for p in seg:
            nodes.add((int(p[0]), int(p[1])))
    adj = defaultdict(set)
    for (x, y) in nodes:
        for nb in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if nb in nodes:
                adj[(x, y)].add(nb)
                adj[nb].add((x, y))
    tree = defaultdict(set)
    visited = set()
    for s in nodes:
        if s in visited:
            continue
        visited.add(s)
        stack = [s]
        while stack:
            u = stack.pop()
            for v in adj[u]:
                if v not in visited:
                    visited.add(v)
                    tree[u].add(v)
                    tree[v].add(u)
                    stack.append(v)
    pinset = set()
    for p in pins or []:
        pp = (int(p[0]), int(p[1]))
        pinset.add(pp if pp in nodes else (min(nodes, key=lambda c: abs(c[0] - pp[0]) + abs(c[1] - pp[1])) if nodes else pp))

    def deg(n):
        return len(tree[n])

    changed = True
    while changed:
        changed = False
        for n in [k for k in tree if tree[k]]:
            if deg(n) == 1 and n not in pinset:
                m = next(iter(tree[n]))
                tree[n].discard(m)
                tree[m].discard(n)
                changed = True

    def walk(a, b, used):
        path = [a, b]
        used.add(frozenset((a, b)))
        prev, cur = a, b
        while deg(cur) == 2:
            nxt = next((n for n in tree[cur] if n != prev), None)
            if nxt is None:
                break
            used.add(frozenset((cur, nxt)))
            path.append(nxt)
            prev, cur = cur, nxt
        merged = [path[0]]
        for i in range(1, len(path) - 1):
            (x0, y0), (x1, y1), (x2, y2) = path[i - 1], path[i], path[i + 1]
            if (x0 == x1 == x2) or (y0 == y1 == y2):
                continue
            merged.append(path[i])
        merged.append(path[-1])
        return merged

    used = set()
    result = []
    live = [n for n in tree if tree[n]]
    for c in [n for n in live if deg(n) != 2]:
        for nb in list(tree[c]):
            if frozenset((c, nb)) not in used:
                result.append(walk(c, nb, used))
    for n in live:
        for nb in tree[n]:
            if frozenset((n, nb)) not in used:
                result.append(walk(n, nb, used))
                break
    return result


def _simplify_poly(poly, blocked, pinset, other_cells=frozenset()):
    """Reduce bends: re-route each pin-to-pin span as a straight or single-L path,
    keeping every pin on the wire, accepted only if it adds NO device overlap and NO
    new collinear overlap with another net's wire (>1 new shared cell) the original
    span didn't have. Falls back to the original span otherwise."""
    poly = [tuple(p) for p in poly]
    if len(poly) < 3:
        return poly
    orig_dev = _poly_cells(poly) & blocked
    orig_other = _poly_cells(poly) & other_cells
    cells = []
    for a, b in zip(poly, poly[1:]):
        if a[0] == b[0]:
            st = 1 if b[1] >= a[1] else -1
            seq = [(a[0], y) for y in range(a[1], b[1] + st, st)]
        else:
            st = 1 if b[0] >= a[0] else -1
            seq = [(x, a[1]) for x in range(a[0], b[0] + st, st)]
        cells += seq if not cells else seq[1:]
    mand = [cells[0]] + [c for c in cells[1:-1] if c in pinset] + [cells[-1]]
    dedup = [mand[0]]
    for c in mand[1:]:
        if c != dedup[-1]:
            dedup.append(c)
    out = []
    for wa, wb in zip(dedup, dedup[1:]):
        cands = []
        if wa[0] == wb[0] or wa[1] == wb[1]:
            cands.append([wa, wb])
        else:
            cands.append([wa, (wb[0], wa[1]), wb])
            cands.append([wa, (wa[0], wb[1]), wb])
        chosen = None
        for path in cands:
            pc = _poly_cells(path)
            if (pc & blocked) - orig_dev:  # no new device-body overlap
                continue
            if len((pc & other_cells) - orig_other) > 1:  # no new collinear overlap w/ another net
                continue
            chosen = path
            break
        if chosen is None:
            ia, ib = cells.index(wa), cells.index(wb)
            chosen = cells[ia:ib + 1]
        out += chosen[1:] if out else chosen
    merged = [out[0]]
    for k in range(1, len(out) - 1):
        (x0, y0), (x1, y1), (x2, y2) = out[k - 1], out[k], out[k + 1]
        if (x0 == x1 == x2) or (y0 == y1 == y2):
            continue
        merged.append(out[k])
    merged.append(out[-1])
    return merged


def clean_net_wires(turning_points, pins, blocked, other_cells=frozenset()):
    """Post-route wire cleanup for one net: drop redundant duplicate/loop segments and
    reduce bends, returning polylines. GUARDED: a step is kept only if it leaves every
    pin no farther from the wire and all pins in one connected component -- otherwise
    that net keeps its original wire, so cleanup can never disconnect a terminal.
    `other_cells` (already-routed nets' cells) keeps the bend-reduction from
    straightening this wire on top of another net. Run before routed_nets /
    intersection dots are derived so all three stay consistent."""
    if not turning_points or not pins:
        return turning_points
    pinset = {(int(p[0]), int(p[1])) for p in pins}

    def _safe(orig, new):
        oc, nc = _seg_cells(orig), _seg_cells(new)
        if not _pins_all_connected(nc, pins):
            return orig
        od, nd = _min_pin_dist(pins, oc), _min_pin_dist(pins, nc)
        if any(nd[k] > od[k] + 1 for k in od):
            return orig
        return new

    # Iterate to convergence: dedupe/simplify are not idempotent -- one pass can
    # leave a residual detour (e.g. a hairpin whose two legs only become a shortcut
    # after the first cleanup) that a second pass removes. Bounded to a few passes.
    result = turning_points
    for _ in range(4):
        step = _safe(result, _dedupe_polys(result, pins))
        step = _safe(step, [_simplify_poly(s, blocked, pinset, other_cells) for s in step])
        if step == result:
            break
        result = step
    return result


def route_net(
    grid,
    net_id,
    pins,
    pin_name_map,
    bend_penalty=5,
    crossing_penalty=20,
    routed_points=None,
    turning_points=None,
    is_tjunction=False,
    preconnected=None,
    trunk_prefer="median",
):
    """
    Route a net connecting the given pins on the grid.

    :param grid: the Grid object representing the routing area
    :param net_id: the identifier of the net being routed
    :param pins: a list of (x, y) tuples representing the pin locations to connect
    :param pin_name_map: a dictionary mapping each pin to its name, used for logging purposes
    :param bend_penalty: the cost added for each bend in the route
    :param crossing_penalty: the cost added for crossing existing wires of other nets
    :return: a tuple of (total_cost, routed_paths) where total_cost is the total routing cost, and routed_paths is a dictionary containing the set of routed points and list of routed segments.
    """

    # A net with a diode's pre-connected gate/drain pair uses the MST directly (the pair
    # is joined by the rendered short, not a trunk/crossbar), so members attach to the
    # nearest of the two terminals via the cluster seeded below.
    preconnected = [((int(a[0]), int(a[1])), (int(b[0]), int(b[1]))) for a, b in (preconnected or [])]
    tjunction = t_junction_topology(pins) if (is_tjunction and not preconnected) else None
    trunk = trunk_topology(pins, grid=grid, prefer=trunk_prefer) if (tjunction is None and not preconnected) else None
    stub_keys = set()  # trunk stub edges get a low bend penalty (see below)
    if tjunction is not None:
        mst_edges, extra_points = tjunction
        for tp in extra_points:  # synthetic branch point needs a name for the lookups below
            pin_name_map.setdefault(tp, "t_junction")
    elif trunk is not None:
        mst_edges, trunk_points, stub_keys = trunk
        # synthetic trunk points need names for the pin_name_map lookups below
        for tp, orig in zip(trunk_points, pins):
            pin_name_map.setdefault(tp, pin_name_map.get(orig, "trunk"))
    else:
        mst_edges = steiner_topology(pins, grid=grid)

    routed_points = set() if routed_points is None else routed_points
    turning_points = []
    routed_segments = []
    total_cost = 0
    num_bends = 0
    num_crossings = 0

    cluster_manager = ClusterManager()
    cluster_manager.add_points_to_cluster(routed_points)
    # Seed each diode's gate+drain as one already-connected cluster: an MST edge between
    # them is skipped, and every other member routes to whichever terminal is nearest.
    for a, b in preconnected:
        cluster_manager.add_points_to_cluster([a, b])

    def route_edge(u, v, u_candidates, v_candidates, u_name=None, v_name=None, bp=None):
        nonlocal total_cost, num_bends, num_crossings
        _bend_penalty = bend_penalty if bp is None else bp
        # Route in a single direction: toward the side with the larger goal-candidate
        # set, so the search can terminate on any already-routed point of that side
        # (see docs/adr/0003, S2 — previously both directions were routed and the
        # cheaper path kept, doubling the A* work).
        if len(v_candidates) >= len(u_candidates):
            src, dst, dst_candidates = u, v, v_candidates
        else:
            src, dst, dst_candidates = v, u, u_candidates

        path, x_turning_points, cost, bend_cost, crossing_cost = astar_route(
            grid,
            src,
            dst,
            dst_candidates,
            net_id,
            _bend_penalty,
            crossing_penalty,
            same_net_overlap_reward=100,
        )
        if cost is None:
            logger.warning(
                f"Routing failed for edge from {u_name} at {u} to (fixed) desc: {v_name} at {v} for net {net_id}"
            )
            return []

        if path is None:
            routed_paths = {
                "routed_points": routed_points,
                "routed_segments": routed_segments,
                "total_bend_cost": num_bends,
                "total_crossing_cost": num_crossings,
                "turning_points": turning_points,
            }
            return -1, routed_paths

        # logger.debug(
        #     f"++ Routing edge from {u_name} at {u} to (fixed) desc: {v_name} at {v} with cost {cost}, bend_cost {bend_cost}, crossing: {crossing_cost}"
        # )
        total_cost += cost
        num_bends += bend_cost
        num_crossings += crossing_cost

        grid.mark_wire(path, net_id)
        routed_points.update(path)
        turning_points.append(x_turning_points)
        routed_segments.append(path)
        return path

    def find_shortest_edges(points_a, points_b):
        min_cost = None
        best_edge = None
        for u in points_a:
            for v in points_b:
                if u[0] == v[0] or u[1] == v[1]:
                    mathatance = abs(u[0] - v[0]) + abs(u[1] - v[1])
                    bends = 0 if u[0] == v[0] or u[1] == v[1] else 10
                    hpwl = max(abs(u[0] - v[0]), abs(u[1] - v[1]))
                    euclidean = ((u[0] - v[0]) ** 2 + (u[1] - v[1]) ** 2) ** 0.5
                    cost = mathatance + hpwl + bends + euclidean
                    if min_cost is None or cost < min_cost:
                        min_cost = cost
                        best_edge = (u, v)
        return best_edge

    # Trunk stubs (pin -> trunk) route with a low bend penalty so they drop
    # straight to the rail instead of doglegging sideways to save a bend, which
    # otherwise leaves redundant horizontal runs along a shared-gate row.
    stub_bend_penalty = max(5, bend_penalty // 10)
    for u, v in mst_edges:
        u_name = pin_name_map[u]
        v_name = pin_name_map[v]

        edge_bp = stub_bend_penalty if frozenset(
            {(int(u[0]), int(u[1])), (int(v[0]), int(v[1]))}
        ) in stub_keys else None

        u_cluster = cluster_manager.get_cluster_for_point(u)
        v_cluster = cluster_manager.get_cluster_for_point(v)

        if u_cluster is None and v_cluster is None:
            u_ = u
            v_ = v
            pathx = route_edge(u_, v_, [], [], u_name=u_name, v_name=v_name, bp=edge_bp)
            cluster_manager.add_points_to_cluster(pathx)

        elif u_cluster is not None and v_cluster is None:
            u_ = (
                nearest_point(v, u_cluster.points, grid)
                if len(u_cluster.points) > 0
                else u
            )
            v_ = v
            pathx = route_edge(
                u_, v_, u_cluster.points, [], u_name=u_name, v_name=v_name, bp=edge_bp
            )
            cluster_manager.add_points_to_cluster(pathx)
        elif v_cluster is not None and u_cluster is None:
            v_ = (
                nearest_point(u, v_cluster.points, grid)
                if len(v_cluster.points) > 0
                else v
            )
            u_ = u
            pathx = route_edge(
                u_, v_, [], v_cluster.points, u_name=u_name, v_name=v_name, bp=edge_bp
            )

        else:
            if bool(u_cluster.points & v_cluster.points):
                print("u and v are already in the same cluster, no need to route")
                continue

            best_edge = find_shortest_edges(u_cluster.points, v_cluster.points)
            if best_edge is None:
                best_edge = (u, v)
            u_ = best_edge[0]
            v_ = best_edge[1]
            pathx = route_edge(
                u_, v_, u_cluster.points, v_cluster.points, u_name=u_name, v_name=v_name, bp=edge_bp
            )
            cluster_manager.add_points_to_cluster(pathx)

    # Recover any pin the topology failed to attach: a per-edge A* aims at one cluster
    # point and, if that hop is blocked, route_edge drops the pin (a missing wire). Retry
    # each still-unconnected pin against the net's *entire* routed wire as goal candidates
    # -- far more reachable targets than the single point the first attempt aimed at.
    # Only ever adds a connection; a pin that is genuinely boxed in stays as before.
    if routed_points and not os.environ.get("SCHENGEN_NO_PIN_RECOVER"):  # kill-switch for A/B
        for _p in pins:
            _pp = (int(_p[0]), int(_p[1]))
            if _pp in routed_points:
                continue
            _goal = nearest_point(_pp, routed_points, grid)
            route_edge(_pp, _goal, [], set(routed_points),
                       u_name=pin_name_map.get(_pp), v_name="net-wire")

    # Peel dangling non-pin wire tails (e.g. a rail trunk drawn past its last real
    # stub attachment), which otherwise render as a redundant segment plus a stray
    # junction dot a cell away from the real one.
    if not os.environ.get("SCHENGEN_NO_PRUNE"):  # kill-switch for A/B
        routed_segments, turning_points = prune_dangling_wire(pins, routed_segments, turning_points)

    routed_paths = {
        "routed_points": routed_points,
        "turning_points": turning_points,
        "routed_segments": routed_segments,
        "total_bend_cost": num_bends,
        "total_crossing_cost": num_crossings,
    }

    return total_cost, routed_paths


def route_net_parallel_priory(
    grid, net_id, pins, pin_names, bend_penalty=500, crossing_penalty=200, is_tjunction=False, preconnected=None, trunk_prefer="median"
):
    """
    Routing the net with same the same x or y coordinates first, which can help to reduce the congestion and improve the routability.
    Remove routed pins from the pins list, and route the remaining pins with route_net.
    """
    pin_name_map = {pin: pin_names[idx] for idx, pin in enumerate(pins)}
    _pins = deepcopy(pins)
    return route_net(
        grid,
        net_id,
        _pins,
        pin_name_map,
        bend_penalty,
        crossing_penalty,
        routed_points=None,
        turning_points=None,
        is_tjunction=is_tjunction,
        preconnected=preconnected,
        trunk_prefer=trunk_prefer,
    )
