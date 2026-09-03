"""Generate LLM placement constraints for a netlist using the constraint-generation
prompt (src/prompts/constraint-generation/<version>.md).

The prompt's {{CONSTRAINT_PRIMITIVES}} block is filled from the primitive registry
(via src.prompts.render_constraint_prompt); this script fills the remaining
placeholders — {{NETLIST}}, {{STRUCTURE_RESULT}}, {{PARTITIONING_RESULT}} — from a
netlist and a *base* constraint file, calls an LLM, and writes a new
constraint JSON with the generated `llm_generated` list (all other fields carried
over from the base file, so the output is directly runnable via `python -m src.cli`).

Two providers are supported via --provider:
  - openai    (default): any OpenAI chat model; reads OPENAI_API_KEY.
  - anthropic          : any Claude model (default claude-opus-4-8); reads
                         ANTHROPIC_API_KEY, or an `ant auth login` profile.

Existing constraint files are never modified. For each run three artifacts are
written to --out-dir: `<name>.json` (the constraint file), `<name>.prompt.txt`
(the exact prompt sent), and `<name>.response.txt` (the raw model reply).

Reproducibility: OpenAI uses temperature 0. Claude (Opus 4.8 tier) does not accept
a temperature and runs with adaptive thinking, so its output is best-effort
reproducible rather than deterministic.

Example:
    # OpenAI
    uv run python scripts/generate_llm_constraints.py \
        --ckt examples/example-7/netlist.ckt \
        --base-constraint examples/example-7/constraint.json --model gpt-4o

    # Claude (Opus 4.8)
    uv run python scripts/generate_llm_constraints.py \
        --ckt examples/example-7/netlist.ckt \
        --base-constraint examples/example-7/constraint.json --provider anthropic
"""

import argparse
import ast
import json
import os
import re
import sys
from pathlib import Path

# Make the repo root importable when run as a plain script.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.prompts import render_constraint_prompt  # noqa: E402
from src.constraints.placement import PRIMITIVE_REGISTRY  # noqa: E402


def read_json_str_data(json_string):
    """Decode a constraint file's escaped-JSON string field (single quotes,
    trailing commas, `#` comments) — mirrors src/cli.py so behaviour matches."""
    if json_string is None:
        return None
    try:
        return json.loads(json_string.replace("'", '"').split("#")[0].strip().rstrip(","))
    except json.JSONDecodeError:
        return None


def pretty(obj) -> str:
    """Render a decoded structure/partitioning object for the prompt, or a
    placeholder when it is empty/missing so the LLM knows it was omitted."""
    if not obj:
        return "(none provided)"
    return json.dumps(obj, indent=2)


def build_prompt(version, netlist, structure_obj, partitioning_obj):
    prompt = render_constraint_prompt(version)  # fills {{CONSTRAINT_PRIMITIVES}}
    prompt = prompt.replace("{{NETLIST}}", netlist.strip())
    prompt = prompt.replace("{{STRUCTURE_RESULT}}", pretty(structure_obj))
    prompt = prompt.replace("{{PARTITIONING_RESULT}}", pretty(partitioning_obj))
    return prompt


def parse_constraints(text):
    """Extract the `constraints = [ ... ]` Python list from the model reply."""
    # Prefer the explicit assignment; fall back to the first top-level list.
    m = re.search(r"constraints\s*=\s*(\[.*\])", text, re.DOTALL)
    if not m:
        m = re.search(r"(\[.*\])", text.strip(), re.DOTALL)
    if not m:
        raise ValueError("no constraint list found in model response")
    return ast.literal_eval(m.group(1))


def netlist_component_names(netlist, terminals):
    """Allowed identifiers a constraint may reference: element names (first token
    of each netlist line) plus terminals in both bare and `terminal_<name>` form."""
    names = set()
    for line in netlist.splitlines():
        line = line.strip()
        if line:
            names.add(line.split()[0])
    for t in terminals or []:
        names.add(t)
        names.add(f"terminal_{t}")
    return names


def validate(constraints, allowed_components):
    """Return a list of human-readable warnings (unknown primitives / components).
    Non-fatal: the solver de-conflicts, and we prefer to surface issues, not drop
    output."""
    warnings = []
    for i, c in enumerate(constraints):
        if not isinstance(c, list) or not c:
            warnings.append(f"[{i}] not a non-empty list: {c!r}")
            continue
        name = c[0]
        if name not in PRIMITIVE_REGISTRY:
            warnings.append(f"[{i}] unknown primitive '{name}'")
        # Referenced components are the string entries after the primitive name
        # (a leading numeric value, if any, is skipped automatically since it is
        # not a str).
        refs = [x for x in c[1:] if isinstance(x, str)]
        unknown = [r for r in refs if r not in allowed_components]
        if unknown:
            warnings.append(f"[{i}] {name}: unknown components {unknown}")
    return warnings


DEFAULT_MODEL = {"openai": "gpt-4o", "anthropic": "claude-opus-4-8"}


def call_openai(prompt, model, temperature, max_tokens):
    from openai import OpenAI

    client = OpenAI()  # reads OPENAI_API_KEY
    # GPT-5 tier models require `max_completion_tokens` (not `max_tokens`) and only
    # support the default temperature; older chat models (e.g. gpt-4o) accept both an
    # explicit temperature and the newer token param.
    kwargs = dict(
        model=model,
        max_completion_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    if not model.startswith("gpt-5"):
        kwargs["temperature"] = temperature
    resp = client.chat.completions.create(**kwargs)
    return resp.choices[0].message.content


def call_anthropic(prompt, model, max_tokens):
    import anthropic

    # Zero-arg client resolves ANTHROPIC_API_KEY or an `ant auth login` profile.
    client = anthropic.Anthropic()
    # Opus 4.8 tier: no temperature (removed — 400s); adaptive thinking on for the
    # strictness reasoning the prompt asks for. Thinking blocks are separate from
    # the text block, so the returned constraint list stays clean.
    resp = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        thinking={"type": "adaptive"},
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(b.text for b in resp.content if b.type == "text")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ckt", required=True, help="path to the .ckt netlist")
    ap.add_argument("--base-constraint", required=True,
                    help="base constraint JSON: supplies structure/partitioning inputs "
                         "for the prompt and all carried-over fields for the output")
    ap.add_argument("--out-dir", default=None,
                    help="output directory (default: alongside the base constraint file)")
    ap.add_argument("--name", default="constraint-llm-gen",
                    help="basename for the output artifacts (default: constraint-llm-gen)")
    ap.add_argument("--provider", choices=["openai", "anthropic"], default="openai",
                    help="LLM provider (default: openai)")
    ap.add_argument("--model", default=None,
                    help="model id (default: gpt-4o for openai, claude-opus-4-8 for anthropic)")
    ap.add_argument("--version", default="v0.0.2", help="prompt version (default: v0.0.2)")
    ap.add_argument("--temperature", type=float, default=0.0,
                    help="OpenAI sampling temperature (default: 0; ignored for anthropic)")
    ap.add_argument("--max-tokens", type=int, default=16000,
                    help="max output tokens (default: 16000; leaves headroom for Claude thinking)")
    ap.add_argument("--dry-run", action="store_true",
                    help="assemble and save the prompt only; do not call the API")
    args = ap.parse_args()
    model = args.model or DEFAULT_MODEL[args.provider]

    ckt_path = Path(args.ckt)
    base_path = Path(args.base_constraint)
    netlist = ckt_path.read_text()
    base = json.loads(base_path.read_text())

    structure_obj = read_json_str_data(base.get("subcircuit_info"))
    partitioning_obj = read_json_str_data(base.get("partitioning_info"))
    terminals = base.get("terminals", [])

    prompt = build_prompt(args.version, netlist, structure_obj, partitioning_obj)

    out_dir = Path(args.out_dir) if args.out_dir else base_path.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"{args.name}.prompt.txt").write_text(prompt)

    if args.dry_run:
        print(f"[dry-run] prompt written to {out_dir / f'{args.name}.prompt.txt'} "
              f"({len(prompt)} chars). No API call made.")
        return

    if args.provider == "openai":
        if not os.environ.get("OPENAI_API_KEY"):
            sys.exit("OPENAI_API_KEY is not set — export it or use --dry-run.")
        print(f"Calling {model} (openai, temperature={args.temperature}) ...")
        response = call_openai(prompt, model, args.temperature, args.max_tokens)
    else:
        # anthropic: the SDK also resolves an `ant auth login` profile, so a missing
        # env var is not necessarily fatal — let the SDK surface an auth error.
        print(f"Calling {model} (anthropic, adaptive thinking) ...")
        response = call_anthropic(prompt, model, args.max_tokens)
    (out_dir / f"{args.name}.response.txt").write_text(response)

    constraints = parse_constraints(response)
    warnings = validate(constraints, netlist_component_names(netlist, terminals))

    # Carry over every base field, replacing only llm_generated. Stored as a JSON
    # string to match the existing constraint-file format (src/cli.py decodes it).
    out = dict(base)
    out["llm_generated"] = json.dumps(constraints)
    out_json = out_dir / f"{args.name}.json"
    out_json.write_text(json.dumps(out, indent=4))

    print(f"Generated {len(constraints)} constraints -> {out_json}")
    if warnings:
        print(f"{len(warnings)} validation warning(s):")
        for w in warnings:
            print("  -", w)


if __name__ == "__main__":
    main()
