from alab_management.device_view import add_device
from alab_management.sample_view import SamplePosition, add_standalone_sample_position
from alab_management.task_view import add_task

from .devices import DeviceThatFails
from .devices import DeviceThatNeverEnds
from .devices import DeviceThatRunSlow
from .devices import Furnace
from .devices import RobotArm

from .tasks import Ending
from .tasks import ErrorHandlingRecoverable
from .tasks import ErrorHandlingUnrecoverable
from .tasks import Heating
from .tasks import InfiniteTask
from .tasks import Moving
from .tasks import Starting
from .tasks import TakePicture
from .tasks import TakePictureMissingResult
from .tasks import TakePictureWithoutSpecifiedResult

add_device(Furnace(name="furnace_1"))
add_device(Furnace(name="furnace_2"))
add_device(Furnace(name="furnace_3"))
add_device(Furnace(name="furnace_4"))
add_device(RobotArm(name="dummy"))
add_device(DeviceThatFails(name="device_that_fails"))
add_device(DeviceThatNeverEnds(name="device_that_never_ends"))
add_device(DeviceThatRunSlow(name="device_that_run_slow"))
add_device(DeviceThatRunSlow(name="device_that_run_slow_2"))

add_standalone_sample_position(
    SamplePosition(
        "furnace_table", description="Temporary position to transfer samples"
    )
)

add_standalone_sample_position(
    SamplePosition(
        "furnace_temp",
        # 64 samples can be held at the same time. This is used for launching a lot of samples at the same time.
        number=64,
        description="Test positions",
    )
)

add_task(Starting)
add_task(Moving)
add_task(Heating)
add_task(Ending)
add_task(ErrorHandlingUnrecoverable)
add_task(ErrorHandlingRecoverable)
add_task(InfiniteTask)
add_task(TakePicture)
add_task(TakePictureMissingResult)
add_task(TakePictureWithoutSpecifiedResult)
