"""Initialize tasks and devices for the ALab_One system."""

import os
from pathlib import Path

# set the config path to the default config file
# keep this line at the top of the file
os.environ["ALABOS_CONFIG_PATH"] = (
    Path(__file__).parent.absolute() / "config.toml"
).as_posix()

from alab_control.door_controller import DoorController

from alab_management import (
    SamplePosition,
    add_device,
    add_standalone_sample_position,
    add_task,
)

from .devices.ball_dispenser import BallDispenser
from .devices.box_furnace import BoxFurnace
from .devices.cap_dispenser import CapDispenser
from .devices.capping_gripper import CappingGripper
from .devices.diffractometer import Diffractometer
from .devices.labman_quadrant import LabmanQuadrant
from .devices.manual_furnace import ManualFurnace
from .devices.robot_arm_characterization import RobotArmCharacterization
from .devices.robot_arm_furnaces import RobotArmFurnaces
from .devices.scale import Scale
from .devices.shaker import Shaker
from .devices.transfer_rack import TransferRack
from .devices.tube_furnace import TubeFurnace
from .devices.vial_dispenser_rack import VialDispenserRack
from .devices.vial_labeler import VialLabeler
from .devices.xrd_dispenser_rack import XRDDispenserRack
from .tasks.diffraction import Diffraction, PrepareSampleforXRD
from .tasks.ending import Ending
from .tasks.heating import Heating
from .tasks.heating_with_atmosphere import HeatingWithAtmosphere
from .tasks.manual_heating import ManualHeating
from .tasks.moving import Moving
from .tasks.powder_dosing import PowderDosing
from .tasks.recover_powder import RecoverPowder
from .tasks.starting import Starting

doorcontroller_AB = DoorController(ip_address="192.168.0.41", names=["A", "B"])
doorcontroller_CD = DoorController(ip_address="192.168.0.42", names=["C", "D"])

add_device(
    BoxFurnace(
        name="box_a",
        com_port="COM17",
        door_controller=doorcontroller_AB,
        furnace_letter="A",
    )
)

add_device(
    BoxFurnace(
        name="box_b",
        com_port="COM15",
        door_controller=doorcontroller_AB,
        furnace_letter="B",
    )
)

add_device(
    BoxFurnace(
        name="box_c",
        com_port="COM14",
        door_controller=doorcontroller_CD,
        furnace_letter="C",
    )
)

add_device(
    BoxFurnace(
        name="box_d",
        com_port="COM13",
        door_controller=doorcontroller_CD,
        furnace_letter="D",
    )
)

# # TODO: delete this (start)
add_device(
    ManualFurnace(
        name="manual_b",
        furnace_letter="B",
    )
)

add_device(
    ManualFurnace(
        name="manual_i",
        furnace_letter="I",
    )
)

add_device(
    ManualFurnace(
        name="manual_j",
        furnace_letter="J",
    )
)

add_device(
    ManualFurnace(
        name="manual_k",
        furnace_letter="K",
    )
)

# # TODO: delete this (end)

add_device(TubeFurnace(name="tube_e", furnace_index=1))
add_device(
    TubeFurnace(name="tube_f", furnace_index=2)
)  # offline until we can catch errors with door not closing properly
add_device(TubeFurnace(name="tube_g", furnace_index=3))
add_device(TubeFurnace(name="tube_h", furnace_index=4))

# labman
add_device(LabmanQuadrant(name="labmanquadrant_1", quadrant_index=1))
add_device(LabmanQuadrant(name="labmanquadrant_2", quadrant_index=2))
add_device(LabmanQuadrant(name="labmanquadrant_3", quadrant_index=3))
add_device(LabmanQuadrant(name="labmanquadrant_4", quadrant_index=4))

# Robot Arms
add_device(
    RobotArmFurnaces(
        name="arm_furnaces",
        ip="192.168.0.22",
        description="UR5e robot arm to move samples on the furnace side of the ALab",
    )
)
add_device(
    RobotArmCharacterization(
        name="arm_characterization",
        ip="192.168.0.23",
        description="UR5e robot arm to move samples on the characterization side of the ALab",
    )
)

# # Powder Collection
# # TODO addresses to connect to all of these
add_device(BallDispenser(name="dispenser_balls", ip_address="192.168.0.33"))
# add_device(Ca(name="dispenser_vials"))  # TODO
add_device(
    CapDispenser(name="dispenser_caps", ip_address="192.168.0.31")
)  # One device to get lids ets

add_device(Shaker(name="shaker", ip_address="192.168.0.32"))
add_device(Scale(name="scale", ip_address="192.168.0.24"))  # TODO
add_device(CappingGripper(name="cappinggripper", ip_address="192.168.0.51"))
add_device(
    VialDispenserRack(
        name="fresh_vial_rack",
        description="A set of racks to hold fresh vials for powder grinding.",
    )
)
add_device(
    VialLabeler(
        name="vial_labeler",
        description="An inket printer for labeling filled vials.",
    )
)

# XRD
add_device(
    XRDDispenserRack(
        name="dispenser_xrd",
        description="A rack to hold clean and dirty sample holders for XRD.",
    )
)

add_device(
    Diffractometer(
        name="aeris_xrd",
        description="Aeris XRD automated diffractometer.",
        address="aeris.lbl.gov",
        results_dir=r"D:\\AerisData",
    )
)

# Sample Positions
add_standalone_sample_position(
    SamplePosition(
        name="labman_rack",
        number=16,
        description="Rack to hold crucibles between the labman and furnace area.",
    )
)
add_device(
    TransferRack(
        name="transfer_rack",
        num_slots=6,
        description="Rack to hold crucibles between the furnace and characterization area.",
    )
)  # device because it can be reached by multiple robot arms. Tasks will reserve the device to prevent collision when
# two tasks/arms want to access slots at the same time.

add_standalone_sample_position(
    SamplePosition(
        name="filled_vial_rack",
        number=16,
        description="Rack to hold vials containing powders. This is located in the characterization area.",
    )
)

add_standalone_sample_position(
    SamplePosition(
        name="powdertransfer_crucible_position",
        number=1,
        description="Position to temporarily place a crucible during powder handling steps."
        "This is on the main breadboard on the characterization side.",
    )
)

add_standalone_sample_position(
    SamplePosition(
        name="powdertransfer_vial_position",
        number=1,
        description="Position to temporarily place a vial during powder handling steps."
        "This is on the main breadboard on the characterization side.",
    )
)
add_standalone_sample_position(
    SamplePosition(
        name="powdertransfer_xrd_position",
        number=1,
        description="Position to temporarily place an XRD sample holder during powder handling steps."
        "This is on the main breadboard on the characterization side.",
    )
)
add_standalone_sample_position(
    SamplePosition(
        name="cap_position",
        number=2,
        description="Position to temporarily place caps during powder handling steps."
        "This is on the main breadboard on the characterization side.",
    )
)

add_standalone_sample_position(
    SamplePosition(
        name="vial_tapping_position",
        number=2,
        description="Position to place a vial to receive powder dumped/tapped out of a crucible."
        "This is immediately to the right of the vertical shaker. Note this is not a part of the shaker itself.",
    )
)

add_standalone_sample_position(
    SamplePosition(
        name="buffer_rack",
        number=20,
        description="Buffer rack for crucible after heating.",
    )
)

add_standalone_sample_position(
    SamplePosition(
        name="filled_vial_storage_bin_A",
        number=64,  # TODO: is there a better way to determine this?
        description="Position to place filled vials after labeling. This is the bin under the shaker.",
    )
)

add_standalone_sample_position(
    SamplePosition(
        name="filled_vial_storage_bin_B",
        number=64,  # TODO: is there a better way to determine this?
        description="Position to place filled vials after labeling. This is the bin under the shaker.",
    )
)

add_standalone_sample_position(
    SamplePosition(
        name="filled_vial_storage_bin_C",
        number=64,  # TODO: is there a better way to determine this?
        description="Position to place filled vials after labeling. This is the bin under the shaker.",
    )
)


# ## Tasks
add_task(Starting)
add_task(PowderDosing)
add_task(Moving)
add_task(Heating)
add_task(ManualHeating)
add_task(HeatingWithAtmosphere)
add_task(RecoverPowder)
add_task(PrepareSampleforXRD)
add_task(Diffraction)
add_task(Ending)
