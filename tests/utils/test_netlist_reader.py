from src.utils.netlist_reader import read_netlist


def test_read_netlist():
    content = read_netlist(
        file_path="examples/example_1_opamp_10_7/three_stage_single_output_op_amp_10_7.ckt",
        use_meaninful_token=False,
    )

    expected_result = """
c1 net1 out
c2 net2 out
m1 net3 ibias gnd! gnd! nmos
m2 net4 ibias gnd! gnd! nmos
m3 net5 net5 vdd! vdd! pmos
m4 net1 net3 net6 net6 pmos
m5 net6 net5 vdd! vdd! pmos
m6 net7 ibias gnd! gnd! nmos
m7 net5 in1 net7 net7 nmos
m8 net1 in2 net7 net7 nmos
c3 out gnd!
m9 net8 net8 gnd! gnd! nmos
m10 net8 net1 vdd! vdd! pmos
m11 net2 net8 gnd! gnd! nmos
m12 net2 net4 vdd! vdd! pmos
m13 out ibias gnd! gnd! nmos
m14 out net2 vdd! vdd! pmos
m15 ibias ibias gnd! gnd! nmos
m16 net3 net3 vdd! vdd! pmos
m17 net4 net4 vdd! vdd! pmos
    """.strip()
    print(content)
    assert content == expected_result
