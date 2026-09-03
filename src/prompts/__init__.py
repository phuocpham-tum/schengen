from pathlib import Path

import src.constraints.placement as pc

_PROMPT_DIR = Path(__file__).parent


def render_constraint_prompt(version: str = "v0.0.2") -> str:
    """Load the constraint-generation prompt template and fill the
    {{CONSTRAINT_PRIMITIVES}} block from the primitive registry (the single
    source of truth), so the vocabulary shown to the LLM can never drift from
    what the solver actually accepts.

    Other placeholders ({{NETLIST}}, {{STRUCTURE_RESULT}}, {{PARTITIONING_RESULT}})
    are left intact, to be filled at generation time.
    """
    template = (_PROMPT_DIR / "constraint-generation" / f"{version}.md").read_text()
    return template.replace("{{CONSTRAINT_PRIMITIVES}}", pc.render_primitives_doc())
