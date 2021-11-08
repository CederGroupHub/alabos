from alab_management import add_device
from alab_management import add_task

from .devices.furnace import Furnace
from .devices.robot_arm import RobotArm

from .tasks.heating import Heating
from .tasks.moving import Moving

add_device(Furnace(name="furnace_1", address="127.0.0.1"))
add_device(Furnace(name="furnace_2", address="127.0.0.2"))
add_device(Furnace(name="furnace_3", address="127.0.0.3"))
add_device(Furnace(name="furnace_4", address="127.0.0.4"))
add_device(RobotArm(name="dummy", address="127.0.0.1"))

add_task(Heating)
add_task(Moving)
