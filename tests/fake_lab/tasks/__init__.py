from alab_management import add_task

from .ending import Ending
from .heating import Heating
from .moving import Moving
from .starting import Starting

add_task(Starting)
add_task(Moving)
add_task(Heating)
add_task(Ending)
