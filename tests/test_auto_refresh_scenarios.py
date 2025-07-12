import subprocess
import time
import unittest
from pathlib import Path
from typing import Any

import requests

from alab_management.experiment_view import ExperimentView
from alab_management.scripts.cleanup_lab import cleanup_lab
from alab_management.scripts.setup_lab import setup_lab
from alab_management.task_view import TaskView


class TestAutoRefreshScenarios(unittest.TestCase):
    """Test auto refresh functionality for various scenarios."""

    def setUp(self) -> None:
        """Set up the test environment."""
        time.sleep(0.5)
        cleanup_lab(
            all_collections=True,
            _force_i_know_its_dangerous=True,
            sim_mode=True,
            database_name="Alab_sim",
            user_confirmation="y",
        )
        setup_lab()
        self.task_view = TaskView()
        self.experiment_view = ExperimentView()

        # Start the lab and worker processes
        self.main_process = subprocess.Popen(
            ["alabos", "launch", "--port", "8897"], shell=False
        )
        self.worker_process = subprocess.Popen(
            ["alabos", "launch_worker", "--processes", "4", "--threads", "128"],
            shell=False,
        )
        time.sleep(5)  # waiting for starting up

        if self.main_process.poll() is not None:
            raise RuntimeError("Main process failed to start")
        if self.worker_process.poll() is not None:
            raise RuntimeError("Worker process failed to start")

    def tearDown(self) -> None:
        """Clean up the test environment."""
        # Kill processes more robustly
        self.main_process.terminate()
        self.worker_process.terminate()
        subprocess.run(
            "lsof -ti :8897 | xargs kill -9 2>/dev/null || true",
            check=False,
            shell=True,
        )
        subprocess.run(
            "ps aux | grep 'dramatiq' | grep 'alab_management.task_actor' | awk '{print $2}' | xargs -r kill",
            check=False,
            shell=True,
        )
        subprocess.run("pkill -f 'alabos launch_worker'", check=False, shell=True)
        time.sleep(5)
        cleanup_lab(
            all_collections=True,
            _force_i_know_its_dangerous=True,
            sim_mode=True,
            database_name="Alab_sim",
            user_confirmation="y",
        )

    def _submit_test_experiment(self) -> dict[str, Any]:
        """Submit a test experiment and return the response."""
        experiment = {
            "name": "Auto refresh test experiment",
            "tags": [],
            "metadata": {},
            "samples": [{"name": "test_sample", "tags": [], "metadata": {}}],
            "tasks": [
                {
                    "type": "Starting",
                    "prev_tasks": [],
                    "parameters": {"dest": "furnace_temp"},
                    "samples": ["test_sample"],
                },
                {
                    "type": "Heating",
                    "prev_tasks": [0],
                    "parameters": {"setpoints": ((1, 5),)},  # 30 second heating
                    "samples": ["test_sample"],
                },
                {
                    "type": "Ending",
                    "prev_tasks": [1],
                    "parameters": {},
                    "samples": ["test_sample"],
                },
            ],
        }

        resp = requests.post(
            "http://127.0.0.1:8897/api/experiment/submit", json=experiment
        )
        return resp

    def wait_for_refresh_cycle(self, timeout: int = 35) -> None:
        """Wait for the refresh cycle to complete (system checks every 20 seconds)."""
        time.sleep(timeout)

    def _wait_for_experiment_completion(self, timeout: int = 120) -> None:
        """Wait for the current experiment to complete."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            task_view = TaskView()
            all_tasks = list(task_view._task_collection.find())
            completed_tasks = [
                task for task in all_tasks if task.get("status") == "COMPLETED"
            ]
            if len(completed_tasks) == 3:
                return
            time.sleep(5)
        raise TimeoutError(f"Experiment did not complete within {timeout} seconds")

    def _wait_and_verify_sample_position_change(
        self, position_name: str, expected_number: int, timeout: int = 120
    ) -> None:
        """Wait for sample position change and verify it's applied."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                # Check if the sample position has the expected number from database
                from alab_management.sample_view.sample_view import SampleView

                sample_view = SampleView()
                max_number = sample_view.get_sample_position_max_number_by_prefix(
                    position_name
                )
                print(
                    f"Sample position {position_name} max number from DB: {max_number}"
                )

                if max_number == expected_number:
                    print(
                        f"Sample position {position_name} number change to {expected_number} detected"
                    )
                    return  # Change detected

                time.sleep(5)
            except Exception:
                time.sleep(5)

        self.fail(
            f"Sample position {position_name} number change to {expected_number} not detected within {timeout} seconds"
        )

    def _wait_and_verify_device_addition(
        self, device_name: str, timeout: int = 60
    ) -> None:
        """Wait for device addition and verify it's applied."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                # Check if the device exists from database
                from alab_management.device_view.device_view import DeviceView

                device_view = DeviceView()
                if device_view.device_exists_in_db(device_name):
                    return  # Device found

                time.sleep(5)
            except Exception:
                time.sleep(5)

        self.fail(
            f"Device {device_name} addition not detected within {timeout} seconds"
        )

    def _wait_and_verify_device_removal(
        self, device_name: str, timeout: int = 60
    ) -> None:
        """Wait for device removal and verify it's applied."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                # Check if the device no longer exists from database
                from alab_management.device_view.device_view import DeviceView

                device_view = DeviceView()
                if not device_view.device_exists_in_db(device_name):
                    return  # Device removed

                time.sleep(5)
            except Exception:
                time.sleep(5)

        self.fail(f"Device {device_name} removal not detected within {timeout} seconds")

    def _wait_and_verify_sample_position_addition(
        self, position_name: str, expected_number: int, timeout: int = 60
    ) -> None:
        """Wait for sample position addition and verify it's applied."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                # Check if the sample position exists from database
                from alab_management.sample_view.sample_view import SampleView

                sample_view = SampleView()
                max_number = sample_view.get_sample_position_max_number_by_prefix(
                    position_name
                )

                if max_number == expected_number:
                    return  # Position found

                time.sleep(5)
            except Exception:
                time.sleep(5)

        self.fail(
            f"Sample position {position_name} addition not detected within {timeout} seconds"
        )

    def _wait_and_verify_sample_position_removal(
        self, position_name: str, timeout: int = 60
    ) -> None:
        """Wait for sample position removal and verify it's applied."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                # Check if the sample position no longer exists from database
                from alab_management.sample_view.sample_view import SampleView

                sample_view = SampleView()
                all_positions = sample_view.get_all_sample_positions_from_db()

                position_found = False
                for position_name_db in all_positions:
                    if position_name_db.startswith(position_name):
                        position_found = True
                        break

                if not position_found:
                    return  # Position removed

                time.sleep(5)
            except Exception:
                time.sleep(5)

        self.fail(
            f"Sample position {position_name} removal not detected within {timeout} seconds"
        )

    # TODO: wrong way to search for device sample position.
    # Search for sample position of the new device sample position alongside the parent device name.
    def _wait_and_verify_device_sample_position_addition(
        self,
        device_name: str,
        position_name: str,
        expected_number: int,
        timeout: int = 60,
    ) -> None:
        """Wait for device sample position addition and verify it's applied."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                # Check if the device has the new sample position from database
                from alab_management.sample_view.sample_view import SampleView

                sample_view = SampleView()
                device_position_prefix = f"{device_name}/{position_name}"
                max_number = sample_view.get_sample_position_max_number_by_prefix(
                    device_position_prefix
                )

                if max_number == expected_number:
                    return  # Position found in device

                time.sleep(5)
            except Exception:
                time.sleep(5)

        self.fail(
            f"Device {device_name} sample position {position_name} addition not detected within {timeout} seconds"
        )

    # TODO: wrong way to search for device sample position.
    def _wait_and_verify_device_sample_position_removal(
        self, device_name: str, position_name: str, timeout: int = 60
    ) -> None:
        """Wait for device sample position removal and verify it's applied."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                # Check if the device no longer has the sample position from database
                from alab_management.sample_view.sample_view import SampleView

                sample_view = SampleView()
                device_position_prefix = f"{device_name}/{position_name}"
                all_positions = sample_view.get_all_sample_positions_from_db()

                position_found = False
                for position_name_db in all_positions:
                    if position_name_db.startswith(device_position_prefix):
                        position_found = True
                        break

                if not position_found:
                    return  # Position removed from device

                time.sleep(5)
            except Exception:
                time.sleep(5)

        self.fail(
            f"Device {device_name} sample position {position_name} removal not detected within {timeout} seconds"
        )

    # TODO: wrong way to search for device sample position.
    # Search for sample position of the new device sample position alongside the parent device name.
    def _wait_and_verify_device_sample_position_change(
        self,
        device_name: str,
        position_name: str,
        expected_number: int,
        timeout: int = 60,
    ) -> None:
        """Wait for device sample position number change and verify it's applied."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                # Check if the device sample position has the expected number from database
                from alab_management.sample_view.sample_view import SampleView

                sample_view = SampleView()
                device_position_prefix = f"{device_name}/{position_name}"
                max_number = sample_view.get_sample_position_max_number_by_prefix(
                    device_position_prefix
                )

                if max_number == expected_number:
                    return  # Change detected

                time.sleep(5)
            except Exception:
                time.sleep(5)

        self.fail(
            f"Device {device_name} sample position {position_name} number change to {expected_number} not detected within {timeout} seconds"
        )

    def _wait_and_verify_task_addition(self, task_name: str, timeout: int = 60) -> None:
        """Wait for task addition and verify it's applied."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                # Check if the task exists from database
                from alab_management.task_view.task_view import TaskView

                task_view = TaskView()
                if task_view.task_type_exists_in_db(task_name):
                    return  # Task found

                time.sleep(5)
            except Exception:
                time.sleep(5)

        self.fail(f"Task {task_name} addition not detected within {timeout} seconds")

    def _wait_and_verify_task_removal(self, task_name: str, timeout: int = 60) -> None:
        """Wait for task removal and verify it's applied."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                # Check if the task no longer exists from database
                from alab_management.task_view.task_view import TaskView

                task_view = TaskView()
                if not task_view.task_type_exists_in_db(task_name):
                    return  # Task removed

                time.sleep(5)
            except Exception:
                time.sleep(5)

        self.fail(f"Task {task_name} removal not detected within {timeout} seconds")

    def test_1_adding_removing_slots_standalone_sample_position(self):
        """Test 1: Adding and removing slots on a standalone sample position/changing the numbers."""
        # Get the original fake_lab __init__.py content
        init_file = Path("tests/fake_lab/__init__.py")
        original_content = init_file.read_text()

        try:
            # Submit an experiment to have tasks running
            resp = self._submit_test_experiment()
            self.assertEqual(resp.status_code, 200)
            time.sleep(5)  # Wait for tasks to start

            # Modify the standalone sample position - change number from 64 to 32
            modified_content = original_content.replace("number=64,", "number=32,")
            init_file.write_text(modified_content)

            # Wait for refresh cycle and verify change is applied
            self._wait_and_verify_sample_position_change("furnace_temp", 32)

            # Change back to original
            modified_content = original_content.replace("number=32,", "number=64,")
            init_file.write_text(modified_content)

            # Wait for refresh cycle and verify change is applied
            self._wait_and_verify_sample_position_change("furnace_temp", 64)

        finally:
            # Restore original content
            init_file.write_text(original_content)

    def test_2_adding_removing_device_and_sample_position(self):
        """Test 2: Adding and removing a device and its sample position."""
        # Get the original fake_lab __init__.py content
        init_file = Path("tests/fake_lab/__init__.py")
        original_content = init_file.read_text()

        try:
            # Submit an experiment to have tasks running
            resp = self._submit_test_experiment()
            self.assertEqual(resp.status_code, 200)
            time.sleep(5)  # Wait for tasks to start

            # Wait for experiment to complete
            self._wait_for_experiment_completion()

            # Add a new device (furnace_17) to the configuration
            add_device_line = 'add_device(Furnace(name="furnace_16"))'

            modified_content = original_content.replace(
                add_device_line,
                f'{add_device_line}\nadd_device(Furnace(name="furnace_17"))',
            )
            init_file.write_text(modified_content)

            # Wait for refresh cycle and verify device is added
            self._wait_and_verify_device_addition("furnace_17")

            # Remove the device by restoring original content
            init_file.write_text(original_content)

            # Wait for refresh cycle and verify device is removed
            self._wait_and_verify_device_removal("furnace_17")

            # Verify the system is still functional
            resp = self._submit_test_experiment()
            self.assertEqual(resp.status_code, 200)

        finally:
            # Restore original content
            init_file.write_text(original_content)

    def test_3_adding_removing_whole_sample_position(self):
        """Test 3: Adding and removing whole sample position."""
        # Get the original fake_lab __init__.py content
        init_file = Path("tests/fake_lab/__init__.py")
        original_content = init_file.read_text()

        try:
            # Submit an experiment to have tasks running
            resp = self._submit_test_experiment()
            self.assertEqual(resp.status_code, 200)
            time.sleep(5)  # Wait for tasks to start

            # Wait for experiment to complete
            self._wait_for_experiment_completion()

            # Add a new standalone sample position
            new_sample_position = """
add_standalone_sample_position(
    SamplePosition(
        "test_position",
        number=16,
        description="Test position for auto refresh",
    )
)
"""
            # Find the last add_standalone_sample_position and add after it
            lines = original_content.split("\n")
            last_sample_pos_idx = -1
            for i, line in enumerate(lines):
                if "add_standalone_sample_position" in line:
                    last_sample_pos_idx = i

            if last_sample_pos_idx != -1:
                # Find the end of the last sample position block
                end_idx = last_sample_pos_idx
                brace_count = 0
                for i in range(last_sample_pos_idx, len(lines)):
                    if "(" in lines[i]:
                        brace_count += lines[i].count("(")
                    if ")" in lines[i]:
                        brace_count -= lines[i].count(")")
                    if brace_count == 0:
                        end_idx = i
                        break

                # Insert new sample position after the last one
                lines.insert(end_idx + 1, new_sample_position)
                modified_content = "\n".join(lines)
                init_file.write_text(modified_content)

                # Wait for refresh cycle and verify sample position is added
                self._wait_and_verify_sample_position_addition("test_position", 16)

                # Remove the sample position by restoring original content
                init_file.write_text(original_content)

                # Wait for refresh cycle and verify sample position is removed
                self._wait_and_verify_sample_position_removal("test_position")

                # Verify the system is still functional
                resp = self._submit_test_experiment()
                self.assertEqual(resp.status_code, 200)

        finally:
            # Restore original content
            init_file.write_text(original_content)

    def test_4_adding_removing_sample_position_prefix_in_device(self):
        """Test 4: Adding and removing a sample position prefix in a device."""
        # Get the original furnace device content
        furnace_file = Path("tests/fake_lab/devices/furnace.py")
        original_content = furnace_file.read_text()

        try:
            # Submit an experiment to have tasks running
            resp = self._submit_test_experiment()
            self.assertEqual(resp.status_code, 200)
            time.sleep(5)  # Wait for tasks to start

            # Wait for experiment to complete
            self._wait_for_experiment_completion()

            # Add a new sample position to the furnace device
            new_position = """
            SamplePosition(
                "test_prefix",
                description="Test position prefix in furnace",
                number=2,
            ),"""

            # Find the sample_positions property and add the new position
            lines = original_content.split("\n")
            sample_positions_start = -1
            for i, line in enumerate(lines):
                if "def sample_positions(self):" in line:
                    sample_positions_start = i
                    break

            if sample_positions_start != -1:
                # Find the return statement
                return_idx = -1
                for i in range(sample_positions_start, len(lines)):
                    if "return [" in lines[i]:
                        return_idx = i
                        break

                if return_idx != -1:
                    # Add the new position before the closing bracket
                    lines.insert(return_idx + 1, new_position)
                    modified_content = "\n".join(lines)
                    furnace_file.write_text(modified_content)

                    # Wait for refresh cycle and verify device sample position is added
                    self._wait_and_verify_device_sample_position_addition(
                        "furnace_1", "test_prefix", 2
                    )

                    # Remove the position by restoring original content
                    furnace_file.write_text(original_content)

                    # Wait for refresh cycle and verify device sample position is removed
                    self._wait_and_verify_device_sample_position_removal(
                        "furnace_1", "test_prefix"
                    )

                    # Verify the system is still functional
                    resp = self._submit_test_experiment()
                    self.assertEqual(resp.status_code, 200)

        finally:
            # Restore original content
            furnace_file.write_text(original_content)

    def test_5_changing_numbers_in_sample_position_in_device(self):
        """Test 5: Changing the numbers in a sample position in a device."""
        # Get the original furnace device content
        furnace_file = Path("tests/fake_lab/devices/furnace.py")
        original_content = furnace_file.read_text()

        try:
            # Submit an experiment to have tasks running
            resp = self._submit_test_experiment()
            self.assertEqual(resp.status_code, 200)
            time.sleep(5)  # Wait for tasks to start

            # Wait for experiment to complete
            self._wait_for_experiment_completion()

            # Change the number of samples in the "inside" position from 8 to 4
            modified_content = original_content.replace(
                "number=8,  # eight samples can be heated at the same time",
                "number=4,  # four samples can be heated at the same time",
            )
            furnace_file.write_text(modified_content)

            # Wait for refresh cycle and verify device sample position number change
            self._wait_and_verify_device_sample_position_change(
                "furnace_1", "inside", 4
            )

            # Change back to original
            modified_content = original_content.replace(
                "number=4,  # four samples can be heated at the same time",
                "number=8,  # eight samples can be heated at the same time",
            )
            furnace_file.write_text(modified_content)

            # Wait for refresh cycle and verify device sample position number change
            self._wait_and_verify_device_sample_position_change(
                "furnace_1", "inside", 8
            )

            # Verify the system is still functional
            resp = self._submit_test_experiment()
            self.assertEqual(resp.status_code, 200)

        finally:
            # Restore original content
            furnace_file.write_text(original_content)

    def test_7_adding_new_task(self):
        """Test 7: Adding a new task."""
        # Create a new task file
        new_task_file = Path("tests/fake_lab/tasks/test_task.py")
        new_task_content = '''import time

from alab_management.task_view import BaseTask


class TestTask(BaseTask):
    """Test task for auto refresh."""

    def __init__(self, samples, *args, **kwargs):
        """Test task.

        Args:
            samples: List of sample names or ids.
        """
        super().__init__(samples=samples, *args, **kwargs)

    def run(self):
        """Run the test task."""
        # Import Furnace locally to avoid circular import
        from .. import Furnace

        with self.lab_view.request_resources({Furnace: {"inside": 1}}) as (
            inner_devices,
            sample_positions,
        ):
            # Just wait for a short time to simulate work
            time.sleep(2)
        return self.task_id
'''

        # Get the original fake_lab __init__.py content
        init_file = Path("tests/fake_lab/__init__.py")
        original_content = init_file.read_text()

        try:
            # Submit an experiment to have tasks running
            resp = self._submit_test_experiment()
            self.assertEqual(resp.status_code, 200)
            time.sleep(5)  # Wait for tasks to start

            # Wait for experiment to complete
            self._wait_for_experiment_completion()

            # Create the new task file
            new_task_file.write_text(new_task_content)

            # Add the task to the __init__.py file
            add_task_line = "add_task(TakePictureWithoutSpecifiedResult)"

            # Add import for the new task
            import_line = "from .tasks import ("
            new_import_line = "from .tasks import (\n    TestTask,"

            # Also add the import to the tasks __init__.py file
            tasks_init_file = Path("tests/fake_lab/tasks/__init__.py")
            tasks_init_content = tasks_init_file.read_text()

            # Add the import if it doesn't already exist
            if "from .test_task import TestTask" not in tasks_init_content:
                tasks_init_content += "\nfrom .test_task import TestTask\n"
                tasks_init_file.write_text(tasks_init_content)

            modified_content = original_content.replace(
                import_line, new_import_line
            ).replace(add_task_line, f"{add_task_line}\nadd_task(TestTask)")
            init_file.write_text(modified_content)

            # Wait for refresh cycle and verify task is added
            self._wait_and_verify_task_addition("TestTask")

            # Test that the new task can be used in an experiment
            new_experiment = {
                "name": "Test new task experiment",
                "tags": [],
                "metadata": {},
                "samples": [{"name": "test_sample_2", "tags": [], "metadata": {}}],
                "tasks": [
                    {
                        "type": "Starting",
                        "prev_tasks": [],
                        "parameters": {"dest": "furnace_temp"},
                        "samples": ["test_sample_2"],
                    },
                    {
                        "type": "TestTask",
                        "prev_tasks": [0],
                        "parameters": {},
                        "samples": ["test_sample_2"],
                    },
                    {
                        "type": "Ending",
                        "prev_tasks": [1],
                        "parameters": {},
                        "samples": ["test_sample_2"],
                    },
                ],
            }

            resp = requests.post(
                "http://127.0.0.1:8897/api/experiment/submit", json=new_experiment
            )
            self.assertEqual(resp.status_code, 200)

            # Remove the task by restoring original content and deleting the file
            init_file.write_text(original_content)
            if new_task_file.exists():
                new_task_file.unlink()

            # Also remove the import from tasks __init__.py
            tasks_init_file = Path("tests/fake_lab/tasks/__init__.py")
            if tasks_init_file.exists():
                tasks_init_content = tasks_init_file.read_text()
                # Remove the TestTask import
                tasks_init_content = tasks_init_content.replace(
                    "\nfrom .test_task import TestTask\n", ""
                )
                tasks_init_content = tasks_init_content.replace(
                    "from .test_task import TestTask\n", ""
                )
                tasks_init_file.write_text(tasks_init_content)

            # Wait for refresh cycle and verify task is removed
            self._wait_and_verify_task_removal("TestTask")

            # Verify the system is still functional
            resp = self._submit_test_experiment()
            self.assertEqual(resp.status_code, 200)

        finally:
            # Restore original content and clean up
            init_file.write_text(original_content)
            if new_task_file.exists():
                new_task_file.unlink()

            # Also remove the import from tasks __init__.py in cleanup
            tasks_init_file = Path("tests/fake_lab/tasks/__init__.py")
            if tasks_init_file.exists():
                tasks_init_content = tasks_init_file.read_text()
                # Remove the TestTask import
                tasks_init_content = tasks_init_content.replace(
                    "\nfrom .test_task import TestTask\n", ""
                )
                tasks_init_content = tasks_init_content.replace(
                    "from .test_task import TestTask\n", ""
                )
                tasks_init_file.write_text(tasks_init_content)


if __name__ == "__main__":
    unittest.main()
