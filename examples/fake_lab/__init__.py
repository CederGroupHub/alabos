from alab_management import add_device
from alab_management import add_task
from .devices.furnace import Furnace
from .devices.robot_arm import RobotArm
from .tasks.ending import Ending
from .tasks.heating import Heating
from .tasks.moving import Moving
from .tasks.starting import Starting

from alab_management import add_standalone_sample_position
from alab_management import SamplePosition

add_device(Furnace(name="furnace_1"))
add_device(Furnace(name="furnace_2"))
add_device(Furnace(name="furnace_3"))
add_device(Furnace(name="furnace_4"))
add_device(RobotArm(name="dummy"))

add_standalone_sample_position(SamplePosition(
    "furnace_table", description="Temporary position to transfer samples"
))

add_standalone_sample_position(SamplePosition(
    "furnace_temp",
    number=4,
    description="Test positions",
))

add_task(Starting)
add_task(Moving)
add_task(Heating)
add_task(Ending)
