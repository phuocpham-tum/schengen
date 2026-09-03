import xml.etree.ElementTree as ET
import glob
import os
from collections import defaultdict


def rename(subblock_name: str) -> str:
    mapping: dict[str, str] = {}
    for inv in [
        "MosfetCascodedPMOSAnalogInverter",
        "MosfetAnalogInverter",
        "MosfetCascodedAnalogInverter",
        "MosfetCascodeAnalogInverterNmosDiodeTransistor",
        "MosfetCascodeNMOSAnalogInverterOneDiodeTransistor",
        "MosfetCascodedNMOSAnalogInverter",
        "MosfetCascodePMOSAnalogInverterOneDiodeTransistor",
        "MosfetCascodeAnalogInverterPmosDiodeTransistor",
        "MosfetCascodeAnalogInverterNmosCurrentMirrorLoad",
    ]:
        mapping[inv] = "Inverter"

    for dp in [
        "MosfetDifferentialPair",
        "MosfetCascodedDifferentialPair",
        "MosfetFoldedCascodeDifferentialPair",
    ]:
        mapping[dp] = "Differential Pair"
    for cm in [
        "MosfetFourTransistorCurrentMirror",
        "MosfetWideSwingCascodeCurrentMirror",
        "MosfetSimpleCurrentMirror",
        "MosfetImprovedWilsonCurrentMirror",
        "MosfetWilsonCurrentMirror",
        "MosfetCascodeCurrentMirror",
    ]:
        mapping[cm] = "Current Mirror"

    return mapping[subblock_name]


def rename_simple(name: str) -> str:
    # remove indices (e.g. CapacitorArray[1] -> CapacitorArray)
    name = name[: name.find("[")]

    # remove keywords (Mosfet, Array)
    name = name.replace("Mosfet", "").replace("Array", "")

    if name == "Normal":
        name = "Normal Transistor"
    return name


def remove_pin_tag(subcircuit: ET.Element) -> None:
    for pins in subcircuit.findall("pins"):
        subcircuit.remove(pins)

    for structure in subcircuit.findall("structure"):
        structure.set("name", rename_simple(structure.attrib["name"]))
        structure.attrib.pop("techType")
        structure.attrib.pop("instance")
        remove_pin_tag(structure)
        for device in structure.iter("device"):
            device.set("name", device.attrib["name"].replace("/", ""))
            if "instance" in device.attrib:
                device.attrib.pop("instance")


def simplify_circuit_structure(xml_file: str) -> ET.ElementTree:
    """
    Create a ElementTree (XML structure) with simplified structures (remove pins/ connections/ redundant attributes)

    :param xml_file: pathh to the structure XML file.
    :return: a modified ElementTree
    """

    tree = ET.parse(xml_file)
    root = tree.getroot()
    subcircuits = root[1]
    structures: list[str] = []
    for sc in subcircuits:

        name = sc.attrib["name"]

        name = rename_simple(name)
        # print(name)

        sc.set("name", name)
        sc.attrib.pop("techType")
        sc.attrib.pop("instance")

        remove_pin_tag(sc)
        for device in sc.iter("device"):
            device.set("name", device.attrib["name"].replace("/", ""))
            if "instance" in device.attrib:
                device.attrib.pop("instance")

    # tree.write("out.xml")
    out_tree = ET.ElementTree(subcircuits)
    return out_tree


def simplify_circuit_partitioning(xml_file: str) -> ET.ElementTree:
    """
    Create a ElementTree (XML structure) with simplified partitioning results

    :param xml_file: pathh to the structure XML file.
    :return: a modified ElementTree
    """

    tree = ET.parse(xml_file)
    root = tree.getroot()[1]
    for gmPart in root.findall("./gmParts/gmPart"):
        for structure in gmPart.findall("structure"):

            name = structure.attrib["name"]
            name = rename_simple(name)
            structure.set("name", name)
            structure.attrib.pop("techType")
            structure.attrib.pop("instance")

            remove_pin_tag(structure)
            for device in structure.iter("device"):
                device.set("name", device.attrib["name"].replace("/", ""))
                if "instance" in device.attrib:
                    device.attrib.pop("instance")

    for loadPart in root.findall("./loadParts/loadPart"):
        for structure in loadPart.findall("structure"):

            name = structure.attrib["name"]
            name = rename_simple(name)
            structure.set("name", name)
            structure.attrib.pop("techType")
            structure.attrib.pop("instance")

            remove_pin_tag(structure)
            for device in structure.iter("device"):
                device.set("name", device.attrib["name"].replace("/", ""))
                if "instance" in device.attrib:
                    device.attrib.pop("instance")

    for biasPart in root.findall("./biasParts/biasPart"):
        for structure in biasPart.findall("structure"):

            name = structure.attrib["name"]
            name = rename_simple(name)
            structure.set("name", name)
            structure.attrib.pop("techType")
            structure.attrib.pop("instance")

            remove_pin_tag(structure)
            for device in structure.iter("device"):
                device.set("name", device.attrib["name"].replace("/", ""))
                if "instance" in device.attrib:
                    device.attrib.pop("instance")

    for capacitance in root.findall("./capacitances/capacitance"):
        for structure in capacitance.findall("structure"):

            name = structure.attrib["name"]
            name = rename_simple(name)
            structure.set("name", name)
            structure.attrib.pop("techType")
            structure.attrib.pop("instance")

            remove_pin_tag(structure)
            for device in structure.iter("device"):
                device.set("name", device.attrib["name"].replace("/", ""))
                if "instance" in device.attrib:
                    device.attrib.pop("instance")

        # name = rename_simple(name)
        # # print(name)

        # sc.set("name", name)
        # sc.attrib.pop("techType")
        # sc.attrib.pop("instance")

        # remove_pin_tag(sc)
        # for device in sc.iter("device"):
        #     device.set("name", device.attrib["name"].replace("/", ""))
        #     if "instance" in device.attrib:
        #         device.attrib.pop("instance")

    # tree.write("out.xml")
    out_tree = ET.ElementTree(root)
    return out_tree


if __name__ == "__main__":
    import sys

    print(sys.argv)
    tree = simplify_circuit_structure(sys.argv[1])
    tree.write("structure_output.xml")

    tree = simplify_circuit_partitioning(sys.argv[2])
    tree.write("partitioning_output.xml")
