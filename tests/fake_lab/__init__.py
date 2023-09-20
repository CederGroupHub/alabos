from alab_management import add_device
from alab_management import add_task
from .devices.furnace import furnace_1, furnace_2, furnace_3, furnace_4
from .devices.robot_arm import robot_arm
from .tasks.ending import Ending
from .tasks.heating import Heating
from .tasks.moving import Moving
from .tasks.starting import Starting

add_device(furnace_1)
add_device(furnace_2)
add_device(furnace_3)
add_device(furnace_4)
add_device(robot_arm)
add_task(Starting)
add_task(Moving)
add_task(Heating)
add_task(Ending)
