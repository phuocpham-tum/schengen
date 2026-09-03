import heapq
from collections import defaultdict
from enum import Enum
import matplotlib.pyplot as plt
import numpy as np
import random
from copy import deepcopy
from typing import Tuple
from collections import namedtuple
from loguru import logger

Pin = namedtuple(
    "Pin", "component name"
)  # component is the Component object, name is the pin name (e.g. "gate", "drain", "source", "center_dot")


class CellType(Enum):
    EMPTY = 0
    COMPONENT = 1
    WIRE = 2

    INNER_KEEP_OUT = 3


class GridCell:
    def __init__(self):
        self.type = CellType.EMPTY
        self.net_id = None
        self.net_ids = set()


class Grid:
    def __init__(self, width, height):
        self.w = width
        self.h = height
        self.cells = [[GridCell() for _ in range(height)] for _ in range(width)]
        self.edge_congestion = defaultdict(int)
        # numpy mirrors of the WIRE state of self.cells, kept in sync by mark_wire /
        # place_component / place_port. Used to compute the surrounding-congestion map
        # once per A* search instead of per visited neighbor (see docs/adr/0003).
        self.wire_mask = np.zeros((width, height), dtype=bool)
        self.net_code = np.zeros((width, height), dtype=np.int32)
        self._net_codes = {}  # net_id -> positive int code used in self.net_code

    def in_bounds(self, x, y):
        return 0 <= x < self.w and 0 <= y < self.h

    def is_blocked(self, x, y, net_id=None):
        if not self.in_bounds(x, y):
            return True
        cell = self.cells[x][y]
        if cell.type == CellType.COMPONENT:
            return True

        if cell.type == CellType.INNER_KEEP_OUT:
            return False

        return False

    def calculate_surrounding_congestion(self, x, y, net_id=None, net_halo=1):
        num_different_nets = 0
        for dx in range(-net_halo, net_halo + 1):
            for dy in range(-net_halo, net_halo + 1):
                if dx == 0 and dy == 0:
                    continue
                nx, ny = x + dx, y + dy
                if self.in_bounds(nx, ny):
                    neighbor_cell = self.cells[nx][ny]
                    if (
                        neighbor_cell.type == CellType.WIRE
                        and neighbor_cell.net_id != net_id
                    ):
                        num_different_nets += 1
        return num_different_nets

    def build_congestion_map(self, net_id, net_halo=1):
        """
        Compute calculate_surrounding_congestion(x, y, net_id, net_halo) for every cell
        at once: congestion_map[x, y] == number of WIRE cells of *other* nets in the
        (2*net_halo+1)^2 window around (x, y), excluding (x, y) itself.

        The grid does not change during a single A* search, so the map is built once
        per search and looked up in O(1) per neighbor.
        """
        other = self.wire_mask.astype(np.int32)
        code = self._net_codes.get(net_id)
        if code is not None:
            other -= (self.wire_mask & (self.net_code == code)).astype(np.int32)

        padded = np.pad(other, net_halo)
        congestion_map = np.zeros_like(other)
        for dx in range(2 * net_halo + 1):
            for dy in range(2 * net_halo + 1):
                congestion_map += padded[dx : dx + self.w, dy : dy + self.h]
        congestion_map -= other  # exclude the center cell itself
        return congestion_map

    def _edge_key(self, u, v):
        return (u, v) if u <= v else (v, u)

    def get_edge_congestion(self, u, v):
        return self.edge_congestion[self._edge_key(u, v)]

    def update_congestion(self, path, amount=3):
        for i in range(len(path) - 1):
            u = path[i]
            v = path[i + 1]
            self.edge_congestion[self._edge_key(u, v)] += amount

    def mark_wire(self, path, net_id):
        net_code = self._net_codes.setdefault(net_id, len(self._net_codes) + 1)
        for x, y in path:
            cell = self.cells[x][y]
            cell.type = CellType.WIRE
            cell.net_id = net_id
            cell.net_ids.add(net_id)
            self.wire_mask[x, y] = True
            self.net_code[x, y] = net_code

            # Mark surrounding cells as keepout for other nets
            net_halo = 1
            for dx in range(-net_halo, net_halo):
                for dy in range(-net_halo, net_halo):
                    if dx == 0 and dy == 0:
                        continue
                    nx, ny = x + dx, y + dy
                    if self.in_bounds(nx, ny):
                        neighbor_cell = self.cells[nx][ny]
                        if neighbor_cell.type == CellType.EMPTY:
                            neighbor_cell.type = CellType.WIRE
                            neighbor_cell.net_id = net_id
                            self.wire_mask[nx, ny] = True
                            self.net_code[nx, ny] = net_code

        self.update_congestion(path)


def place_port(grid, x, y, w, h, open_for_routing=True):
    """
    Place a port on the grid with given parameters.
    The port occupies a rectangle defined by (x, y, w, h), and is marked as EMPTY type to allow routing through it.

    :param grid: the Grid object representing the routing area
    :param x: the x coordinate of the top-left corner of the port
    :param y: the y coordinate of the top-left corner of the port
    :param w: the width of the port
    :param h: the height of the port
    :return: None
    """
    for i in range(x, x + w):
        for j in range(y, y + h):
            if grid.in_bounds(i, j):
                grid.cells[i][j].type = CellType.EMPTY
                grid.wire_mask[i, j] = False

    min_x = x + 4
    max_x = x + 6
    min_y = y + 4
    max_y = y + 6

    for i in range(x, x + w):
        for j in range(y, y + h):
            if not grid.in_bounds(i, j):
                continue  # a port drawn at the grid edge can overrun; clip it like the
                          # EMPTY-marking loop above already does, instead of IndexError (#82)
            grid.cells[i][j].type = CellType.COMPONENT
            grid.wire_mask[i, j] = False
            if i > min_x and i < max_x:
                grid.cells[i][j].type = CellType.INNER_KEEP_OUT

            if j > min_y and j < max_y:
                grid.cells[i][j].type = CellType.INNER_KEEP_OUT

    if not open_for_routing:
        for i in range(x + 3, x + 7):
            for j in range(y + 3, y + 7):
                if grid.in_bounds(i, j):
                    grid.cells[i][j].type = CellType.COMPONENT
                    grid.wire_mask[i, j] = False


def place_component(
    grid,
    x,
    y,
    w,
    h,
    keepout=1,
    drill_through=False,
    vertical_barrier=True,
    horizontal_barrier=False,
    y_offset="bottom",
    max_keepout=4,
):
    """
    Place a component on the grid with given parameters.
    The component occupies a rectangle defined by (x, y, w, h).

    :param grid: the Grid object representing the routing area
    :param x: the x coordinate of the top-left corner of the component
    :param y: the y coordinate of the top-left corner of the component
    :param w: the width of the component
    :param h: the height of the component
    :param keepout: the keepout distance around the component, which will be marked as COMPONENT type to prevent routing through them.
    :param drill_through: whether to create a drill-through hole in the middle of the component, which can be used for routing wires through the component.
    :param vertical_barrier: whether to create a vertical barrier in the middle of the component, which can be used to prevent routing through the middle of the component.
    :param horizontal_barrier: whether to create a horizontal barrier in the middle of the component, which can be used to prevent routing through the middle of the component.
    :param y_offset: the offset for the y coordinate, either "bottom" or "middle"
    :return: None
    """
    # max_keepout = 4

    assert keepout >= 0
    if max_keepout != 0:
        assert keepout <= max_keepout
    assert y_offset in ["bottom", "middle"]

    for i in range(x - max_keepout, x + w + max_keepout):
        for j in range(y - max_keepout, y + h + max_keepout):
            if grid.in_bounds(i, j):
                grid.cells[i][j].type = CellType.EMPTY
                grid.wire_mask[i, j] = False

    min_x = x + 4
    max_x = x + 6
    min_y = y + 4
    max_y = y + 6

    for i in range(x - keepout, x + w + keepout):
        start_j = y - keepout if y_offset == "bottom" else y - keepout + int(h / 2)
        for j in range(start_j, y + h + keepout):
            if grid.in_bounds(i, j):
                grid.cells[i][j].type = CellType.COMPONENT
                grid.wire_mask[i, j] = False

            if drill_through:
                if i > min_x and i < max_x:
                    if grid.in_bounds(i, j):
                        grid.cells[i][j].type = CellType.INNER_KEEP_OUT

                if j > min_y and j < max_y:
                    if grid.in_bounds(i, j):
                        grid.cells[i][j].type = CellType.INNER_KEEP_OUT

    if max_keepout != 0 and vertical_barrier:
        for i in range(x + 3, x + 8):
            if grid.in_bounds(i, y + 6):
                grid.cells[i][y + 6].type = CellType.COMPONENT
                grid.wire_mask[i, y + 6] = False
            if grid.in_bounds(i, y + 4):
                grid.cells[i][y + 4].type = CellType.COMPONENT
                grid.wire_mask[i, y + 4] = False

    if max_keepout != 0 and horizontal_barrier:
        for j in range(y + 3, y + 8):
            if grid.in_bounds(x + 6, j):
                grid.cells[x + 6][j].type = CellType.COMPONENT
                grid.wire_mask[x + 6, j] = False
            if grid.in_bounds(x + 4, j):
                grid.cells[x + 4][j].type = CellType.COMPONENT
                grid.wire_mask[x + 4, j] = False


def translate_to_grid_positions(
    pins: list[Pin], scale: int = 10
) -> list[Tuple[int, int]]:

    new_pins = []
    for pin in pins:
        comp, pin_name = pin
        x, y, comp_type, component_orientation = (
            comp.col,
            comp.row,
            comp.comp_type,
            comp.orientation,
        )

        X0 = x * scale
        X1 = x * scale + int(scale / 2)
        X2 = x * scale + scale

        Y0 = y * scale
        Y1 = y * scale + int(scale / 2)
        Y2 = y * scale + scale

        if comp_type in [
            "nmos",
            "nmos_normal",
            "nmos_diode",
            "npn",
            "npn_normal",
            "npn_diode",
        ]:
            if pin_name in ["source"]:
                new_pins.append((X1, Y0))
            elif pin_name in ["drain"]:
                new_pins.append((X1, Y2))
            elif pin_name in ["gate"]:
                if component_orientation == 1:
                    new_pins.append((X0, Y1))
                else:
                    new_pins.append((X2, Y1))

        elif comp_type in [
            "pmos",
            "pmos_normal",
            "pmos_diode",
            "pnp",
            "pnp_normal",
            "pnp_diode",
        ]:
            if pin_name in ["source"]:
                new_pins.append((X1, Y2))
            elif pin_name in ["drain"]:
                new_pins.append((X1, Y0))
            elif pin_name in ["gate"]:
                if component_orientation == 1:
                    new_pins.append((X0, Y1))
                else:
                    new_pins.append((X2, Y1))
        elif comp_type in ["port"]:
            new_pins.append((X1, Y1))
        elif comp_type in ["cap_vertical", "resistor"]:
            if component_orientation == 0:
                if pin_name in ["pos"]:
                    new_pins.append((X1, Y2))
                elif pin_name in ["neg"]:
                    new_pins.append((X1, Y0))
            elif component_orientation == 1:
                if pin_name in ["neg"]:
                    new_pins.append((X1, Y2))
                elif pin_name in ["pos"]:
                    new_pins.append((X1, Y0))
        else:
            raise ValueError(f"unknown component type: {comp_type=} ")

    return new_pins
