from alab_management import add_device
from alab_management import add_task

from .devices.furnace import Furnace
from .devices.robot_arm import RobotArm

from .tasks.heating import Heating
from .tasks.moving import Moving
from .tasks.starting import Starting
from .tasks.ending import Ending

add_device(Furnace(name="furnace_1"))
add_device(Furnace(name="furnace_2"))
add_device(Furnace(name="furnace_3"))
add_device(Furnace(name="furnace_4"))
add_device(RobotArm(name="dummy"))

add_task(Heating)
add_task(Moving)
add_task(Starting)
add_task(Ending)
