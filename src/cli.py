import argparse
import time
from pathlib import Path
import json

from src.schengen import generate_schematic

parser = argparse.ArgumentParser(description="Run schengen from the command line.")

parser.add_argument(
    "--num",
    type=int,
    default=1,
    help="number of schematics to generate.",
    required=False,
)
parser.add_argument(
    "--log_level",
    default="debug",
    help="logging level (debug, info, warning, error, critical)",
    required=False,
)
parser.add_argument(
    "--ckt",
    default="debug",
    help="path to the .ckt file to generate schematic for",
    required=False,
)
parser.add_argument(
    "--constraint-file",
    default="debug",
    help="path to the constraint file (json) for schematic generation",
    required=False,
)

parser.add_argument(
    "--output_dir",
    default="output",
    help="path to the output directory for generated schematics",
    required=False,
)

parser.add_argument(
    "--render",
    action="store_true",
    help="also render each generated schematic to a PNG next to its result JSON",
)

parser.add_argument(
    "--render-prompt",
    action="store_true",
    help="print the constraint-generation prompt with the primitive vocabulary filled from the registry, then exit",
)

args = parser.parse_args()


time.sleep(2)


def read_json_str_data(json_string):
    """Utility function to read JSON string data, handling single quotes, comments, and trailing commas."""
    try:
        data = json.loads(
            json_string.replace("'", '"').split("#")[0].strip().rstrip(",")
        )
        return data
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON: {e}")
        return None


if __name__ == "__main__":

    if args.render_prompt:
        from src.prompts import render_constraint_prompt

        print(render_constraint_prompt())
        raise SystemExit(0)

    simplified_netlist_path = Path(args.ckt)
    netlist = open(simplified_netlist_path).read()

    example_dir = Path(args.ckt).parent
    with open(f"{args.constraint_file}", "r") as f:
        data = json.load(f)

    subcircuit_data = read_json_str_data(data["subcircuit_info"])
    print("Parsed subcircuit_info:", subcircuit_data)

    partioning_data = read_json_str_data(data["partitioning_info"])
    print("Parsed partioning_results:", partioning_data)

    llm_generated_constraints = read_json_str_data(data["llm_generated"])
    print("Parsed llm_generated:", llm_generated_constraints)

    user_defined_constraints = read_json_str_data(data["user_defined"])
    print("Parsed user_defined_constraints:", user_defined_constraints)

    user_defined_orientations = read_json_str_data(data["orientation_constraints"])
    print("Parsed user_defined_orientations:", user_defined_orientations)

    terminals = data.get("terminals", [])

    print("Extracted path_based_constraints:", data["path_based_constraints"])
    print("Extracted terminals:", terminals)

    for runid in range(args.num):
        results = generate_schematic(
            netlist,
            user_defined_constraints,
            llm_generated_constraints,
            subcircuit_data,
            partioning_data,
            user_defined_orientations,  # TODO: change to llm_generated_orientations after LLM orientation generation is ready
            terminals,
            user_defined_orientations,
            pathbased_constraints=data["path_based_constraints"],
            enable_routing_local_nets=True,
            component_placement_data={},
        )

        output_dir = example_dir / args.output_dir
        output_dir.mkdir(exist_ok=True)

        if len(results) == 0:
            print("No results generated for this run.")
            break

        routing_cost = results["routing_cost"]
        num_bends = results["num_bends"]
        num_crossings = results["num_crossings"]
        hpwl_cost = results["hpwl_cost"]
        result_path = (
            output_dir
            / f"schematic_result_{runid}_{routing_cost}_{num_bends}_{num_crossings}_{hpwl_cost}.json"
        )
        with open(result_path, "w") as f:
            json.dump(results, f, indent=4)

        if args.render:
            from src.render_schematic import render_schematic_result

            png_path = render_schematic_result(str(result_path))
            print(f"Rendered schematic to {png_path}")
