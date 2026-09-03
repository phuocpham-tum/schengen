from collections import defaultdict
from typing import Tuple


def trace_vdd_gnd(
    netlist: str,
    targets=["vdd!", "gnd!"],
) -> list[list[Tuple[str, str]]]:
    """
    Trace VDD and GND connections in the netlist

    :param netlist: SPICE netlist, in form of list of strings, for each string represents a component and its connections.
    :return: dict mapping from net to 'vdd' or 'gnd' if connected
    """

    paths = []

    def dfs(
        netlist,
        next_types=["pmos", "nmos", "pnp", "npn"],
        current="vdd!",
        target="gnd!",
        path=[],
    ):
        if current == target:
            paths.append(path.copy())
            return

        for line in netlist:
            component_type = line.strip()[0].lower()[0]

            if component_type in ["m", "q"]:
                parts = line.strip().split(" ")
                name = parts[0]
                d = parts[1]
                g = parts[2]
                s = parts[3]
                transistor_type = parts[-1].lower()
                if transistor_type in next_types:
                    if transistor_type in ["pmos", "pnp"] and s == current:
                        path.append((d, name))
                        dfs(netlist, current=d, path=path)
                        path.pop()
                    elif transistor_type in ["nmos", "npn"] and d == current:
                        path.append((s, name))
                        dfs(netlist, current=s, path=path)
                        path.pop()

    src = targets[0]
    dst = targets[1]
    dfs(
        netlist.strip().splitlines(),
        path=[(src, None)],
        current=src,
        target=dst,
    )
    return paths


# ----------------------------
# Example usage
# ----------------------------
def test_example2():
    netlist = """
    c1 net1 out
    m1 net2 ibias gnd! gnd! nmos
    m2 net3 net3 vdd! vdd! pmos
    m3 net1 net2 net4 net4 pmos
    m4 net4 net3 vdd! vdd! pmos
    m5 net5 ibias gnd! gnd! nmos
    m6 net3 in1 net5 net5 nmos
    m7 net1 in2 net5 net5 nmos
    c2 out gnd!
    m8 out ibias gnd! gnd! nmos
    m9 out net2 net6 net6 pmos
    m10 net6 net1 vdd! vdd! pmos
    m11 ibias ibias gnd! gnd! nmos
    m12 net2 net2 vdd! vdd! pmos
    """

    paths = trace_vdd_gnd(netlist)
    for path in paths:
        devs = [dev for net, dev in path if dev != None]
        print(" -> ".join(devs))


def test_example3():
    netlist = """
m1 net1 net1 vdd! vdd pmos
m2 net2 net1 vdd! vdd pmos
m3 ibias ibias gnd! gnd! nmos
m4 net1 ibias gnd! gnd! nmos
m5 net4 ibias gnd! gnd! nmos
m6 net5 in1 net4 gnd! nmos
m7 net6 in2 net4 gnd! nmos
m8 net5 net5 vdd! vdd! pmos
m9 net6 net6 vdd! vdd! pmos
m10 out1 net5 vdd! vdd! pmos
m11 out2 net6 vdd! vdd! pmos
m12 out1 net2 net7 gnd! nmos
m13 out2 net2 net8 gnd! nmos
m14 net7 net9 gnd! gnd! nmos
m15 net8 net9 gnd! gnd! nmos
m16 net9 net9 gnd! gnd! nmos
m17 net9 net1 vdd! vdd! pmos
m18 net10 net1 vdd! vdd! pmos
m19 net13 net1 vdd! vdd! pmos
m20 net11 out2 net10 vdd! pmos
m21 net9 vcm net10 vdd! pmos
m22 net9 vcm net13 vdd! pmos
m23 net11 out1 net13 vdd! pmos
m24 net9 net11 gnd! gnd! nmos
m25 net11 net11 gnd! gnd! nmos
m26 net2 net2 gnd! gnd! nmos
    """

    paths = trace_vdd_gnd(netlist)
    for path in paths:
        devs = [dev for net, dev in path if dev != None]
        print(" -> ".join(devs))


if __name__ == "__main__":
    print("\nExample #2: ")
    test_example2()
    print("\nExample #3: ")
    test_example3()
