import json
import pprint


def print_json(data: dict) -> None:
    print(json.dumps(data, indent=4))


def print_json_compact(data: dict) -> None:
    pprint.pprint(data)
