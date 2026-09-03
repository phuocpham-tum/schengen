from src.utils.structure_reader import (
    simplify_circuit_structure,
    simplify_circuit_partitioning,
)


def test_read_circuit_structure():
    tree = simplify_circuit_structure(
        xml_file="examples/example_1_opamp_10_7/str_three_stage_single_output_op_amp_10_7.xml"
    )
    tree.write("output.xml")


def test_simplify_circuit_partitioning():
    tree = simplify_circuit_partitioning(
        xml_file="examples/example_1_opamp_10_7/p_three_stage_single_output_op_amp_10_7.xml"
    )
    tree.write("p_output.xml")
