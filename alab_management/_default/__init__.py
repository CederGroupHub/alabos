"""
This is the entry point for the alab_management package. This package is used to manage the ALab project.

You will need to import all the device and task definitions in the project and register them using the `add_device`
and `add_task` functions.
"""

# import helper functions from alabos package
from alab_management.device_view import add_device
from alab_management.sample_view import SamplePosition, add_standalone_sample_position
from alab_management.task_view import add_task

# import all the device and task definitions here
# relative imports are recommended (starts with a dot)
from .devices.default_device import DefaultDevice
from .tasks.default_task import DefaultTask

# you can add the devices here. If they are the same type,
# you can use the same class and just change the name.
#
# For example, if you have 3 devices under different IP addresses,
# you can use the same class and just change the IP address and name.
# AlabOS will autoamtically decide which device to run an experiment
# based on their availability.
add_device(DefaultDevice(name="device_1", ip_address="192.168.1.11"))
add_device(DefaultDevice(name="device_2", ip_address="192.168.1.12"))
add_device(DefaultDevice(name="device_3", ip_address="192.168.1.13"))

# you can add all the tasks here
add_task(DefaultTask)

# When defining a device, you can define the sample positions related to that device,
# where the sample positions are bound to the device.
# AlabOS also provides a way to define standalone sample positions that are not bound to any device.
add_standalone_sample_position(
    SamplePosition(
        "default_standalone_sample_position",
        description="Default sample position",
        number=8,
    )
)
