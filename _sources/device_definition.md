# Defining devices and sample positions
The device refers to one piece of equipment in the lab, such as a box furnace, a robot arm, and etc. 
In alabos, the device object is usually a wrapper around the real device that provide serveral methods to interact with the device.

In each device object, there can be multiple sample positions associated with the device. The sample positions are the positions
where the samples are placed. For example, in a box furnace, there are multiple sample positions where the samples can be placed
and heated. In alabos, the position of each sample is recorded in the sample position which currently holds the sample.
If one sample occupies a sample position, the sample position cannot be used by other samples until the sample is moved.

The sample positions can also be standalone, which means that the sample positions are not associated with any device.

In this tutorial, we will show you how to define a new device and sample positions in alabos.

To define a device, you should inherit from [`BaseDevice`](alab_management.device_view.device.BaseDevice). `BaseDevice`
provides a basic interface for a device, with a few abstract methods that should be implemented in the derived class.

Other than the required abstract methods, you can also define additional methods that are specific to the device. For
example, you can define a `.do_powder_dosing` function for a powder dosing station, or a `.move_to` function for a robot arm.
The defined methods will be accessible to the task that uses the device.

We will take the box furnace as an example to show how to define a new device.

```{note}
If you are interested in how the communication can be implemented, you can check [`alab_control`](https://github.com/CederGroupHub/alab_control)
where all the communication with the device is implemented for A-Lab.

To install `alab_control`, you can run:

```bash
pip install git+https://github.com/CederGroupHub/alab_control
```

## Implementing `BoxFurnace`
First of all, we need to create a new class `BoxFurnace` that inherits from `BaseDevice`. 
```python
from alab_management import BaseDevice

class BoxFurnace(BaseDevice):
    pass
```

### Implementing all abstract methods
`BaseDevice` requires some of the basic metadata to be defined in the derived class. These include `sample_positions`, `connect`, 
`disconnect`, `is_running`.

First we need to import some dependencies:
```python
import time
from datetime import timedelta
from typing import ClassVar

from alab_control.door_controller import DoorController
from alab_control.furnace_2416 import FurnaceController, Segment
from alab_control.furnace_2416.furnace_driver import (
    FurnaceError,
    ProgramEndType,
    SegmentType,
)
from alab_management import BaseDevice
from alab_management import SamplePosition
```

The description of the device should be defined as a class variable. This description can provide some useful information
about the deivce.

```python
class BoxFurnace(BaseDevice):
    description: ClassVar[str] = (
        "The box furnace is a device that can heat samples up to 1200 degrees Celsius. "
        "It is used for heat treatment of samples. In current setting, one box furnace "
        "can hold up to 8 samples. Due to the limitation of the power supply, the "
        "max ramping rate is 10 degrees Celsius per minute."
    )
```

The `__init__` method should be implemented to store the information about the device. For example, if the device is
communicated through a serial port, you can store the serial port information here.

```python
def __init__(self, com_port_id: str, *args, **kwargs):
    """
    You can customize this method to store more information about the device. For example,
    if the device is communicated through a serial port, you can store the serial port information here.

    Args:
        com_port_id: The ID of the COM port that the device is connected to.
    """
    self.com_port_id = com_port_id
    self.door_controller = DoorController(
        names=[self.name], ip_address="192.168.0.51"
    )
    self.driver = None
    super().__init__(*args, **kwargs)
```

The `sample_positions` property should be implemented to return the sample positions of the device. The sample positions
are the positions inside the device where the samples are placed. It is used to track the samples in the system. When
setting up the system, all the sample positions will be created and stored in the database.

```python
@property
def sample_positions(self) -> list[SamplePosition]:
    """
    Return the sample positions of the BoxFurnace.

    Sample positions are the positions inside the device where the samples are placed.
    It is used to track the samples in the system. When setting up the system,
    all the sample positions will be created and stored in the database.
    """
    return [
        SamplePosition(
            "slot",
            description="The position inside the box furnace, where the samples are heated",
            number=8,
        ),
    ]
```

The `connect`, `disconnect`, and `is_running` methods should be implemented to connect to the device, disconnect from the
device, and check if the device is running, respectively.

```python
def get_driver(self):
    """Return the driver of the device. It is a helper method to get the driver of the device."""
    return FurnaceController(port=self.com_port_id)

def connect(self):
    """Connect to the BoxFurnace."""
    self.driver = self.get_driver()

def disconnect(self):
    """Disconnect from the BoxFurnace."""
    if self.driver is not None:
        self.driver.close()
    self.driver = None

def is_running(self):
    """Check if the device is running."""
    return self.driver.is_running()
```

### Defining the device interface
Apart from the required methods, you will need to define some additional methods that are specific to the device. For
example, for this type of the furnace, you will need a `run_program` method that will start the heating process. Also,
there is a `get_temperature` method that will return the current temperature of the furnace.

```python
class BoxFurnace(BaseDevice):
    ...
    
    def run_program(
        self,
        profiles: list[list[float]],
    ):
        """
        Run a heating program on the BoxFurnace.

        Args:
            profiles: A list of profiles. Each profile is a list of three elements:
                - The target temperature in Celsius.
                - The ramping rate in Celsius per minute.
                - The duration in minutes
        """
        segments = []
        for profile in profiles:
            segments.append(
                Segment(
                    segment_type=SegmentType.RAMP_RATE,
                    target_setpoint=profile[0],
                    ramp_rate_per_min=profile[1],
                )
            )
            segments = segments + [
                Segment(
                    segment_type=SegmentType.DWELL,
                    # the upper limit of heating is 900 minutes
                    duration=timedelta(
                        minutes=900 if i < (profile[2] // 900) else profile[2] % 900
                    ),
                )
                for i in range((profile[2] + 899) // 900)
            ]

        segments = [
            *segments,
            Segment(segment_type=SegmentType.END, endt=ProgramEndType.RESET),
        ]
        self.set_message(
            "Running a program with profiles:\n"
            + "\n".join(
                [
                    f"Setpoint: {profile[0]} C, "
                    f"Ramp rate: {profile[1]} C/min, "
                    f"Dwelling duration: {profile[2]} min"
                    for profile in profiles
                ]
            )
        )
        while True:
            try:
                self.driver.run_program(*segments)
                time.sleep(2)
            except FurnaceError:  # if there is an error, prompt the user to retry
                response = self.request_maintenance(
                    prompt="There is an error running the program. Do you want to retry?",
                    options=["Yes", "No"],
                )
                if response == "No":
                    raise  # if the user chooses not to retry, raise the error
            else:
                break

    def get_temperature(self):
        """Get the current temperature of the BoxFurnace."""
        return self.driver.get_temperature()
```
#### Setting up the message
In the `run_program` method, we set a message using `self.set_message()`. The message will be displayed in the UI. 
This message will be used to inform the user about the current state of the device. For example, 
when the device is heating, the message can be

```
Running a program with profiles: 
Setpoint: 1000 C, Ramp rate: 5 C/min, Dwelling duration: 60 min
```

#### Error handling
Sometimes there can be an error when using the device. To handle the error, we can use the `request_maintenance` method
to prompt the user to check the device and retry the operation. If the user chooses not to retry, the error will be raised.

```{note}
`BaseDevice.request_maintenance` is part of the user notification system in alabos. The user notification system is used as
a way for human-in-the-loop to interact with the system. At the moment when the system needs human intervention, it will
create a notification with a message and options for the user to choose. The system will react based on the user's choice.
```

In the `run_program` method, if there is an error when starting the program in the furnace, 
the user will be prompted to check the device and retry the operation. If the user chooses not to retry,
the error will be raised and the task that uses the device will be stopped.

### Mocking the device
When the code is made, it will be necessary to test it without connecting to the real device so that 
we can detect any bugs in the workflow. For this purpose, alabos provides a `@mock` decorator to
mock the device.

The `@mock` decorator can skip the method call and return a predefined value. For example, if you want to mock the
`get_temperature` method, you can use the following code:
```python
from alab_management import mock

class BoxFurnace(BaseDevice):
    ...
    
    @mock(return_constant=30)
    def get_temperature(self):
        return self.driver.get_temperature()
```

If it is in the simulation mode, the `get_temperature` method will return 30 without calling the real method to read
the furnace sensor.

What's more, you can also use the `@mock` decorator to return a mocked object. For example, if you want to mock the
`FurnaceController` object in the `get_driver` method, you can use the following code:

```python
from alab_management import mock

class BoxFurnace(BaseDevice):
    ...
    
    @mock(object_type=FurnaceController)
    def get_driver(self):
        return FurnaceController(port=self.com_port_id)
```

If the system is in the simulation mode, the `get_driver` method will return a mocked `FurnaceController` object. You can
still call the methods of the `FurnaceController` object, but the real methods will not be called.

```{note}
For more information about the `@mock` decorator, you can check its docstring at [`@mock`](alab_management.device_view.device.mock).
```

## Registering the device
After defining the device, you will also need to register the device in the system. To do so,
you can use the `add_device` method in the `__init__.py` file at the root of the folder.

`add_device` takes a device object as an argument and registers the device in the system. You will need to
pass a unique device name as well as other arguments that are required by the device when creating the device object.

You can create multiple devices in the `__init__.py` file. For example, if you have four box furnaces, you can create
four box furnaces in the `__init__.py` file as follows:

```python
from alab_management import add_device

from .devices.box_furnace import BoxFurnace

add_device(BoxFurnace(name="box_1", com_port_id="COM3"))
add_device(BoxFurnace(name="box_2", com_port_id="COM4"))
add_device(BoxFurnace(name="box_3", com_port_id="COM5"))
add_device(BoxFurnace(name="box_4", com_port_id="COM6"))
```

## Registering standalone sample positions
Sometimes, the sample positions may not be associated with any device. For example, you may have serveral sample positions
that are served as a buffer area for the crucibles. In this case, you can register the standalone sample positions in the
`__init__.py` file as well:

```python
from alab_management import add_standalone_sample_position, SamplePosition

add_standalone_sample_position(
    SamplePosition(
        "crucible_buffer",
        description="The buffer area for the crucibles",
        number=16,
    )
)
```

## What's next
After defining the device, you can use the device in the task. In the next tutorial, we will show you how to create a task
that will request the device and sample positions to perform the experiment.
