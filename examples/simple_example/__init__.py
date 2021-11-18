from alab_management import add_device
from alab_management import add_task

from .devices.furnace import Furnace
from .devices.robot_arm import RobotArm
from .devices.scale import Scale

from .tasks.heating import Heating
from .tasks.moving import Moving
from .tasks.weighing import Weighing
from .tasks.pouring import Pouring
from .tasks.starting import Starting
from .tasks.ending import Ending

add_device(Furnace(name="furnace", address="128.3.19.20"))
add_device(Scale(name="ipad"))
add_device(RobotArm(name="dummy", address="128.3.19.7"))

add_task(Heating)
add_task(Moving)
add_task(Weighing)
add_task(Pouring)
add_task(Starting)
add_task(Ending)
