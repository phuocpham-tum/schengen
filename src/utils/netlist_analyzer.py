from dataclasses import dataclass
from collections import defaultdict
from typing import Tuple


class Component:
    def __init__(self, name):
        self.name = name


class Transistor(Component):
    def __init__(self, name, drain, gate, source, mos_type):
        super().__init__(name)

        self.drain = drain
        self.gate = gate
        self.source = source
        self.mos_type = mos_type


class Capacitor(Component):
    def __init__(self, name, pos, neg):
        super().__init__(name)

        self.pos = pos
        self.neg = neg

    def get_all_connected_nets(self):
        return [self.pos, self.neg]


class Resistor(Component):
    def __init__(self, name, pos, neg):
        super().__init__(name)

        self.pos = pos
        self.neg = neg

    def get_all_connected_nets(self):
        return [self.pos, self.neg]


class NetlistAnalyzer:
    def __init__(self, netlist: str):
        self.netlist = netlist

        # initialize other analysis data structures as needed
        self.transistors: list[Transistor] = []
        self.caps: list[Capacitor] = []
        self.resistors: list[Resistor] = []
        self.nets: set[str] = set()
        self.initialize()

    def initialize(self):
        self.transistors = []
        self.caps = []
        self.resistors = []
        self.nets = set()

        for line in self.netlist.strip().split("\n"):
            if line[0].lower().startswith("m") or line[0].lower().startswith("q"):
                data = line.split(" ")
                t = Transistor(
                    name=data[0],
                    drain=data[1],
                    gate=data[2],
                    source=data[3],
                    mos_type=data[-1],
                )
                self.transistors.append(t)
                self.nets.add(data[1])
                self.nets.add(data[2])
                self.nets.add(data[3])
            if line[0].lower().startswith("c"):
                data = line.split(" ")
                cap = Capacitor(name=data[0], pos=data[1], neg=data[2])
                self.caps.append(cap)

                self.nets.add(data[1])
                self.nets.add(data[2])
            if line[0].lower().startswith("r"):
                data = line.split(" ")
                res = Resistor(name=data[0], pos=data[1], neg=data[2])
                self.resistors.append(res)
                self.nets.add(data[1])
                self.nets.add(data[2])

    @property
    def num_transistors(self) -> int:
        return len(self.transistors)

    def get_all_net_connections(self) -> dict[str, list[Tuple[str, str]]]:
        """
        Get all net connections in the netlist, in forms of a dictionary (net: [component_name, port])

        :return: A dictionary mapping net names to lists of (component_name, port) tuples
        """
        shared_connections = defaultdict(list)
        for net in self.nets:
            for t in self.transistors:
                if t.drain == net:
                    shared_connections[net].append((t.name, "drain"))
                if t.gate == net:
                    shared_connections[net].append((t.name, "gate"))
                if t.source == net:
                    shared_connections[net].append((t.name, "source"))

            for c in self.caps:
                if c.pos == net:
                    shared_connections[net].append((c.name, "pos"))
                if c.neg == net:
                    shared_connections[net].append((c.name, "neg"))
            for r in self.resistors:
                if r.pos == net:
                    shared_connections[net].append((r.name, "pos"))
                if r.neg == net:
                    shared_connections[net].append((r.name, "neg"))

        return shared_connections

    def get_single_net_connections(self, net: str) -> list[Tuple[str, str]]:
        """
        Get connections for a single net in the netlist, in forms of a list of (component_name, port) tuples

        :param net: the net name to query
        :return: A list of (component_name, port) tuples connected to the specified net
        """

        all_connections = self.get_all_net_connections()
        if net not in all_connections:
            raise ValueError(f"Net: {net} could not find.")
        return all_connections[net]

    def get_drain_source_connection(self) -> dict[str, list]:
        """
        Get drain-source connections in the netlist, in forms of a dictionary (component_name: [connected_component_names])
        with the key being the name of the transistor that has the drain terminal connected to the source  of the transistors in the value list.

        :return: A dictionary mapping transistor names to lists of connected transistor names
        """
        shared_connections = defaultdict(list)
        for t1 in self.transistors:
            for t2 in self.transistors:
                if t1.drain == t2.source:
                    if (t1.mos_type == "pmos" and t2.mos_type == "pmos") or (
                        t1.mos_type == "pnp" and t2.mos_type == "pnp"
                    ):
                        shared_connections[t1.name].append(t2.name)
                    elif (t1.mos_type == "nmos" and t2.mos_type == "nmos") or (
                        t1.mos_type == "npn" and t2.mos_type == "npn"
                    ):
                        shared_connections[t2.name].append(t1.name)

        return shared_connections

    def get_drain_drain_connection(self) -> dict[str, list]:
        """
        Get drain-drain connections in the netlist, in forms of a dictionary (component_name: [connected_component_names])
        with the key being the name of the transistor that has the drain terminal connected to the drain of the transistors in the value list.

        :return: A dictionary mapping transistor names to lists of connected transistor names
        """
        shared_connections = defaultdict(list)
        for t1 in self.transistors:
            for t2 in self.transistors:
                if (
                    (t1.mos_type == "pmos" or t1.mos_type == "pnp")
                    and t1.drain == t2.drain
                    and (t2.mos_type == "nmos" or t2.mos_type == "npn")
                ):
                    shared_connections[t1.name].append(t2.name)
        return shared_connections

    def get_shared_gate_connections(self):
        shared_connections = defaultdict(list)
        for t in self.transistors:
            shared_connections[t.gate].append(t.name)

        shared_connections = {k: v for k, v in shared_connections.items() if len(v) > 1}
        return shared_connections

    def get_shared_source_connections(self):
        shared_connections = defaultdict(list)
        for t in self.transistors:
            if t.source not in ["gnd!", "vdd!"]:
                shared_connections[t.source].append(t.name)

        shared_connections = {k: v for k, v in shared_connections.items() if len(v) > 1}
        return shared_connections

    def get_shared_source_connections_same_types(self):
        c = {
            "pmos": defaultdict(list),
            "nmos": defaultdict(list),
            "pmos_diode": defaultdict(list),
            "nmos_diode": defaultdict(list),
            # BJI
            "pnp": defaultdict(list),
            "npn": defaultdict(list),
            "pnp_diode": defaultdict(list),
            "npn_diode": defaultdict(list),
        }
        for t in self.transistors:
            if t.source not in ["gnd!", "vdd!"]:
                c[t.mos_type][t.source].append(t.name)

        for k, v in c.items():
            c[k] = {net: comps for net, comps in v.items() if len(comps) > 1}
        return c
