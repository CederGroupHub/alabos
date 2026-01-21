import atexit
import signal
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


class VerificationTimeout(Exception):
    """Raised when a verification helper times out waiting for a condition."""

    pass


def cleanup_background_processes():
    """Clean up background processes in case of test failure."""
    try:
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
        subprocess.run("pkill -f 'alabos launch'", check=False, shell=True)
    except Exception:
        pass


def signal_handler(signum, frame):
    """Handle interrupt signals to ensure cleanup."""
    print(f"\nReceived signal {signum}, cleaning up...")
    cleanup_background_processes()
    exit(1)


# Register signal handlers and cleanup function
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)
atexit.register(cleanup_background_processes)


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
        try:
            # Kill processes more robustly
            if hasattr(self, "main_process") and self.main_process:
                self.main_process.terminate()
                try:
                    self.main_process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.main_process.kill()

            if hasattr(self, "worker_process") and self.worker_process:
                self.worker_process.terminate()
                try:
                    self.worker_process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.worker_process.kill()

            # Additional cleanup to ensure all processes are killed
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
            subprocess.run("pkill -f 'alabos launch'", check=False, shell=True)
            time.sleep(2)

            cleanup_lab(
                all_collections=True,
                _force_i_know_its_dangerous=True,
                sim_mode=True,
                database_name="Alab_sim",
                user_confirmation="y",
            )
        except Exception as e:
            print(f"Error during tearDown: {e}")
            # Force cleanup even if there's an error
            cleanup_background_processes()

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

    def _wait_for_experiment_completion(
        self, timeout: int = 120, expected_tasks: int = 3
    ) -> None:
        """Wait for the current experiment to complete."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            task_view = TaskView()
            all_tasks = list(task_view._task_collection.find())
            completed_tasks = [
                task for task in all_tasks if task.get("status") == "COMPLETED"
            ]
            if len(completed_tasks) == expected_tasks:
                return
            time.sleep(5)
        raise VerificationTimeout(
            f"Experiment did not complete within {timeout} seconds"
        )

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
                    return True  # Change detected

                time.sleep(5)
            except Exception:
                time.sleep(5)

        raise VerificationTimeout(
            f"Sample position {position_name} did not reach expected number {expected_number} within {timeout} seconds"
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
                    return True  # Device found

                time.sleep(5)
            except Exception:
                time.sleep(5)

        raise VerificationTimeout(
            f"Device {device_name} was not added within {timeout} seconds"
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
                    return True  # Device removed

                time.sleep(5)
            except Exception:
                time.sleep(5)

        raise VerificationTimeout(
            f"Device {device_name} was not removed within {timeout} seconds"
        )

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
                    return True  # Position found

                time.sleep(5)
            except Exception:
                time.sleep(5)

        raise VerificationTimeout(
            f"Sample position {position_name} was not added with expected number {expected_number} within {timeout} seconds"
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
                    return True  # Position removed

                time.sleep(5)
            except Exception:
                time.sleep(5)

        raise VerificationTimeout(
            f"Sample position {position_name} was not removed within {timeout} seconds"
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
                    return True  # Position found in device

                time.sleep(5)
            except Exception:
                time.sleep(5)

        raise VerificationTimeout(
            f"Device sample position {device_name}/{position_name} was not added with expected number {expected_number} within {timeout} seconds"
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
                    return True  # Position removed from device

                time.sleep(5)
            except Exception:
                time.sleep(5)

        raise VerificationTimeout(
            f"Device sample position {device_name}/{position_name} was not removed within {timeout} seconds"
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
                    return True  # Change detected

                time.sleep(5)
            except Exception:
                time.sleep(5)

        raise VerificationTimeout(
            f"Device sample position {device_name}/{position_name} did not reach expected number {expected_number} within {timeout} seconds"
        )

    def _wait_and_verify_task_addition(self, task_name: str, timeout: int = 60) -> None:
        """Wait for task addition and verify it's applied."""
        print(f"=== Starting _wait_and_verify_task_addition for {task_name} ===")
        start_time = time.time()
        iteration = 0
        while time.time() - start_time < timeout:
            iteration += 1
            elapsed = time.time() - start_time
            print(f"=== Iteration {iteration}, elapsed: {elapsed:.1f}s ===")
            try:
                # Check if the task exists from database
                from alab_management.task_view.task_view import TaskView

                task_view = TaskView()
                exists = task_view.task_type_exists_in_db(task_name)
                print(f"=== Task {task_name} exists in DB: {exists} ===")

                # Debug: Let's see what tasks are actually in the database
                all_tasks = task_view.get_all_tasks_from_db()
                print(f"=== All tasks in DB: {list(all_tasks.keys())} ===")

                if exists:
                    print(f"=== Task {task_name} found successfully! ===")
                    return True  # Task found

                print(f"=== Task {task_name} not found yet, sleeping 5s ===")
                time.sleep(5)
            except Exception as e:
                print(f"=== Exception in _wait_and_verify_task_addition: {e} ===")
                time.sleep(5)

        print(f"=== Timeout reached for task {task_name} ===")
        raise VerificationTimeout(
            f"Task {task_name} was not added within {timeout} seconds"
        )

    def _wait_and_verify_task_removal(self, task_name: str, timeout: int = 60) -> None:
        """Wait for task removal and verify it's applied."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                # Check if the task no longer exists from database
                from alab_management.task_view.task_view import TaskView

                task_view = TaskView()
                if not task_view.task_type_exists_in_db(task_name):
                    return True  # Task removed

                time.sleep(5)
            except Exception:
                time.sleep(5)

        raise VerificationTimeout(
            f"Task {task_name} was not removed within {timeout} seconds"
        )

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
            self._wait_for_experiment_completion(expected_tasks=3)

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
            self._wait_for_experiment_completion(expected_tasks=3)

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
            self._wait_for_experiment_completion(expected_tasks=3)

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
            self._wait_for_experiment_completion(expected_tasks=3)

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

    def test_6_adding_new_task(self):
        """Test 6: Adding a new task."""
        print("=== Starting test_6_adding_new_task ===")

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
        print("=== Original content loaded ===")

        try:
            print("=== Submitting test experiment ===")
            resp = self._submit_test_experiment()
            print(f"=== Response status: {resp.status_code} ===")
            self.assertEqual(resp.status_code, 200)
            print("=== Test experiment submitted successfully ===")
            time.sleep(5)  # Wait for tasks to start

            print("=== Waiting for experiment to complete ===")
            self._wait_for_experiment_completion(expected_tasks=3)
            print("=== Experiment completed ===")

            print("=== Creating new task file ===")
            new_task_file.write_text(new_task_content)
            print("=== New task file written ===")

            add_task_line = "add_task(TakePictureWithoutSpecifiedResult)"
            import_line = "from .tasks import ("
            new_import_line = "from .tasks import (\n    TestTask,"

            tasks_init_file = Path("tests/fake_lab/tasks/__init__.py")
            tasks_init_content = tasks_init_file.read_text()
            print("=== Read tasks/__init__.py ===")

            if "from .test_task import TestTask" not in tasks_init_content:
                tasks_init_content += "\nfrom .test_task import TestTask\n"
                tasks_init_file.write_text(tasks_init_content)
                print("=== Added import to tasks/__init__.py ===")

            modified_content = original_content.replace(
                import_line, new_import_line
            ).replace(add_task_line, f"{add_task_line}\nadd_task(TestTask)")
            init_file.write_text(modified_content)
            print("=== Modified __init__.py with new task ===")
            time.sleep(100)  # wait for refresh cycle
            print("=== Submitting experiment with new task ===")
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
            print(f"=== Response status for new experiment: {resp.status_code} ===")
            self.assertEqual(resp.status_code, 200)
            print("=== New task experiment submitted successfully ===")

            print("=== Waiting for refresh cycle and verifying task addition ===")
            self._wait_and_verify_task_addition("TestTask")
            print("=== Task addition verified ===")

            resp = requests.post(
                "http://127.0.0.1:8897/api/experiment/submit", json=new_experiment
            )
            print(f"=== Response status for new experiment: {resp.status_code} ===")
            self.assertEqual(resp.status_code, 200)
            print("=== New task experiment submitted successfully ===")

            print(
                "=== Submitting another test experiment to verify system is functional ==="
            )
            resp = self._submit_test_experiment()
            print(
                f"=== Response status for final test experiment: {resp.status_code} ==="
            )
            self.assertEqual(resp.status_code, 200)
            print("=== System functional after adding new task ===")

        finally:
            print("=== Cleaning up and restoring original files ===")
            init_file.write_text(original_content)
            if new_task_file.exists():
                new_task_file.unlink()

            tasks_init_file = Path("tests/fake_lab/tasks/__init__.py")
            if tasks_init_file.exists():
                tasks_init_content = tasks_init_file.read_text()
                tasks_init_content = tasks_init_content.replace(
                    "\nfrom .test_task import TestTask\n", ""
                )
                tasks_init_content = tasks_init_content.replace(
                    "from .test_task import TestTask\n", ""
                )
                tasks_init_file.write_text(tasks_init_content)
            print("=== Cleanup complete ===")

    def test_7_adding_removing_new_device_class(self):
        """Test 7: Adding and removing a new device class."""
        print("=== Starting test_7_adding_removing_new_device_class ===")

        # Create a new device file
        new_device_file = Path("tests/fake_lab/devices/scale.py")
        new_device_content = '''from typing import ClassVar

from alab_management.device_view import BaseDevice
from alab_management.sample_view import SamplePosition


class Scale(BaseDevice):
    """Fake scale device for auto refresh testing."""

    description: ClassVar[str] = "Fake scale device"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._is_running = False

    @property
    def sample_positions(self):
        return [
            SamplePosition(
                "weighing_platform",
                description="The platform where samples are placed for weighing",
                number=4,  # four samples can be weighed at the same time
            ),
        ]

    def emergent_stop(self):
        pass

    def run_program(self, *args, **kwargs):
        self._is_running = True

    def is_running(self):
        return self._is_running

    def get_weight(self):
        return 10.5

    def connect(self):
        pass

    def disconnect(self):
        pass
'''

        # Get the original fake_lab __init__.py content
        init_file = Path("tests/fake_lab/__init__.py")
        original_content = init_file.read_text()
        print("=== Original content loaded ===")

        try:
            print("=== Submitting test experiment ===")
            resp = self._submit_test_experiment()
            print(f"=== Response status: {resp.status_code} ===")
            self.assertEqual(resp.status_code, 200)
            print("=== Test experiment submitted successfully ===")
            time.sleep(5)  # Wait for tasks to start

            print("=== Waiting for experiment to complete ===")
            self._wait_for_experiment_completion(expected_tasks=3)
            print("=== Experiment completed ===")

            print("=== Creating new device file ===")
            new_device_file.write_text(new_device_content)
            print("=== New device file written ===")

            # Update the devices/__init__.py to include the new Scale device
            devices_init_file = Path("tests/fake_lab/devices/__init__.py")
            devices_init_content = devices_init_file.read_text()
            print("=== Read devices/__init__.py ===")

            if "from .scale import Scale" not in devices_init_content:
                # Add import for Scale device
                import_line = "from .robot_arm import RobotArm"
                new_import_line = (
                    "from .robot_arm import RobotArm\nfrom .scale import Scale"
                )
                devices_init_content = devices_init_content.replace(
                    import_line, new_import_line
                )

                # Add Scale to the __all__ list if it exists
                if "__all__" in devices_init_content:
                    all_line = "__all__ = ["
                    new_all_line = "__all__ = [\n    Scale,"
                    devices_init_content = devices_init_content.replace(
                        all_line, new_all_line
                    )

                devices_init_file.write_text(devices_init_content)
                print("=== Added Scale import to devices/__init__.py ===")

            # Add the Scale device to the main __init__.py
            # First, add Scale to the import statement
            import_line = "from .devices import ("
            new_import_line = "from .devices import (\n    Scale,"
            modified_content = original_content.replace(import_line, new_import_line)

            # Then add the device registration
            add_device_line = (
                'add_device(DeviceThatRunSlow(name="device_that_run_slow_2"))'
            )
            new_device_line = 'add_device(Scale(name="scale_1"))'

            modified_content = modified_content.replace(
                add_device_line,
                f"{add_device_line}\n{new_device_line}",
            )
            init_file.write_text(modified_content)
            print("=== Modified __init__.py with new Scale device ===")
            time.sleep(100)  # wait for refresh cycle
            # Wait for refresh cycle and verify device is added
            print(
                "=== Waiting for refresh cycle and verifying Scale device addition ==="
            )
            self._wait_and_verify_device_addition("scale_1")
            print("=== Scale device addition verified ===")

            # Verify the device sample position was also added
            print("=== Verifying Scale device sample position addition ===")
            self._wait_and_verify_device_sample_position_addition(
                "scale_1", "weighing_platform", 4
            )
            print("=== Scale device sample position addition verified ===")

            # Submit an experiment that uses the new Scale device
            print("=== Submitting experiment that uses the new Scale device ===")
            scale_experiment = {
                "name": "Scale device test experiment",
                "tags": [],
                "metadata": {},
                "samples": [{"name": "scale_test_sample", "tags": [], "metadata": {}}],
                "tasks": [
                    {
                        "type": "Starting",
                        "prev_tasks": [],
                        "parameters": {"dest": "furnace_temp"},
                        "samples": ["scale_test_sample"],
                    },
                    {
                        "type": "Moving",
                        "prev_tasks": [0],
                        "parameters": {"dest": "scale_1/weighing_platform"},
                        "samples": ["scale_test_sample"],
                    },
                    {
                        "type": "Ending",
                        "prev_tasks": [1],
                        "parameters": {},
                        "samples": ["scale_test_sample"],
                    },
                ],
            }
            resp = requests.post(
                "http://127.0.0.1:8897/api/experiment/submit", json=scale_experiment
            )
            print(f"=== Response status for Scale experiment: {resp.status_code} ===")
            self.assertEqual(resp.status_code, 200)
            print("=== Scale experiment submitted successfully ===")

            # Wait for the Scale experiment to complete
            print("=== Waiting for Scale experiment to complete ===")
            self._wait_for_experiment_completion(expected_tasks=6)
            print("=== Scale experiment completed ===")

            # Remove the device by restoring original content
            print("=== Removing Scale device by restoring original content ===")
            init_file.write_text(original_content)
            print("=== Original content restored ===")

            # Wait for refresh cycle and verify device is removed
            print(
                "=== Waiting for refresh cycle and verifying Scale device removal ==="
            )
            self._wait_and_verify_device_removal("scale_1")
            print("=== Scale device removal verified ===")

            # Verify the device sample position was also removed
            print("=== Verifying Scale device sample position removal ===")
            self._wait_and_verify_device_sample_position_removal(
                "scale_1", "weighing_platform"
            )
            print("=== Scale device sample position removal verified ===")

            # Verify the system is still functional
            print(
                "=== Submitting test experiment to verify system is still functional ==="
            )
            resp = self._submit_test_experiment()
            print(
                f"=== Response status for final test experiment: {resp.status_code} ==="
            )
            self.assertEqual(resp.status_code, 200)
            print("=== System functional after adding/removing new device class ===")

        finally:
            print("=== Cleaning up and restoring original files ===")

            # Delete the Scale device file
            if new_device_file.exists():
                new_device_file.unlink()
                print("=== Deleted scale.py file ===")

            # Restore devices/__init__.py
            devices_init_file = Path("tests/fake_lab/devices/__init__.py")
            if devices_init_file.exists():
                devices_init_content = devices_init_file.read_text()
                devices_init_content = devices_init_content.replace(
                    "\nfrom .scale import Scale", ""
                )
                devices_init_content = devices_init_content.replace(
                    "from .scale import Scale\n", ""
                )
                devices_init_content = devices_init_content.replace("\n    Scale,", "")
                devices_init_file.write_text(devices_init_content)
                print("=== Restored devices/__init__.py ===")

            # Restore main __init__.py - remove Scale from imports and device registration
            init_content = init_file.read_text()
            # Remove Scale from the import statement
            init_content = init_content.replace("\n    Scale,", "")
            # Remove the Scale device registration
            init_content = init_content.replace(
                '\nadd_device(Scale(name="scale_1"))', ""
            )
            init_file.write_text(init_content)
            print("=== Restored main __init__.py ===")

            print("=== Cleanup complete ===")


if __name__ == "__main__":
    unittest.main()
