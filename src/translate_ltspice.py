import argparse
import time
from pathlib import Path
import json


def _placement_to_symbol(placement):
    if placement[-1].startswith("npn"):
        return "npn"
    if placement[-1].startswith("pnp"):
        return "pnp"
    if placement[-1].startswith("nmos"):
        return "nmos"
    if placement[-1].startswith("pmos"):
        return "pmos"
    if placement[-1].startswith("res"):
        return "res"
    if placement[-1].startswith("cap"):
        return "cap"
    return None


def translate_to_ltspice_format(schengen_result_path: str):
    """Translate the schengen result to LTspice format.
    Args:
        schengen_result_path (str): The path to the schengen result file.
    """
    netlist = Path(schengen_result_path).read_text()

    data = json.loads(netlist)
    placement_data = data.get("component_placement_data", {})

    content = "Version 4\n"
    content += f"SHEET 1 {20*100} {40*100}\n"
    max_rows = 20
    for name, placement in placement_data.items():
        symbol = _placement_to_symbol(placement)
        if symbol is None:
            continue

        if "terminal" in name:
            x = placement[0] * 100 + 50
            y = (max_rows - placement[1]) * 100
            y = int(y) + 50
            name_attr = name.replace("terminal_", "")
            content += f"SYMATTR InstName {name_attr}\n"

            content += f"FLAG {x} {y} {name_attr}\n"
            if "out" not in name:
                content += f"IOPIN {x} {y} In\n"
            else:
                content += f"IOPIN {x} {y} Out\n"
        else:
            x = placement[0] * 100
            y = (max_rows - placement[1]) * 100
            y = int(y)

            if symbol in ["res", "cap"]:
                x += 66
                y += 4
                orientation = "M0"
            else:
                if placement[2] == 1:
                    # gate on the left
                    orientation = "R0"
                    if symbol in ["pnp", "npn"]:
                        x -= 15
                        y += 2
                    if symbol in ["pmos", "nmos"]:
                        x -= 15
                        y += 2

                elif placement[2] == 0:
                    # gate on the right
                    orientation = "M0"
                    if symbol in ["pnp", "npn"]:
                        x += 100 + 15
                        y += 2
                    if symbol in ["pmos", "nmos"]:
                        x += 100 + 15
                        y += 2

            content += f"SYMBOL {symbol} {x} {y} {orientation}\n"

            name_attr = name.replace("terminal_", "")
            content += f"SYMATTR InstName {name_attr}\n"

            if symbol in ["res", "cap"]:
                content += f"WIRE {x-16} {y + 16} {x-16} {y-5}\n"
                content += f"WIRE {x-16} {y + 100+10} {x-16} {y+95}\n"

    canvas_max_row = 20 * 100 + 100
    for net, routed_points_all in data.get("turning_points", {}).items():
        for seg in routed_points_all:

            for i in range(len(seg) - 1):
                src_point = seg[i]
                dst_point = seg[i + 1]
                x1, y1 = src_point
                x2, y2 = dst_point

                y1 = int(canvas_max_row - y1 * 10)
                y2 = int(canvas_max_row - y2 * 10)
                content += f"WIRE {x1*10} {y1} {x2*10} {y2}\n"

    return content


def translate_schengen_result_file(
    schengen_result_path: str, output_path: str | None = None
) -> str:
    """Translate a schengen result JSON file to an LTspice .asc file.

    Returns the output path.
    """
    ltspice_content = translate_to_ltspice_format(schengen_result_path)
    if output_path is None:
        output_path = str(Path(schengen_result_path).with_suffix(".asc"))

    Path(output_path).write_text(ltspice_content)
    return output_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run schengen from the command line.")
    parser.add_argument(
        "--schengen_result",
        default="/tmp/schengen_result.json",
        help="path to the schengen result file",
        required=False,
    )
    args = parser.parse_args()

    start_time = time.time()
    output_path = translate_schengen_result_file(args.schengen_result)
    print(f"LTspice schematic saved to {output_path}")
    print(f"Total time taken: {time.time() - start_time:.2f} seconds")
