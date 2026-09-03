from flask import Flask, render_template, request, send_file, jsonify
from src.schengen import generate_schematic
from src.translate_ltspice import translate_schengen_result_file
import json
from pathlib import Path
import tempfile

app = Flask(__name__, static_folder="static", template_folder="templates")


@app.route("/")
def index():
    message = "schengen: Netlist to Schematic Conversion Tool"
    return render_template("index.html", message=message)


@app.route("/file_upload", methods=["GET", "POST"])
def file_upload():
    file = request.files["file"]
    if file:
        filename = file.filename
        print(
            file.read().decode("utf-8")
        )  # Print the content of the file to the console
        file.save(f"uploads/{filename}")
        message = f"File {filename} uploaded successfully!"
        return render_template("index.html", message=message)

    return "No file uploaded"


@app.route("/cmd", methods=["GET"])
def console():
    return render_template("console.html")


@app.route("/menu", methods=["GET"])
def menu():
    return render_template("menu.html")


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


def resolve_latest_schengen_result_path() -> Path | None:
    outputs_dir = Path("outputs")
    if not outputs_dir.exists():
        return None
    candidates = sorted(outputs_dir.glob("schematic_data_*.json"))
    return candidates[-1] if candidates else None


@app.route("/schengen", methods=["POST"])
def schengen():
    # Get the data from the request
    data = request.json
    constraints = data.get("constraints", None)
    netlist = data.get("netlist", None)
    if netlist:
        netlist = (
            netlist.strip()
        )  # Remove leading/trailing whitespace from the netlist string

    print(
        "Received constraints:", constraints
    )  # Print the constraints to the console for debugging
    print(
        "Received netlist:\n", netlist
    )  # Print the netlist to the console for debugging

    component_placement_data = constraints.get("component_placement_data", {})
    print("Extracted component_placement_data:", component_placement_data)

    if (not constraints or not netlist) and len(component_placement_data.keys()) == 0:
        return {
            "message": "Input SPICE Netlist & Constraints are required!",
            "status": 400,
        }

    subcircuit_data = read_json_str_data(constraints["subcircuit_info"])
    print("Parsed subcircuit_info:", subcircuit_data)

    partioning_data = read_json_str_data(constraints["partitioning_info"])
    print("Parsed partioning_results:", partioning_data)

    llm_generated_constraints = read_json_str_data(constraints["llm_generated"])
    print("Parsed llm_generated:", llm_generated_constraints)

    user_defined_constraints = read_json_str_data(constraints["user_defined"])
    print("Parsed user_defined_constraints:", user_defined_constraints)

    user_defined_orientations = read_json_str_data(
        constraints["orientation_constraints"]
    )
    print("Parsed user_defined_orientations:", user_defined_orientations)

    terminals = constraints.get("terminals", [])

    print("Extracted path_based_constraints:", constraints["path_based_constraints"])
    print("Extracted terminals:", terminals)

    results = generate_schematic(
        netlist,
        user_defined_constraints,
        llm_generated_constraints,
        subcircuit_data,
        partioning_data,
        user_defined_orientations,  # TODO: change to llm_generated_orientations after LLM orientation generation is ready
        terminals,
        user_defined_orientations,
        pathbased_constraints=constraints["path_based_constraints"],
        enable_routing_local_nets=True,
        component_placement_data=component_placement_data,
    )
    if not results.get("success", False):
        return {
            "message": results.get(
                "message", "An error occurred during schematic generation."
            ),
            "status": 409,
            "data": results,
        }
    else:
        return {
            "message": results.get("message", "Schematic generated successfully!"),
            "status": 200,
            "data": results,
        }


@app.route("/export_ltspice", methods=["POST"])
def export_ltspice():
    payload = request.get_json(silent=True) or {}
    result_path = payload.get("schengen_result_path")

    if result_path:
        candidate_path = Path(result_path)
    else:
        candidate_path = resolve_latest_schengen_result_path()

    if candidate_path is None or not candidate_path.exists():
        return (
            jsonify(
                {
                    "message": "No generated schematic result found to export.",
                    "status": 404,
                }
            ),
            404,
        )

    temp_dir = Path(tempfile.mkdtemp(prefix="schengen_ltspice_"))
    output_path = temp_dir / candidate_path.with_suffix(".asc").name
    translated_path = translate_schengen_result_file(
        str(candidate_path), str(output_path)
    )

    return send_file(
        translated_path,
        as_attachment=True,
        download_name=Path(translated_path).name,
        mimetype="text/plain",
    )


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5555)
