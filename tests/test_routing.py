from src.routing import *
from src.routing.routing_2 import prune_dangling_wire, smooth_path, densify_path


def test_routing_example2():
    grid = Grid(200, 100)
    scale = 10

    # Place components
    components = [
        # row, col
        [8, 3],
        (2, 5),
        (5, 9),
        (2, 9),
        (8, 7),
        (7, 5),
        (7, 9),
        (8, 11),
        (4, 11),
        (1, 11),
        (8, 1),
        (3, 3),
    ]
    for comp in components:
        place_component_reversed(
            grid, comp[1] * scale, comp[0] * scale, 9, 9, keepout=0
        )

    nets = {
        "n1": [
            (5, 7, "nmos", "source", "bottom"),
            (9, 7, "nmos", "source", "bottom"),
            (7, 8, "nmos", "drain", "top"),
        ],
        "n2": [
            (9, 5, "nmos", "drain", "bottom"),
            (9, 7, "nmos", "drain", "top"),
            (11, 4, "nmos", "gate", "left"),
        ],
    }

    nets = update_net_positions(nets, grid)
    for net_id, pins in nets.items():
        cost = route_net(grid, net_id, pins)
        print(f"routing cost: ", cost)

    visualize_grid(grid, filename="outputs/test_routing_example2.png")


def test_prune_dangling_wire_removes_trunk_overhang():
    # A rail trunk (x=10, y0..y5) whose top cell (10,5) has no attachment: the two
    # stubs tee onto the trunk at y2 and y4, so (10,5) is a dangling overhang.
    trunk = [(10, y) for y in range(0, 6)]
    stub_b = [(13, 2), (12, 2), (11, 2), (10, 2)]
    stub_c = [(13, 4), (12, 4), (11, 4), (10, 4)]
    segments = [trunk, stub_b, stub_c]
    turning_points = [smooth_path(s) for s in segments]
    pins = [(10, 0), (13, 2), (13, 4)]  # trunk bottom + the two stub pins

    new_segs, _ = prune_dangling_wire(pins, segments, turning_points)
    cells = {c for seg in new_segs for c in seg}

    assert (10, 5) not in cells  # dangling overhang removed
    for p in pins:  # connectivity preserved
        assert tuple(p) in cells
    assert all(c in cells for c in trunk[:-1])  # rest of trunk kept
    # idempotent: a second pass peels nothing more
    again, _ = prune_dangling_wire(pins, new_segs, [smooth_path(s) for s in new_segs])
    assert {c for s in again for c in s} == cells


def test_prune_dangling_wire_noop_when_clean():
    # Both ends of a straight segment are pins: nothing to peel.
    seg = [(0, 0), (1, 0), (2, 0), (3, 0)]
    pins = [(0, 0), (3, 0)]
    new_segs, new_tps = prune_dangling_wire(pins, [seg], [smooth_path(seg)])
    assert new_segs == [seg]


def test_densify_path_fills_lookahead_gap():
    # The astar goal-candidate lookahead can link cells up to 3 apart; densify_path
    # must fill the intermediate cells so the path is grid-contiguous.
    assert densify_path([(375, 90), (375, 93)]) == [(375, 90), (375, 91), (375, 92), (375, 93)]
    assert densify_path([(0, 0), (3, 0)]) == [(0, 0), (1, 0), (2, 0), (3, 0)]
    # already contiguous -> unchanged; duplicates collapsed
    assert densify_path([(0, 0), (0, 1), (0, 2)]) == [(0, 0), (0, 1), (0, 2)]
    assert densify_path([(5, 5), (5, 5)]) == [(5, 5)]


def test_prune_does_not_strand_a_pin():
    # A pin whose only wire is a dead-end stub must keep at least one link, even
    # though the stub connects nothing (the routing gap it reveals is a separate bug).
    seg = [(0, 0), (0, 1), (0, 2)]  # pin (0,0); (0,2) dead-ends (non-pin)
    pins = [(0, 0)]
    new_segs, _ = prune_dangling_wire(pins, [seg], [smooth_path(seg)])
    cells = {c for s in new_segs for c in s}
    assert (0, 0) in cells                 # pin never removed
    assert (0, 1) in cells                 # its link is protected -> not stranded
