# Testing for AlabOS Project


To ensure a seamless installation and robust testing of the software system, several key processes have been implemented.

1. Testing Framework
   - a suite of unit tests using the pytest framework. These tests cover
all functionalities of tasks and devices, ensuring that each component works as expected
in isolation.
   - In addition to unit tests, integration tests are also developed. These tests validate the
interactions between different components of the system. Integration tests are simulating
real-world scenarios which help us to ensure that the system works correctly as a whole.

2. Continuous Integration (CI)
   - A CI pipeline is set up using tools like GitHub Actions. This pipeline automatically runs
the entire test suite (both unit and integration tests) whenever new code is committed.
This ensures that any changes introduced do not break existing functionalities.

## Methodology

Before writing the unit tests, one needs to modify the files under devices & tasks by adding the ``@mock decorator`` to all the places that require connections to all the hardware in Alab.

This decorator is defined in ``alab_management/device_view/device``. The decorator uses the ``Mock`` class from ``unittest.mock`` to create dummy instances of all the objects that require API calls, including all the devices and their corresponding drivers. All the drivers of the devices are defined in alab_control which need to be mocked. Thus, the key to write good class definitions is to be able to identify the methods that talk to drivers. The mock decorator is activated by setting up the env variable — ``SIM_MODE_FLAG = True``. If the SIM_MODE_FLAG is set to ``False`` then the code will try to connect to the real devices which will result in an error, unless you are running the code in Sauron — the computer that runs the real Alab!

- **Step 1**: decorate the get_driver method inside the devices folder with @mock, and specify the object type that needs to get mocked. Make sure that the object to be mocked is one of the return objects. You can also return a constant value if the return is a fixed value.

- **Step 2**: most of the run_program methods have sub-methods that call in methods from alab_control in the form of ``self.driver.is_running()`` or any other method from self.driver 

- **Step 3**: look out for other methods that are communicating with the methods from alab_control, and decorate with @mock by assigning a suitable return_value or return_type.

Once all the methods that talk to alab_control are mocked, we can now move on to writing the actual unit tests. The unit tests make use of pytest testing framework for writing the unit-tests. We make use of ``pytest.fixtures()`` to create class level and module level fixtures that can be used by the individual unittests. By default, all the unittests start with ``test_{name of the method for which unit tests is written}``. Remember that a single method can have multiple unittests depending upon all the cases whose behaviour needs to be checked. 

- **Step 4**: one has to create pytest fixtures for all the objects that talk with the alab_control package. All the methods (ex: drivers) from alab_control need to be mocked using MagicMock from unittest.mock. Also, all the methods from alab_one that communicate with alab_control need to mocked by setting them to mocked methods using monkeypatch.setattr from pytest. Once done, these fixtures can now be used to test the methods from the classes defined in alab_one devices and tasks.

- **Step 5**:  Each unittest primarly checks the following three things: 

   1. if the object type is the one that we were expecting
   2. if the return of the method is correct
   3. the number of times a particular method gets called

- **Step 6**: The unittests for tasks are also similar. They have certain pytest fixtures that can be used by the downstream unittests. These unit tests provide a set of dummy config, path and input files and checks whether the expected outcomes are met.

## Example

### Device Class: BoxFurnace
Key functionalities of the BoxFurnace class:

   - `initialization`: Sets up communication port, driver, door controller, and furnace letter.
   - `connect/disconnect`: Manages connection to the furnace driver.
   - `run_program`: Executes heating programs with specified parameters or profiles.
   - `emergent_stop`: Immediately stops the furnace operation.
   - `get_temperature`: Retrieves the current temperature.
   - `open_door/close_door`: Manages the furnace door operations.
   - `is_running`: Checks if the furnace is currently running a program.

#### Fixtures
Fixtures set up the necessary preconditions for the tests:

   - `door_controller_ab` and `door_controller_cd`: Create instances of DoorController
for different sets of furnaces.
   - `box_furnace`: Parameterized fixture to create BoxFurnace instances with various
configurations.
   - `mock_drivers`: Mocks the furnace and door controller drivers to isolate and test
BoxFurnace methods without real hardware.

#### Tests

1. Basic Connection Tests:
   - `test_connect`: Verifies that the connect method correctly initializes the
furnace and door controller drivers.
   - `test_disconnect:` Ensures that the disconnect method properly sets the
furnace driver to None.

```python
def test_connect(box_furnace, mock_drivers):
	box_furnace.connect()
	assert box_furnace.driver is mock_drivers[0]
	assert box_furnace.door_controller is mock_drivers[1]
	
def test_disconnect(box_furnace, mock_drivers):
    box_furnace.driver = mock_drivers[0]
    box_furnace.disconnect()
    assert box_furnace.driver is None
```

2. Functional Tests:
   - `test_sample_positions`: Checks the sample_positions property to ensure it
returns expected slot details.
   - `test_emergent_stop`: Confirms that the emergent_stop method calls the
driver’s stop function.

```python
def test_sample_positions(box_furnace):
    positions = box_furnace.sample_positions
    assert len(positions) == 1
    assert positions[0].name == "slot"
    assert positions[0].description == "The position inside the box furnace, where the samples are heated"
    assert positions[0].number == 8
    
 def test_emergent_stop(box_furnace, mock_drivers):
    box_furnace.driver = mock_drivers[0]
    box_furnace.emergent_stop()
    box_furnace.driver.stop.assert_called_once()
```

3. Program Execution Tests:
   - `test_run_program`: Validates the run_program method for specified heating
times and temperatures, ensuring segments are correctly constructed and
sent to the driver.
   - `test_run_program_with_profiles`: Tests running custom heating profiles to
verify segment creation and driver invocation.

4. Utility Tests:
   - `test_is_running`: Checks if the is_running method correctly returns the
furnace’s running state based on environment variables.
   - `test_get_temperature`: Ensures the get_temperature method fetches the
current temperature from the driver.

   - `test_open_door` and `test_close_door`: Verify that the open_door and close_door methods invoke
   - the door controller’s methods with the correct parameters.


#### Source code
The whole source code for the BoxFurnace class is attached below:

```python
"""This module contains unit tests for the BoxFurnace class."""

import os
from datetime import timedelta
from unittest.mock import MagicMock

import pytest
from alab_control.door_controller import DoorController
from alab_control.furnace_2416 import FurnaceController, Segment
from alab_control.furnace_2416.furnace_driver import (
    ProgramEndType,
    SegmentType,
)

from alab_example.devices.box_furnace import BoxFurnace


@pytest.fixture()
def door_controller_ab():
    """Fixture for DoorController instance for furnaces A and B."""
    return DoorController(ip_address="192.168.0.41", names=["A", "B"])

@pytest.fixture()
def door_controller_cd():
    """Fixture for DoorController instance for furnaces C and D."""
    return DoorController(ip_address="192.168.0.42", names=["C", "D"])

@pytest.fixture(params=[("A", "COM17", door_controller_ab),
                        ("B", "COM15", door_controller_ab),
                        ("C", "COM14", door_controller_cd),
                        ("D", "COM13", door_controller_cd)])
def box_furnace(request):
    """Fixture to create a BoxFurnace instance for each test case."""
    furnace_letter, com_port, door_controller = request.param
    return BoxFurnace(name=f"box_{furnace_letter.lower()}",
                      com_port=com_port,
                      door_controller=door_controller,
                      furnace_letter=furnace_letter)

@pytest.fixture()
def mock_drivers(monkeypatch):
    """Fixture to mock the drivers for furnace and door controller."""
    mock_furnace_driver = MagicMock(spec=FurnaceController)
    mock_door_controller = MagicMock(spec=DoorController)
    # Correctly mock get_driver to return both mocks as a tuple
    monkeypatch.setattr("alab_one.devices.box_furnace.BoxFurnace.get_driver",
                        MagicMock(return_value=(mock_furnace_driver, mock_door_controller)))
    return mock_furnace_driver, mock_door_controller

@pytest.fixture(autouse=True)
def isolate_env_vars():
    """Fixture to isolate the environment variables."""
    old_value = os.getenv("SIM_MODE_FLAG")
    yield
    if old_value is None:
        os.unsetenv("SIM_MODE_FLAG")
    else:
        os.environ["SIM_MODE_FLAG"] = old_value

def test_connect(box_furnace, mock_drivers):
    """Test the connect method."""
    box_furnace.connect()
    assert box_furnace.driver is mock_drivers[0]
    assert box_furnace.door_controller is mock_drivers[1]

def test_disconnect(box_furnace, mock_drivers):
    """Test the disconnect method."""
    box_furnace.driver = mock_drivers[0]
    box_furnace.disconnect()
    assert box_furnace.driver is None

def test_sample_positions(box_furnace):
    """Test the sample_positions property."""
    positions = box_furnace.sample_positions
    assert len(positions) == 1
    assert positions[0].name == "slot"
    assert positions[0].description == "The position inside the box furnace, where the samples are heated"
    assert positions[0].number == 8

def test_emergent_stop(box_furnace, mock_drivers):
    """Test the emergency stop method."""
    # Ensure the furnace is connected, setting up the driver and door controller
    box_furnace.driver = mock_drivers[0]
    box_furnace.emergent_stop()
    box_furnace.driver.stop.assert_called_once()

def test_run_program(box_furnace, mock_drivers):
    """Test running a heating program with specific parameters."""
    heating_time_minutes = 120
    heating_temperatures = [1000,200]

    # Directly assign the mock_driver to the box_furnace's driver attribute
    box_furnace.driver = mock_drivers[0]
    for heating_temperature in heating_temperatures:
        box_furnace.run_program(heating_time_minutes=heating_time_minutes, heating_temperature=heating_temperature)
        if heating_temperature > 300:
            heating_segment = [
                            Segment(
                                segment_type=SegmentType.RAMP_RATE,
                                target_setpoint=300,
                                ramp_rate_per_min=2,
                            ),
                        ]
        else:
            heating_segment = []
        segments = (
                    heating_segment
                    + [
                        Segment(
                            segment_type=SegmentType.RAMP_RATE,
                            target_setpoint=heating_temperature,
                            ramp_rate_per_min=5,
                        )
                    ]
                    + [
                        Segment(
                            segment_type=SegmentType.DWELL,
                            # the upper limit of heating is 900 minutes
                            duration=timedelta(
                                minutes=900 if i < heating_time_minutes // 900 else heating_time_minutes % 900
                            ),
                        )
                        for i in range((heating_time_minutes + 899) // 900)
                    ]
                )
        segments = [*segments, Segment(segment_type=SegmentType.END, endt=ProgramEndType.RESET)]
        box_furnace.driver.run_program.assert_called_with(*segments)

def test_run_program_with_profiles(box_furnace, mock_drivers):
    """Test running a program with a custom profile."""
    profiles = [[1000, 5, 60], [1200, 5, 240]]

    # Directly assign the mock_driver to the box_furnace's driver attribute
    box_furnace.driver = mock_drivers[0]

    # Mock the run_program method to simulate successful box furnace operation
    mock_drivers[0].run_program.side_effect = None  # No exception raised

    box_furnace.run_program(profiles=profiles)

    # Verify the correct segments were created and passed to run_program
    expected_segments = [
        Segment(SegmentType.RAMP_RATE, target_setpoint=profiles[0][0], ramp_rate_per_min=profiles[0][1]),
        Segment(SegmentType.DWELL, duration=timedelta(minutes=profiles[0][2])),
        Segment(SegmentType.RAMP_RATE, target_setpoint=profiles[1][0], ramp_rate_per_min=profiles[1][1]),
        Segment(SegmentType.DWELL, duration=timedelta(minutes=profiles[1][2])),
        Segment(SegmentType.END, endt=ProgramEndType.RESET)
    ]
    # This is a simplified assertion. You should adjust it based on the exact behavior of your run_program method.
    mock_drivers[0].run_program.assert_called_with(*expected_segments)

def test_is_running(box_furnace, mock_drivers):
    """Test the is_running method."""
    os.environ["SIM_MODE_FLAG"] = "False"
    mock_drivers[0].is_running.return_value = True
    assert mock_drivers[0].is_running() is True

    os.environ["SIM_MODE_FLAG"] = "True"
    mock_drivers[0].is_running.return_value = False
    assert mock_drivers[0].is_running() is False

def test_get_temperature(box_furnace, mock_drivers):
    """Test the get_temperature method."""
    # Directly assign the mock_driver to the box_furnace's driver attribute
    box_furnace.driver = mock_drivers[0]

    # Set a mock temperature to be returned by the driver
    mock_temperature = 30.0
    mock_drivers[0].current_temperature = mock_temperature
    # Check if the get_temperature method correctly fetches the temperature
    assert box_furnace.get_temperature() == mock_temperature

    os.environ["SIM_MODE_FLAG"] = "False"
    mock_temperature = 60.0
    mock_drivers[0].current_temperature = mock_temperature
    assert box_furnace.get_temperature() == mock_temperature


def test_open_door(box_furnace, mock_drivers):
    """Test the open_door method."""
    # Directly assign the mock_driver to the door_controller's driver attribute
    box_furnace.door_controller = mock_drivers[1]

    # Invoke the open_door method
    box_furnace.open_door()

    # Verify that the door_controller's open method was called with the correct parameters
    mock_drivers[1].open.assert_called_once_with(name=box_furnace.furnace_letter)

def test_close_door(box_furnace, mock_drivers):
    """Test the close_door method."""
    # Directly assign the mock_driver to the door_controller's driver attribute
    box_furnace.door_controller = mock_drivers[1]

    # Invoke the close_door method
    box_furnace.close_door()

    # Verify that the door_controller's close method was called with the correct parameters
    mock_drivers[1].close.assert_called_once_with(name=box_furnace.furnace_letter)
```

### Task Class: Heating

Similar to the CI of the box furnace, we can also use pytest fixtures and mock to test the tasks. 

```python
"""This module contains unit tests for the Heating class."""

import os
from itertools import chain, repeat
from unittest.mock import MagicMock, patch

import pytest

from alab_example.devices.box_furnace import BoxFurnace
from alab_example.devices.labman_quadrant import LabmanQuadrant
from alab_example.devices.robot_arm_furnaces import RobotArmFurnaces
from alab_example.tasks import Heating


@pytest.fixture()
def lab_view_mock():
    mock = MagicMock()

    mock_box_furnace = MagicMock(spec=BoxFurnace)
    mock_box_furnace.name = "box_furnace_mock"

    mock_box_furnace.get_temperature.return_value = 25.0
    mock_robot_arm = MagicMock(spec=RobotArmFurnaces)
    mock_labman_quadrant = MagicMock()
    mock_labman_quadrant.name = "labman_quadrant_mock"

    devices_mock = {
        BoxFurnace: mock_box_furnace,
        RobotArmFurnaces: mock_robot_arm,
        "labmanquadrant_1": mock_labman_quadrant,
    }

    sample_positions_mock = {BoxFurnace: {"slot": ["A/1", "A/2"]}}

    mock_request_resources_context = MagicMock()
    mock_request_resources_context.__enter__.return_value = (devices_mock, sample_positions_mock)
    mock_request_resources_context.__exit__.return_value = None
    mock.request_resources.return_value = mock_request_resources_context

    mock.get_sample.return_value = MagicMock(position="Position_1")
    mock.request_user_input.return_value = "OK"
    mock.get_sample_position_parent_device.return_value = "labmanquadrant_1"
    return mock


@pytest.fixture()
def heating(lab_view_mock):
    return Heating(heating_time=60, heating_temperature=500, samples=["sample1", "sample2"], lab_view=lab_view_mock)


def test_validate(heating):
    # Test valid setup
    assert heating.validate() == True

    # Test invalid number of samples
    heating = Heating(10, 300, samples=[f"sample{i}" for i in range(9)])
    with pytest.raises(ValueError) as ex:
        heating.validate()
    assert (str(ex.value)) == "Number of samples must be between 1 and 8"

    # Test invalid heating temperature
    heating = Heating(10, 300, samples=["sample1", "sample2"])
    heating.heating_temperature = 1200  # Above MAX_TEMPERATURE
    with pytest.raises(ValueError) as ex:
        heating.validate()
    assert (
        str(ex.value)
    ) == "Heating temperature ({self.heating_temperature}) must be less than {self.MAX_TEMPERATURE} C!"


def test_check_for_labman_quadrant_single_quadrant(heating, lab_view_mock):
    heating = Heating(heating_time=60, heating_temperature=500, samples=["sample1"], lab_view=lab_view_mock)
    heating.lab_view = lab_view_mock
    heating.lab_view.get_sample.return_value = MagicMock(position="Position_1")
    heating.lab_view.get_sample_position_parent_device.return_value = "labmanquadrant_1"
    assert heating.check_for_labman_quadrant() == "labmanquadrant_1"

    heating.lab_view.get_sample_position_parent_device.return_value = ""
    assert heating.check_for_labman_quadrant() == None


@pytest.fixture()
def furnace_and_log():
    # Mock the BoxFurnace object
    furnace_mock = MagicMock()
    furnace_mock.get_temperature.return_value = 100

    temperature_log = {"time_minutes": [], "temperature_celsius": []}
    return furnace_mock, temperature_log


def test_cooldown(furnace_and_log, lab_view_mock):
    os.environ["SIM_MODE_FLAG"] = "False"
    furnace_mock, temperature_log = furnace_and_log
    heating_task = Heating(heating_time=60, heating_temperature=500, samples=["sample1"], lab_view=lab_view_mock)

    start_time = 0

    def fake_time():
        nonlocal start_time
        start_time += heating_task.LOGGING_INTERVAL_SECONDS * 60
        return start_time

    with patch("time.sleep", return_value=None) as mock_sleep, patch("time.time", side_effect=fake_time) as mock_time:
        updated_log = heating_task.cooldown(furnace_mock, temperature_log)

        assert len(updated_log["time_minutes"]) > 0
        assert updated_log["temperature_celsius"][-1] == 100
    # We need to return the flag to True since otherwise there will be leakage between tests!
    os.environ["SIM_MODE_FLAG"] = "True"


def test_run(heating, lab_view_mock):
    # Set the initial time for the fake_time function
    start_time = [0]

    def fake_time():
        start_time[0] += heating.LOGGING_INTERVAL_SECONDS * 6
        return start_time[0]

    # Create mocks for BoxFurnace, RobotArmFurnaces, and LabmanQuadrant
    box_furnace_mock = MagicMock(spec=BoxFurnace, name="box_furnace_mock")
    box_furnace_mock.name = "box_furnace_mock"
    robot_arm_mock = MagicMock(spec=RobotArmFurnaces)
    labman_quadrant_mock = MagicMock(spec=LabmanQuadrant)
    labman_quadrant_mock.name = "labmanquadrant_mock"

    # Simulate is_running() being True twice, then False.
    is_running_side_effect = chain([True, True], repeat(False))
    box_furnace_mock.is_running.side_effect = is_running_side_effect
    box_furnace_mock.get_temperature.return_value = 100.0  # Return a fixed temperature

    # Simulate BoxFurnace, RobotArmFurnaces, and LabmanQuadrant being part of the resources returned by request_resources
    mock_context_manager = MagicMock()
    mock_context_manager.__enter__.return_value = (
        {
            BoxFurnace: box_furnace_mock,
            RobotArmFurnaces: robot_arm_mock,
            "labmanquadrant_1": labman_quadrant_mock,
        },  # Devices
        {BoxFurnace: {"slot": [1, 2, 3, 4, 5, 6, 7, 8]}},
    )

    # Assuming fake_time() is defined as before to simulate the passage of time
    with patch("time.time", side_effect=fake_time), patch("time.sleep", return_value=None):
        lab_view_mock.request_resources.return_value = mock_context_manager
        heating.lab_view = lab_view_mock
        result = heating.run()

        lab_view_mock.request_resources.assert_called()
        retrieved_box_furnace = mock_context_manager.__enter__.return_value[0][BoxFurnace]
        retrieved_box_furnace.open_door.assert_called()
        retrieved_robot_arm = mock_context_manager.__enter__.return_value[0][RobotArmFurnaces]
        retrieved_robot_arm.move_rack_into_box_furnace.assert_called()
        retrieved_labman_quadrant = mock_context_manager.__enter__.return_value[0]["labmanquadrant_1"]
        assert result == {  
                            "heating_temperature": 500,
                            "heating_time": 60,
                            "heating_profiles": None,
                            "cooling_rate": None,
                            "low_temperature_calcination": False,
                            "temperature_log": 
                            {"time_minutes": [6.0, 18.0], 
                            "temperature_celsius": [100.0, 100.0]}
                          }
        assert not box_furnace_mock.is_running()
```