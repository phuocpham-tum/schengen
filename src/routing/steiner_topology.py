import math
import itertools
from collections import defaultdict


def _is_routable_point(grid, point: tuple[int, int]) -> bool:
    """Return True when a grid point can be used as a Steiner candidate."""
    if grid is None:
        return True

    x, y = point

    # Prefer explicit bounds checks when available.
    if hasattr(grid, "in_bounds") and not grid.in_bounds(x, y):
        return False

    # Keep compatibility with Grid.is_blocked(x, y, net_id) and simpler variants.
    if hasattr(grid, "is_blocked"):
        try:
            return not grid.is_blocked(x, y, None)
        except TypeError:
            return not grid.is_blocked(x, y)

    return True


def steiner_topology(terminals: list[tuple[int, int]], grid=None) -> dict:
    """
    Find a near-optimal Steiner tree topology for a set of terminal points.

    Minimizes:
      - Total Manhattan (HPWL) wire length
      - Number of bends
      - Estimated wire crossingsx

    Strategy:
      1. Build a Hanan grid (candidate Steiner point locations)
      2. Use a greedy MST-based approach with Steiner point insertion
      3. Post-process to reduce bends via L-shape routing

    Args:
        terminals: List of (x, y) tuples representing net terminals.
        grid: Optional routing grid. When provided, Steiner candidate points are
            filtered to avoid blocked cells.

    Returns:
        A dict with:
          - 'steiner_points': additional points added
          - 'edges': list of ((x1,y1),(x2,y2)) wire segments
          - 'total_wirelength': total Manhattan distance
          - 'num_bends': estimated bend count
          - 'topology': adjacency list of the tree
    """
    if not terminals:
        return {
            "steiner_points": [],
            "edges": [],
            "total_wirelength": 0,
            "num_bends": 0,
            "topology": {},
        }
    if len(terminals) == 1:
        return {
            "steiner_points": [],
            "edges": [],
            "total_wirelength": 0,
            "num_bends": 0,
            "topology": {terminals[0]: []},
        }

    terminals = [(int(p[0]), int(p[1])) for p in terminals]

    # ── Step 1: Build Hanan grid ──────────────────────────────────────────────
    # The optimal Steiner tree in Manhattan metric always has Steiner points
    # at Hanan grid intersections (intersections of x/y coords of terminals).
    xs = sorted(set(p[0] for p in terminals))
    ys = sorted(set(p[1] for p in terminals))
    hanan_points = [
        (x, y)
        for x in xs
        for y in ys
        if (x, y) not in terminals and _is_routable_point(grid, (x, y))
    ]
    candidates = list(terminals) + hanan_points

    # ── Step 2: Prim's MST on full candidate set ──────────────────────────────
    def manhattan(a, b):
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    # Build MST using Prim's algorithm (O(n²), fine for typical net sizes)
    in_tree = {candidates[0]}
    remaining = set(candidates[1:])
    edges_mst = []
    node_dist = {p: (manhattan(candidates[0], p), candidates[0]) for p in remaining}

    while remaining:
        # Pick the closest node to the current tree
        best = min(remaining, key=lambda p: node_dist[p][0])
        d, parent = node_dist[best]
        edges_mst.append((parent, best))
        in_tree.add(best)
        remaining.remove(best)

        # Update distances
        for p in remaining:
            d2 = manhattan(best, p)
            if d2 < node_dist[p][0]:
                node_dist[p] = (d2, best)

    # ── Step 3: Prune Steiner points that don't help ──────────────────────────
    # Build adjacency list
    adj = defaultdict(set)
    for u, v in edges_mst:
        adj[u].add(v)
        adj[v].add(u)

    # Remove leaf Steiner points (degree-1 non-terminals) iteratively
    terminal_set = set(terminals)
    changed = True
    while changed:
        changed = False
        leaves = [p for p in list(adj) if p not in terminal_set and len(adj[p]) == 1]
        for leaf in leaves:
            neighbor = next(iter(adj[leaf]))
            adj[neighbor].discard(leaf)
            del adj[leaf]
            changed = True

    # ── Step 4: Rectilinear edge decomposition ────────────────────────────────
    # Each logical edge becomes one or two axis-aligned segments (L-shape).
    # Choose the bend direction that minimises crossings with other edges.
    used_nodes = set(adj.keys())
    steiner_points = [p for p in used_nodes if p not in terminal_set]

    # Collect all final edges from adjacency list (undirected, deduplicated)
    seen_edges = set()
    logical_edges = []
    for u in adj:
        for v in adj[u]:
            key = (min(u, v), max(u, v))
            if key not in seen_edges:
                seen_edges.add(key)
                logical_edges.append((u, v))

    # Expand each logical edge into rectilinear segments
    def rectilinear_segments(u, v, prefer_horizontal_first=True):
        """Return one or two axis-aligned segments for edge u→v."""
        if u[0] == v[0] or u[1] == v[1]:
            return [(u, v)]  # Already axis-aligned, no bend needed
        mid = (v[0], u[1]) if prefer_horizontal_first else (u[0], v[1])
        return [(u, mid), (mid, v)]

    # Estimate crossing cost for a given bend choice
    def crossing_estimate(segs_a, all_segs):
        """Count how many segments in all_segs cross any segment in segs_a."""

        def seg_bbox(s):
            (x1, y1), (x2, y2) = s
            return min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2)

        def segments_cross(s1, s2):
            # Only H–V crossings matter (both axis-aligned)
            (x1a, y1a), (x2a, y2a) = s1
            (x1b, y1b), (x2b, y2b) = s2
            h, v = None, None
            if y1a == y2a and x1b == x2b:
                h, v = s1, s2
            elif x1a == x2a and y1b == y2b:
                h, v = s2, s1
            else:
                return False
            hx1, hx2 = min(h[0][0], h[1][0]), max(h[0][0], h[1][0])
            hy = h[0][1]
            vx = v[0][0]
            vy1, vy2 = min(v[0][1], v[1][1]), max(v[0][1], v[1][1])
            return hx1 < vx < hx2 and vy1 < hy < vy2

        count = 0
        for sa in segs_a:
            for sb in all_segs:
                if segments_cross(sa, sb):
                    count += 1
        return count

    # Choose bend direction per edge to minimise crossings
    wire_segments = []
    for u, v in logical_edges:
        if u[0] == v[0] or u[1] == v[1]:
            wire_segments.extend([(u, v)])
            continue

        segs_h = rectilinear_segments(u, v, prefer_horizontal_first=True)
        segs_v = rectilinear_segments(u, v, prefer_horizontal_first=False)

        cost_h = crossing_estimate(segs_h, wire_segments)
        cost_v = crossing_estimate(segs_v, wire_segments)

        chosen = segs_h if cost_h <= cost_v else segs_v
        wire_segments.extend(chosen)

    # ── Step 5: Compute metrics ───────────────────────────────────────────────
    def seg_length(s):
        return manhattan(s[0], s[1])

    total_wl = sum(seg_length(s) for s in wire_segments)

    # A bend occurs at every intermediate point in a multi-segment logical edge
    num_bends = sum(
        1
        for segs in [
            rectilinear_segments(u, v)
            for u, v in logical_edges
            if u[0] != v[0] and u[1] != v[1]
        ]
        for _ in [1]  # each diagonal logical edge contributes 1 bend
    )

    def count_crossings(segs):
        count = 0
        for i, sa in enumerate(segs):
            for sb in segs[i + 1 :]:
                (x1a, y1a), (x2a, y2a) = sa
                (x1b, y1b), (x2b, y2b) = sb
                h, v = None, None
                if y1a == y2a and x1b == x2b:
                    h, v = sa, sb
                elif x1a == x2a and y1b == y2b:
                    h, v = sb, sa
                else:
                    continue
                hx1, hx2 = min(h[0][0], h[1][0]), max(h[0][0], h[1][0])
                hy = h[0][1]
                vx = v[0][0]
                vy1, vy2 = min(v[0][1], v[1][1]), max(v[0][1], v[1][1])
                if hx1 < vx < hx2 and vy1 < hy < vy2:
                    count += 1
        return count

    num_crossings = count_crossings(wire_segments)

    # Build final topology adjacency list (tree structure)
    topology = {p: list(adj[p]) for p in adj}

    return {
        "steiner_points": steiner_points,
        "edges": wire_segments,
        "total_wirelength": total_wl,
        "num_bends": num_bends,
        "num_crossings": num_crossings,
        "topology": topology,
    }


if __name__ == "__main__":
    terminals = [(0, 0), (4, 0), (2, 3), (4, 3)]
    result = steiner_topology(terminals)

    print("Steiner points:", result["steiner_points"])
    print("Total wirelength:", result["total_wirelength"])
    print("Bends:", result["num_bends"])
    print("Crossings:", result["num_crossings"])
    for seg in result["edges"]:
        print("  wire:", seg)
