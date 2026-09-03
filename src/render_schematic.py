"""Render a schengen result JSON to a PNG image, without the web UI.

This is the CLI twin of the web renderer (src/ui/static/js/schengen.js): it consumes
the same result JSON contract (component_placement_data, turning_points/routed_nets,
intersection_points) and the same component sprite PNGs under src/ui/static/, so both
renderers always agree on what a schematic looks like (see docs/adr/0004).

Differences from the web export, by design:
- wires are drawn as clean polylines from `turning_points` (the web UI plots the
  densified `routed_nets` points as dots; polylines look better in exported PNGs)
- output size is deterministic (the web export inherits the browser viewport width)

Usage:
    python -m src.render_schematic result1.json [result2.json ...] [-o OUT] [--cell-px N]

With multiple inputs, -o must be a directory (default: alongside each input).
"""

import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

# sprite root = src/ui/static, resolved relative to this file so it works from any cwd
_STATIC_DIR = Path(__file__).resolve().parent / "ui" / "static"

# Same mapping as getImageUrlForComponentType (src/ui/static/js/schengen.js:491-517),
# including the quirk that nmos_diode/pmos_diode use the *normal* MOS sprites.
# Value: (sprite for orientation != 1, sprite for orientation == 1)
_SPRITES = {
    "cap_vertical": ("cap.png", "cap.png"),
    "resistor": ("two-terminals/resistor.png", "two-terminals/resistor_1.png"),
    "nmos_normal": ("nmos_normal_gate_right.png", "nmos_normal_gate_left.png"),
    "nmos_diode": ("nmos_normal_gate_right.png", "nmos_normal_gate_left.png"),
    "pmos_normal": ("pmos_normal_gate_right.png", "pmos_normal_gate_left.png"),
    "pmos_diode": ("pmos_normal_gate_right.png", "pmos_normal_gate_left.png"),
    "pnp_normal": ("bjt/pnp_normal_base_right.png", "bjt/pnp_normal_base_left.png"),
    "pnp_diode": ("bjt/pnp_diode_base_right.png", "bjt/pnp_diode_base_left.png"),
    "npn_normal": ("bjt/npn_normal_base_right.png", "bjt/npn_normal_base_left.png"),
    "npn_diode": ("bjt/npn_diode_base_right.png", "bjt/npn_diode_base_left.png"),
    "gnd": ("gnd.png", "gnd.png"),
    "port": ("port.png", "port.png"),
}
_DEFAULT_SPRITE = ("port.png", "port.png")

# Same palette as drawRoutedNets (schengen.js:658-663), but assigned in stable net
# order instead of shuffled, so batch renders are deterministic.
_NET_COLORS = [
    "#F55A07", "#410252", "#A41600", "#E60DC1", "#004761",
    "#2F8900", "#945701", "#009478", "#F50A1F", "#F5BB00",
    "#7701F5", "#D4C359", "#4C7DA2", "#937F6A", "#A85F5C",
    "#5C4C28", "#0E14DC", "#8AC944", "#876AD6", "#EEACC3",
    "#5C4C28", "#9CACDA", "#000000", "#968fff", "#ff8f96",
]

_LABEL_COLOR = "#2600ff"  # .cell-label-component-name (src/ui/static/css/index.css)


def _load_font(size: int) -> ImageFont.ImageFont:
    """Bold sans font, mirroring the web export's 'bold 12px sans-serif' labels."""
    try:
        from matplotlib import font_manager

        path = font_manager.findfont("DejaVu Sans:bold")
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()


def _label_for(comp_name: str) -> str:
    # same rules as drawComponents (schengen.js:460-470)
    if comp_name.startswith("terminal_gnd!"):
        return ""
    if comp_name.startswith("terminal_"):
        return comp_name.replace("terminal_", "")
    return comp_name


def render_schematic_result(
    result_path: str,
    output_path: str | None = None,
    cell_px: int = 100,
    num_rows: int = 25,
    num_cols: int = 40,
) -> str:
    """Render a schengen result JSON to PNG. Returns the output path.

    Coordinates follow the web renderer: components at (col, row) with row 0 at the
    bottom; routing coordinates have 100 units per grid cell, origin bottom-left.
    """
    with open(result_path) as f:
        data = json.load(f)

    components = data.get("component_placement_data", {})
    turning_points = data.get("turning_points", {})
    routed_nets = data.get("routed_nets", {})
    intersection_points = data.get("intersection_points", {})

    # net -> wire colour (same order the wire loop below assigns), and each
    # diode-connected device -> its net (gate == drain in the netlist), so the
    # rendered gate->drain short can match the colour of the net it belongs to.
    net_color = {net: _NET_COLORS[i % len(_NET_COLORS)] for i, net in enumerate(routed_nets.keys())}
    diode_net = {}
    for _line in data.get("netlist", "").splitlines():
        _p = _line.split()
        if len(_p) >= 3 and _p[0][:1].lower() in ("m", "q") and _p[1] == _p[2]:
            diode_net[_p[0]] = _p[1]

    width, height = num_cols * cell_px, num_rows * cell_px
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)

    def to_canvas(x: float, y: float) -> tuple[float, float]:
        # routing coords (100 units/cell, origin bottom-left) -> pixels (origin top-left)
        s = cell_px / 100.0
        return x * s, height - y * s

    # 1) wires first, components on top — same z-order as the web export
    #    (exportSchematicAsPNG, schengen.js:1362-1396)
    line_width = max(1, round(cell_px / 50))

    # Collect axis-aligned sub-segments (bend points are in 10-units/cell) so a
    # horizontal wire can "hop" over a *different* net's vertical wire where they
    # cross. Different nets never connect, so an interior H/V crossing is always a
    # crossover, not a tap — the hop makes that unambiguous in the drawing.
    h_subsegs = []  # (net, y, xlo, xhi)
    v_subsegs = []  # (net, x, ylo, yhi)
    for _net, _segs in turning_points.items():
        for _seg in _segs or []:
            for (x0, y0), (x1, y1) in zip(_seg, _seg[1:]):
                if y0 == y1 and x0 != x1:
                    h_subsegs.append((_net, y0, min(x0, x1), max(x0, x1)))
                elif x0 == x1 and y0 != y1:
                    v_subsegs.append((_net, x0, min(y0, y1), max(y0, y1)))

    def _crossings(net, y, xlo, xhi):
        # x's (10-unit) where a different net's vertical wire crosses this
        # horizontal run strictly inside it.
        xs = [x for (vnet, x, ylo, yhi) in v_subsegs
              if vnet != net and xlo < x < xhi and ylo < y < yhi]
        return sorted(set(xs))

    hop_px = max(3, round(cell_px * 0.08))  # bump radius

    def _draw_h_with_hops(net, y, x0, x1, color):
        xs = _crossings(net, y, min(x0, x1), max(x0, x1))
        p0 = to_canvas(x0 * 10, y * 10)
        p1 = to_canvas(x1 * 10, y * 10)
        if not xs:
            draw.line([p0, p1], fill=color, width=line_width, joint="curve")
            return
        py = p0[1]
        cursor = min(p0[0], p1[0])
        end = max(p0[0], p1[0])
        for cx in xs:
            cpx = to_canvas(cx * 10, y * 10)[0]
            if cpx - hop_px > cursor:
                draw.line([(cursor, py), (cpx - hop_px, py)], fill=color, width=line_width)
            # top-half arc (bump up: smaller pixel-y)
            draw.arc([cpx - hop_px, py - hop_px, cpx + hop_px, py + hop_px],
                     180, 360, fill=color, width=line_width)
            cursor = cpx + hop_px
        if end > cursor:
            draw.line([(cursor, py), (end, py)], fill=color, width=line_width)

    for i, net in enumerate(routed_nets.keys()):
        color = _NET_COLORS[i % len(_NET_COLORS)]
        segments = turning_points.get(net)
        if segments:
            # clean polylines through the bend points (10 units/cell -> x10);
            # horizontal runs hop over crossing wires of other nets.
            for seg in segments:
                if len(seg) < 2:
                    continue
                for (x0, y0), (x1, y1) in zip(seg, seg[1:]):
                    if y0 == y1 and x0 != x1:
                        _draw_h_with_hops(net, y0, x0, x1, color)
                    else:
                        draw.line([to_canvas(x0 * 10, y0 * 10), to_canvas(x1 * 10, y1 * 10)],
                                  fill=color, width=line_width, joint="curve")
        else:
            # fallback for result files without turning_points: dots like the web UI
            r = 0.9 * cell_px / 50
            for x, y in routed_nets.get(net, []):
                px, py = to_canvas(x, y)
                draw.ellipse([px - r, py - r, px + r, py + r], fill=color)

        r = 3.0 * cell_px / 50
        for x, y in intersection_points.get(net, []):
            px, py = to_canvas(x, y)
            draw.ellipse([px - r, py - r, px + r, py + r], fill=color)

    # 2) component sprites + name labels
    font = _load_font(max(8, round(12 * cell_px / 50)))
    sprite_cache: dict[str, Image.Image] = {}
    for comp_name, (col, row, orientation, comp_type) in components.items():
        normal, flipped = _SPRITES.get(comp_type, _DEFAULT_SPRITE)
        sprite_name = flipped if orientation == 1 else normal
        sprite = sprite_cache.get(sprite_name)
        if sprite is None:
            sprite = Image.open(_STATIC_DIR / sprite_name).convert("RGBA")
            if sprite.size != (cell_px, cell_px):
                sprite = sprite.resize((cell_px, cell_px), Image.LANCZOS)
            sprite_cache[sprite_name] = sprite

        x = col * cell_px
        y = (num_rows - 1 - row) * cell_px
        image.paste(sprite, (x, y), sprite)

        # Diode-connected MOS reuses the normal sprite, so it carries no diode
        # marking. Draw the gate->drain short (an L hooking round the cell corner)
        # that a drain==gate device has, so it reads as diode-connected.
        if comp_type in ("nmos_diode", "pmos_diode"):
            is_n = comp_type.startswith("nmos")
            gate_x = col * 10 if orientation == 1 else col * 10 + 10  # left/right edge
            gate_y = row * 10 + 5
            drain_x = col * 10 + 5
            drain_y = row * 10 + 10 if is_n else row * 10  # nmos drain top, pmos bottom
            g = to_canvas(gate_x * 10, gate_y * 10)
            corner = to_canvas(gate_x * 10, drain_y * 10)
            d = to_canvas(drain_x * 10, drain_y * 10)
            short_color = net_color.get(diode_net.get(comp_name), (30, 30, 30))
            draw.line([g, corner, d], fill=short_color, width=line_width)

        label = _label_for(comp_name)
        if label:
            # same placement as the web export labels: left + 25px, cell bottom (at 50px cells)
            draw.text(
                (x + cell_px / 2, y + cell_px - 2 * cell_px / 50),
                label,
                fill=_LABEL_COLOR,
                font=font,
                anchor="ls",
            )

    if output_path is None:
        output_path = str(Path(result_path).with_suffix(".png"))
    image.save(output_path)
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Render schengen result JSON file(s) to PNG.")
    parser.add_argument("results", nargs="+", help="path(s) to schengen result JSON files")
    parser.add_argument(
        "-o", "--output", default=None,
        help="output PNG path (single input) or directory (multiple inputs); "
        "default: next to each input with .png suffix",
    )
    parser.add_argument("--cell-px", type=int, default=100, help="pixels per grid cell (default 100)")
    parser.add_argument("--rows", type=int, default=25, help="number of grid rows (default 25)")
    parser.add_argument("--cols", type=int, default=40, help="number of grid columns (default 40)")
    args = parser.parse_args()

    outputs = []
    for result_path in args.results:
        if args.output is None:
            output_path = None
        elif len(args.results) > 1 or Path(args.output).is_dir():
            out_dir = Path(args.output)
            out_dir.mkdir(parents=True, exist_ok=True)
            output_path = str(out_dir / Path(result_path).with_suffix(".png").name)
        else:
            output_path = args.output
        outputs.append(
            render_schematic_result(result_path, output_path, args.cell_px, args.rows, args.cols)
        )

    for out in outputs:
        print(out)


if __name__ == "__main__":
    main()
