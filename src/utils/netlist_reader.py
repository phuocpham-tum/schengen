from typing import Optional, Union
from pathlib import Path


def read_netlist(file_path: Union[str, Path], use_meaninful_token: bool = False) -> str:
    """
    Read SPICE netlist and convert all meaningful net names into non-meaningful net names.
    This mainly to prevent leaking meaningful information to LLMs during inference/evaluation.

    :param file_path: path to SPICE netlist file
    :param use_meaninful_token: whether we use "net**" (could be inpretered as multile token in LLMs) or a,b,c, etc... (single token in LLMs) as new net names
    :return: the content of new SPICE netlist with new net names
    """

    netid = 97 if use_meaninful_token else 1
    mapping = {}
    spice_content = ""
    with open(file_path, "r") as f:
        for line in f:
            line = line.strip()
            if (
                line.startswith(".suckt")
                or line.startswith(".SUBCKT")
                or line.startswith(".end ")
            ):
                continue

            connection_info = line.split()
            if len(connection_info) > 3:
                new_line = connection_info[0] + " "
                for i in range(1, len(connection_info)):
                    if connection_info[i] == "sourceNmos":
                        if use_meaninful_token:
                            new_line += "ground" + " "
                        else:
                            new_line += "gnd!" + " "

                    elif connection_info[i] == "sourcePmos":
                        if use_meaninful_token:
                            new_line += "supply" + " "
                        else:
                            new_line += "vdd!" + " "
                    elif connection_info[i] in [
                        "nmos",
                        "pmos",
                        "ibias",
                        "vref",
                        "in1",
                        "in2",
                        "out",
                        "out1",
                        "out2",
                    ]:
                        new_line += connection_info[i] + " "
                    elif connection_info[i] not in mapping:

                        mapping[connection_info[i]] = (
                            f"net{netid}" if not use_meaninful_token else chr(netid)
                        )  #
                        netid += 1
                        new_line += mapping[connection_info[i]] + " "
                    else:
                        new_line += mapping[connection_info[i]] + " "

            elif len(connection_info) == 3:
                new_line = connection_info[0] + " "
                for i in range(1, len(connection_info)):
                    if connection_info[i] in [
                        "nmos",
                        "pmos",
                        "ibias",
                        "vref",
                        "in1",
                        "in2",
                        "out",
                        "out1",
                        "out2",
                    ]:
                        new_line += connection_info[i] + " "

                    elif connection_info[i] == "sourceNmos":
                        if use_meaninful_token:
                            new_line += "ground" + " "
                        else:
                            new_line += "gnd!" + " "

                    elif connection_info[i] == "sourcePmos":
                        if use_meaninful_token:
                            new_line += "supply" + " "
                        else:
                            new_line += "vdd!" + " "

                    elif connection_info[i] not in mapping:
                        mapping[connection_info[i]] = (
                            f"net{netid}" if not use_meaninful_token else chr(netid)
                        )  #
                        netid += 1
                        new_line += mapping[connection_info[i]] + " "
                    else:
                        new_line += mapping[connection_info[i]] + " "
            else:
                new_line = line

            new_line = new_line.strip()
            spice_content += new_line + "\n"

    return spice_content.strip()
