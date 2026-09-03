import src.constraints.placement as pc


def MosfetCascodeAnalogInverterNmosDiodeTransistor(schematic, transistors: list):
    """Create placement constraints for a cascode analog inverter with NMOS diode transistor."""

    # Ensure that the transistors are in the correct order
    assert (
        len(transistors) == 4
    ), "Expected 4 transistors for the cascode analog inverter."
    M2, M1, M3, M4 = transistors

    # Define the placement constraints for the cascode analog inverter
    pc.above(schematic, M1, M2)  # M1 is above M2
    pc.above(schematic, M2, M3)  # M2 is above M3
    pc.above(schematic, M3, M4)  # M3 is above M4

    pc.same_column(schematic, M1, M2)  # M1 and M2 are in the same column
    pc.same_column(schematic, M2, M3)  # M2 and M3 are in the same column
    pc.same_column(schematic, M3, M4)  # M3 and M4 are in the same column


def MosfetCascodedAnalogInverter(schematic, transistors: list):
    """Create placement constraints for a cascoded analog inverter."""

    # Ensure that the transistors are in the correct order
    assert (
        len(transistors) == 4
    ), "Expected 4 transistors for the cascoded analog inverter."

    M2, M1, M3, M4 = transistors

    # Define the placement constraints for the cascode analog inverter
    pc.above(schematic, M1, M2)  # M1 is above M2
    pc.above(schematic, M2, M3)  # M2 is above M3
    pc.above(schematic, M3, M4)  # M3 is above M4

    pc.same_column(schematic, M1, M2)  # M1 and M2 are in the same column
    pc.same_column(schematic, M2, M3)  # M2 and M3 are in the same column
    pc.same_column(schematic, M3, M4)  # M3 and M4 are in the same column


def MosfetFourTransistorCurrentMirror(schematic, transistors: list):
    """Create placement constraints for a four-transistor current mirror."""

    # Ensure that the transistors are in the correct order
    assert (
        len(transistors) == 4
    ), "Expected 4 transistors for the four-transistor current mirror."

    M2, M1, M4, M3 = transistors

    # Define the placement constraints for the four-transistor current mirror
    pc.above(schematic, M1, M2)  # M1 is above
    pc.above(schematic, M3, M4)  # M3 is above M4

    pc.same_row(schematic, M1, M3)  # M1 and M3 are in the same row
    pc.same_row(schematic, M2, M4)  # M2 and M4 are in the same row

    pc.same_column(schematic, M1, M2)  # M1 and M2 are in the same column
    pc.same_column(schematic, M3, M4)  # M3 and M4 are in the same column

    pc.left_of(schematic, M1, M3)  # M1 is to the left of M3
    pc.left_of(schematic, M2, M4)  # M2 is to the left of M4

    # pc.clear_column_between(schematic, M1, M3)  # Clear column between M1 and M3
    # pc.clear_column_between(schematic, M2, M4)  # Clear column between M2 and M4


def MosfetDifferentialPair(schematic, transistors: list):
    """Create placement constraints for a differential pair."""

    # Ensure that the transistors are in the correct order
    assert len(transistors) == 2, "Expected 2 transistors for the differential pair."

    M1, M2 = transistors

    # Define the placement constraints for the differential pair
    pc.same_row(schematic, M1, M2)  # M1 and M2 are in the same row
    pc.clear_column_between(schematic, M1, M2)  # Clear column between M1 and M2

    pc.left_of(schematic, M1, M2)  # M1 is to the left of M2
    schematic.find_component(M2).orientation = 0
    schematic.find_component(M1).orientation = 1


def MosfetSimpleCurrentMirror(schematic, transistors: list):
    """Create placement constraints for a simple current mirror."""

    # Ensure that the transistors are in the correct order
    assert (
        len(transistors) <= 5
    ), "Expected 2, 3, 4, or 5 transistors for the simple current mirror."

    if len(transistors) == 2:
        M1, M2 = transistors
        # Define the placement constraints for the simple current mirror
        pc.same_row(schematic, M1, M2)  # M1 and M2 are in the same row
        pc.left_of(schematic, M1, M2)  # M1 is to the left of M2
        pc.clear_column_between(schematic, M1, M2)  # Clear column between M1 and M2
    elif len(transistors) == 3:
        M1, M2, M3 = transistors
        # Define the placement constraints for the simple current mirror with an additional transistor
        pc.same_row(schematic, M1, M2)  # M1 and M2 are in the same row
        pc.same_row(schematic, M1, M3)  # M1 and M3 are in the same row
        pc.left_of(schematic, M1, M2)  # M1 is to the left of M2
        pc.left_of(schematic, M1, M3)  # M1 is to the left of M3
        pc.left_of(schematic, M2, M3)  # M2 is to the left of M3

        pc.clear_column_between(schematic, M1, M2)  # Clear column between M1 and M2
        pc.clear_column_between(schematic, M2, M3)  # Clear column between M2 and M3
    elif len(transistors) == 4:
        M1, M2, M3, M4 = transistors
        # Define the placement constraints for the simple current mirror with four transistors
        pc.same_row(schematic, M1, M2)  # M1 and M2 are in the same row
        pc.same_row(schematic, M3, M4)  # M3 and M4 are in the same row
        pc.same_row(schematic, M1, M3)  # M1 and M3 are in the same row
        pc.left_of(schematic, M1, M2)  # M1 is to the left of M2
        pc.left_of(schematic, M3, M4)  # M3 is to the left of M4
        pc.left_of(schematic, M2, M3)  # M2 is to the left of M3

        pc.clear_column_in_between_multi(
            schematic, transistors
        )  # Clear column between M1/M2 and M3/M4
    elif len(transistors) == 5:
        M1, M2, M3, M4, M5 = transistors
        # Define the placement constraints for the simple current mirror with five transistors
        pc.same_row(schematic, M1, M2)  # M1 and M2 are in the same row
        pc.same_row(schematic, M3, M4)  # M3 and M4 are in the same row
        pc.same_row(schematic, M4, M5)  # M4 and M5 are in the same row
        pc.same_row(schematic, M1, M3)  # M1 and M3 are in the same row
        pc.left_of(schematic, M1, M2)  # M1 is to the left of M2
        pc.left_of(schematic, M3, M4)  # M3 is to the left of M4
        pc.left_of(schematic, M2, M3)  # M2 is to the left of M3
        pc.left_of(schematic, M4, M5)  # M4 is to the left of M5
        pc.left_of(schematic, M3, M5)  # M3 is to the left of M5


def MosfetCascodedNMOSAnalogInverter(schematic, transistors: list):
    """Create placement constraints for a cascoded NMOS analog inverter."""

    # Ensure that the transistors are in the correct order
    assert (
        len(transistors) == 3
    ), "Expected 3 transistors for the cascoded NMOS analog inverter."

    M1, M2, M3 = transistors

    # Define the placement constraints for the cascoded NMOS analog inverter
    pc.above(schematic, M1, M2)  # M1 is above M2
    pc.above(schematic, M2, M3)  # M2 is above M3

    pc.same_column(schematic, M1, M2)  # M1 and M2 are in the same column
    pc.same_column(schematic, M2, M3)  # M2 and M3 are in the same column


def MosfetPmosNonInvertingInverter(schematic, transistors: list):
    """Create placement constraints for a PMOS non-inverting inverter."""

    # Ensure that the transistors are in the correct order
    assert (
        len(transistors) == 2
    ), "Expected 2 transistors for the PMOS non-inverting inverter."
    M1, M2 = transistors

    pc.above(schematic, M1, M2)  # M1 is above M2
    pc.same_column(schematic, M1, M2)  # M1 and M2 are in the same column


def MosfetAnalogInverter(schematic, transistors: list):
    """Create placement constraints for a simple analog inverter."""

    # Ensure that the transistors are in the correct order
    assert (
        len(transistors) == 2
    ), "Expected 2 transistors for the simple analog inverter."
    M1, M2 = transistors
    pc.above(schematic, M1, M2)  # M1 is above M2
    pc.same_column(schematic, M1, M2)  # M1 and M2 are in the same column


def MosfetNmosDiodeAnalogInverter(schematic, transistors: list):
    """Create placement constraints for a simple NMOS diode analog inverter."""

    # Ensure that the transistors are in the correct order
    assert (
        len(transistors) == 2
    ), "Expected 2 transistors for the NMOS diode analog inverter."
    M1, M2 = transistors
    pc.above(schematic, M1, M2)  # M1 is above M2
    pc.same_column(schematic, M1, M2)  # M1 and M2 are in the same column
