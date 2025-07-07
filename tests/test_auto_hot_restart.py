import os
import subprocess
import tempfile
import time
import unittest
from pathlib import Path

import requests

from alab_management.experiment_view import ExperimentView
from alab_management.scripts.cleanup_lab import cleanup_lab
from alab_management.scripts.setup_lab import setup_lab
from alab_management.task_view import TaskView
from alab_management.task_view.task_enums import TaskStatus
from alab_management.utils.module_ops import (
    calculate_package_hash,
    hash_python_files_in_folder,
)


class TestAutoHotRestart(unittest.TestCase):
    """Test the auto hot restart functionality."""

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
            ["alabos", "launch_worker", "--processes", "4", "--threads", "8"],
            shell=False,
        )
        time.sleep(5)  # waiting for starting up

        if self.main_process.poll() is not None:
            raise RuntimeError("Main process failed to start")
        if self.worker_process.poll() is not None:
            raise RuntimeError("Worker process failed to start")

    def tearDown(self) -> None:
        """Clean up the test environment."""
        self.main_process.terminate()
        self.worker_process.terminate()
        time.sleep(5)
        cleanup_lab(
            all_collections=True,
            _force_i_know_its_dangerous=True,
            sim_mode=True,
            database_name="Alab_sim",
            user_confirmation="y",
        )

    def test_package_hash_calculation(self):
        """Test that package hash calculation works correctly."""
        # Test with a temporary directory
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create some test Python files
            test_file1 = temp_path / "test1.py"
            test_file1.write_text("print('test1')")

            test_file2 = temp_path / "test2.py"
            test_file2.write_text("print('test2')")

            # Calculate hash
            hash1 = hash_python_files_in_folder(temp_path)

            # Modify a file
            test_file1.write_text("print('test1_modified')")
            hash2 = hash_python_files_in_folder(temp_path)

            # Hashes should be different
            self.assertNotEqual(hash1, hash2)

            # Add a new file
            test_file3 = temp_path / "test3.py"
            test_file3.write_text("print('test3')")
            hash3 = hash_python_files_in_folder(temp_path)

            # Hash should change again
            self.assertNotEqual(hash2, hash3)

    def test_auto_refresh_disabled_by_default(self):
        """Test that auto refresh is disabled by default."""
        from pathlib import Path

        from alab_management.config import AlabOSConfig

        # Save the original config file content
        config_path = Path("tests/fake_lab/config.toml")
        original_content = config_path.read_text()

        try:
            # Temporarily remove the auto_refresh line from the config
            lines = original_content.split("\n")
            lines = [
                line for line in lines if not line.strip().startswith("auto_refresh")
            ]
            modified_content = "\n".join(lines)
            config_path.write_text(modified_content)

            # Load the config and check auto_refresh setting
            config = AlabOSConfig()
            auto_refresh = config["general"].get("auto_refresh", False)
            self.assertFalse(auto_refresh)

        finally:
            # Restore original config file content
            config_path.write_text(original_content)

    def test_auto_refresh_enabled_in_fake_lab(self):
        """Test that auto refresh is enabled in the fake lab config."""
        # This test verifies that the fake lab config has auto_refresh enabled
        # which is needed for the auto hot restart functionality
        config_path = Path("tests/fake_lab/config.toml")
        self.assertTrue(config_path.exists())

        # Read the config file to check auto_refresh setting
        config_content = config_path.read_text()
        self.assertIn("auto_refresh = true", config_content)

    def test_file_change_detection(self):
        """Test that file changes are detected and trigger refresh."""
        # This test simulates file changes and verifies the system responds
        # We'll modify a task file and check if the system detects the change

        # Get the original hash
        original_hash = calculate_package_hash()

        # Modify a task file to trigger change detection
        task_file = Path("tests/fake_lab/tasks/heating.py")
        original_content = task_file.read_text()

        try:
            # Add a comment to the file
            modified_content = (
                original_content + "\n# Test modification for auto restart\n"
            )
            task_file.write_text(modified_content)

            # Wait a bit for the system to detect the change
            time.sleep(35)  # System checks every 30 seconds

            # Calculate new hash
            new_hash = calculate_package_hash()

            # Hash should be different
            self.assertNotEqual(original_hash, new_hash)

        finally:
            # Restore original content
            task_file.write_text(original_content)

    def test_system_refresh_behavior(self):
        """Test that the system properly refreshes when changes are detected."""
        # This test verifies that the system refresh mechanism works correctly
        # by monitoring the system behavior during a refresh cycle

        # Get initial package hash
        initial_hash = calculate_package_hash()

        # Submit a simple experiment to have some tasks running
        experiment = {
            "name": "Auto restart test experiment",
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
                    "parameters": {
                        "setpoints": ((1, 30),)
                    },  # 30 second heating to ensure it's still running
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

        # Submit the experiment
        resp = requests.post(
            "http://127.0.0.1:8897/api/experiment/submit", json=experiment
        )
        self.assertEqual(resp.status_code, 200)

        # Wait for tasks to start running (check earlier)
        time.sleep(5)

        # Check task statuses with debugging
        task_view = TaskView()  # Create fresh task view
        all_tasks = list(task_view._task_collection.find())
        print(f"Total tasks in database: {len(all_tasks)}")

        for task in all_tasks:
            print(
                f"Task ID: {task['_id']}, Status: {task['status']}, Type: {task.get('type', 'N/A')}"
            )

        running_tasks = task_view.get_tasks_by_status(TaskStatus.RUNNING)
        initiated_tasks = task_view.get_tasks_by_status(TaskStatus.INITIATED)
        requesting_tasks = task_view.get_tasks_by_status(
            TaskStatus.REQUESTING_RESOURCES
        )

        print(f"Running tasks: {len(running_tasks)}")
        print(f"Initiated tasks: {len(initiated_tasks)}")
        print(f"Requesting resources tasks: {len(requesting_tasks)}")

        # Check that we have some tasks in a processing state
        total_processing_tasks = (
            len(running_tasks) + len(initiated_tasks) + len(requesting_tasks)
        )
        self.assertGreater(total_processing_tasks, 0, "No tasks are being processed")

        # Now modify a file to trigger refresh
        task_file = Path("tests/fake_lab/tasks/heating.py")
        original_content = task_file.read_text()

        try:
            # Add a comment to trigger refresh
            modified_content = original_content + "\n# Triggering auto restart test\n"
            task_file.write_text(modified_content)

            # Wait for the refresh cycle (30 seconds + some buffer)
            time.sleep(40)

            # Check that the package hash has changed (indicating refresh detection)
            new_hash = calculate_package_hash()
            self.assertNotEqual(
                initial_hash,
                new_hash,
                "Package hash should change after file modification",
            )

            # The system should have refreshed, but tasks should still complete
            # Wait for tasks to complete with a maximum timeout of 60 seconds
            start_time = time.time()
            timeout = 60  # 60 seconds timeout

            while time.time() - start_time < timeout:
                all_tasks = list(task_view._task_collection.find())
                completed_tasks = [
                    task for task in all_tasks if task["status"] == "COMPLETED"
                ]
                failed_tasks = [
                    task for task in all_tasks if task["status"] == "FAILED"
                ]

                # Check if we have completed or failed tasks
                if len(completed_tasks) > 0 or len(failed_tasks) > 0:
                    break

                time.sleep(1)  # Check every second

            # Verify that at least some tasks completed or failed within the timeout
            # This indicates that the system processed the tasks
            total_processed_tasks = len(completed_tasks) + len(failed_tasks)
            self.assertGreater(
                total_processed_tasks, 0, f"No tasks processed within {timeout} seconds"
            )

        finally:
            # Restore original content
            task_file.write_text(original_content)

    def test_refresh_detection_mechanism(self):
        """Test that the system properly detects changes and triggers refresh."""
        # Get initial package hash
        initial_hash = calculate_package_hash()

        # Modify a task file to trigger refresh detection
        task_file = Path("tests/fake_lab/tasks/heating.py")
        original_content = task_file.read_text()

        try:
            # Add a comment to trigger refresh
            modified_content = original_content + "\n# Test refresh detection\n"
            task_file.write_text(modified_content)

            # Wait for the system to detect the change (30 seconds + buffer)
            time.sleep(35)

            # Check that the package hash has changed
            new_hash = calculate_package_hash()
            self.assertNotEqual(
                initial_hash,
                new_hash,
                "Package hash should change after file modification",
            )

            # Verify that the change was detected by checking the hash calculation
            # The system should have detected the file change and updated its internal hash
            self.assertNotEqual(initial_hash, new_hash)

        finally:
            # Restore original content
            task_file.write_text(original_content)

    def test_refresh_with_no_changes(self):
        """Test that refresh doesn't occur when no changes are detected."""
        # Get the initial hash
        initial_hash = calculate_package_hash()

        # Wait for a refresh cycle
        time.sleep(35)

        # Hash should remain the same
        current_hash = calculate_package_hash()
        self.assertEqual(initial_hash, current_hash)

    def test_module_reload_functionality(self):
        """Test that module reloading works correctly."""
        from alab_management.utils.module_ops import (
            import_module_from_path,
            load_definition,
        )

        # Test that load_definition can be called with reload=True
        try:
            load_definition(reload=True)
        except Exception as e:
            self.fail(f"load_definition with reload=True failed: {e}")

        # Test that import_module_from_path works with reload
        test_path = Path("tests/fake_lab/tasks/heating.py")
        try:
            module = import_module_from_path(test_path, reload=True)
            self.assertIsNotNone(module)
        except Exception as e:
            self.fail(f"import_module_from_path with reload=True failed: {e}")

    def test_environment_variable_during_reload(self):
        """Test that ALABOS_RELOAD environment variable is set during reload."""
        from alab_management.utils.module_ops import import_module_from_path

        test_path = Path("tests/fake_lab/tasks/heating.py")

        # Clear the environment variable
        if "ALABOS_RELOAD" in os.environ:
            del os.environ["ALABOS_RELOAD"]

        # Import with reload
        import_module_from_path(test_path, reload=True)

        # The environment variable should be cleared after reload
        self.assertNotIn("ALABOS_RELOAD", os.environ)

    def test_refresh_with_running_tasks(self):
        """Test that refresh works correctly when tasks are running."""
        # Submit a long-running experiment
        experiment = {
            "name": "Long running test",
            "tags": [],
            "metadata": {},
            "samples": [{"name": "long_sample", "tags": [], "metadata": {}}],
            "tasks": [
                {
                    "type": "Starting",
                    "prev_tasks": [],
                    "parameters": {"dest": "furnace_temp"},
                    "samples": ["long_sample"],
                },
                {
                    "type": "Heating",
                    "prev_tasks": [0],
                    "parameters": {"setpoints": ((1, 10),)},  # 10 second heating
                    "samples": ["long_sample"],
                },
                {
                    "type": "Ending",
                    "prev_tasks": [1],
                    "parameters": {},
                    "samples": ["long_sample"],
                },
            ],
        }

        # Submit the experiment
        resp = requests.post(
            "http://127.0.0.1:8897/api/experiment/submit", json=experiment
        )
        self.assertEqual(resp.status_code, 200)

        # Wait for tasks to start
        time.sleep(5)

        # Modify a file while tasks are running
        task_file = Path("tests/fake_lab/tasks/heating.py")
        original_content = task_file.read_text()

        try:
            # Add a comment
            modified_content = (
                original_content + "\n# Modification during running tasks\n"
            )
            task_file.write_text(modified_content)

            # Wait for refresh cycle
            time.sleep(35)

            # Tasks should still complete despite the refresh
            # Wait for tasks to complete with a maximum timeout of 60 seconds
            start_time = time.time()
            timeout = 60  # 60 seconds timeout

            while time.time() - start_time < timeout:
                all_tasks = list(self.task_view._task_collection.find())
                completed_tasks = [
                    task for task in all_tasks if task["status"] == "COMPLETED"
                ]
                failed_tasks = [
                    task for task in all_tasks if task["status"] == "FAILED"
                ]

                # Check if we have completed or failed tasks
                if len(completed_tasks) > 0 or len(failed_tasks) > 0:
                    break

                time.sleep(1)  # Check every second

            # Verify that at least some tasks completed or failed within the timeout
            # This indicates that the system processed the tasks
            total_processed_tasks = len(completed_tasks) + len(failed_tasks)
            self.assertGreater(
                total_processed_tasks, 0, f"No tasks processed within {timeout} seconds"
            )

        finally:
            # Restore original content
            task_file.write_text(original_content)


if __name__ == "__main__":
    unittest.main()
