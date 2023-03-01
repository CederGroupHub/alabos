from alab_management import add_device

from .furnace import furnace_1, furnace_2, furnace_3, furnace_4
from .robot_arm import robot_arm

add_device(furnace_1)
add_device(furnace_2)
add_device(furnace_3)
add_device(furnace_4)
add_device(robot_arm)
