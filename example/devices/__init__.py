from alab_management.device_def import add_device
from .furnace import Furnace
from .robot_arm import RobotArm

add_device(Furnace("furnace_1", address="127.0.0.1"))
add_device(Furnace("furnace_2", address="127.0.0.2"))
add_device(Furnace("furnace_3", address="127.0.0.3"))
add_device(Furnace("furnace_4", address="127.0.0.4"))

add_device(RobotArm("dummy", address="127.0.0.1"))
