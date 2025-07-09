from alab_management.device_view import add_device
from alab_management.sample_view import SamplePosition, add_standalone_sample_position
from alab_management.task_view import add_task
from tests.fake_lab.devices import (
    DeviceThatFails,
    DeviceThatNeverEnds,
    DeviceThatRunSlow,
    Furnace,
    RobotArm,
)
from tests.fake_lab.tasks import (
    Ending,
    ErrorHandlingRecoverable,
    ErrorHandlingUnrecoverable,
    Heating,
    InfiniteTask,
    Moving,
    Starting,
    TakePicture,
    TakePictureMissingResult,
    TakePictureWithoutSpecifiedResult,
)

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
