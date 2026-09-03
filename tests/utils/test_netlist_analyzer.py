from src.utils.netlist_analyzer import get_drain_source_connection


def test_get_drain_source_connection():
    shared_connections = get_drain_source_connection(
        open(
            "./examples/example_2_two_stage_single_output_op_amp_10_10/simplified_netlist.ckt"
        ).read()
    )
    expected_results = {'m4': ['m3'], 'm5': ['m6', 'm7'], 'm10': ['m9']}
    assert shared_connections == expected_results
    print(shared_connections)
