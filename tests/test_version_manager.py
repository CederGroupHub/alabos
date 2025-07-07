"""
Tests for the version management system.
"""

import shutil
import tempfile
import unittest
from pathlib import Path

from alab_management.utils.version_manager import VersionManager


class TestVersionManager(unittest.TestCase):
    """Test the version management functionality."""

    def setUp(self):
        """Set up test environment."""
        # Create temporary directory
        self.test_dir = Path(tempfile.mkdtemp())
        self.backup_dir = self.test_dir / ".alab_backups"

        # Create test files
        self.tasks_dir = self.test_dir / "tasks"
        self.tasks_dir.mkdir()

        self.devices_dir = self.test_dir / "devices"
        self.devices_dir.mkdir()

        # Create test task file
        self.task_file = self.tasks_dir / "test_task.py"
        with open(self.task_file, "w") as f:
            f.write("class TestTask:\n    pass\n")

        # Create test device file
        self.device_file = self.devices_dir / "test_device.py"
        with open(self.device_file, "w") as f:
            f.write("class TestDevice:\n    pass\n")

        # Create test config
        self.config_file = self.test_dir / "config.toml"
        with open(self.config_file, "w") as f:
            f.write("[general]\nname = 'test'\n")

    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.test_dir)

    def test_version_manager_initialization(self):
        """Test version manager initialization."""
        # Mock the config to use our test directory
        original_config = VersionManager.__init__

        def mock_init(self):
            self.config = type(
                "Config",
                (),
                {
                    "get": lambda x, default=None: {
                        "general": {"working_dir": str(self.test_dir)},
                        "version_management": {"enabled": True, "keep_versions": 5},
                    }.get(x, default)
                },
            )()
            self.working_dir = self.test_dir
            self.backup_dir = self.backup_dir
            self.db_path = self.backup_dir / "version_tracking.db"
            self._current_version = None
            self._current_hash = None
            self._init_database()

        VersionManager.__init__ = mock_init

        try:
            VersionManager()
            self.assertTrue(self.backup_dir.exists())
            self.assertTrue(self.db_path.exists())
        finally:
            VersionManager.__init__ = original_config

    def test_file_hash_calculation(self):
        """Test file hash calculation."""
        vm = VersionManager()

        # Test file hash
        file_hash = vm._get_file_hash(self.task_file)
        self.assertIsInstance(file_hash, str)
        self.assertEqual(len(file_hash), 64)  # SHA256 hash length

        # Test directory hash
        dir_hash = vm._get_directory_hash(self.test_dir)
        self.assertIsInstance(dir_hash, str)
        self.assertEqual(len(dir_hash), 64)

    def test_version_recording(self):
        """Test version recording functionality."""

        # Mock the config
        def mock_get(self, key, default=None):
            if key == "version_management":
                return {"enabled": True, "keep_versions": 5}
            elif key == "general":
                return {"working_dir": str(self.test_dir)}
            return default

        vm = VersionManager()
        vm.config.get = mock_get.__get__(vm, VersionManager)
        vm.working_dir = self.test_dir
        vm.backup_dir = self.backup_dir
        vm.db_path = self.backup_dir / "version_tracking.db"
        vm._init_database()

        # Record first version
        hash1 = vm.record_task_completion("task1", "TestTask")
        self.assertIsNotNone(hash1)

        # Record second version (should be same if no changes)
        hash2 = vm.record_task_completion("task2", "TestTask")
        self.assertIsNone(hash2)  # No changes detected

        # Modify a file and record again
        with open(self.task_file, "w") as f:
            f.write("class TestTask:\n    def run(self):\n        pass\n")

        hash3 = vm.record_task_completion("task3", "TestTask")
        self.assertIsNotNone(hash3)
        self.assertNotEqual(hash1, hash3)

    def test_version_listing(self):
        """Test version listing functionality."""
        vm = VersionManager()
        vm.working_dir = self.test_dir
        vm.backup_dir = self.backup_dir
        vm.db_path = self.backup_dir / "version_tracking.db"
        vm._init_database()

        # Record a version
        vm.record_task_completion("task1", "TestTask")

        # List versions
        versions = vm.list_versions()
        self.assertEqual(len(versions), 1)
        self.assertEqual(versions[0]["task_id"], "task1")

    def test_version_restoration(self):
        """Test version restoration functionality."""
        vm = VersionManager()
        vm.working_dir = self.test_dir
        vm.backup_dir = self.backup_dir
        vm.db_path = self.backup_dir / "version_tracking.db"
        vm._init_database()

        # Record initial version
        initial_hash = vm.record_task_completion("task1", "TestTask")

        # Modify files
        with open(self.task_file, "w") as f:
            f.write("class TestTask:\n    def run(self):\n        pass\n")

        # Record modified version
        vm.record_task_completion("task2", "TestTask")

        # Restore to initial version
        success = vm.restore_version(initial_hash)
        self.assertTrue(success)

        # Verify restoration
        with open(self.task_file) as f:
            content = f.read()
        self.assertIn("class TestTask:", content)
        self.assertNotIn("def run(self):", content)

    def test_cleanup_functionality(self):
        """Test cleanup functionality."""
        vm = VersionManager()
        vm.working_dir = self.test_dir
        vm.backup_dir = self.backup_dir
        vm.db_path = self.backup_dir / "version_tracking.db"
        vm._init_database()

        # Record multiple versions
        for i in range(5):
            vm.record_task_completion(f"task{i}", "TestTask")

        # Clean up, keeping only 2 versions
        removed_count = vm.cleanup_old_versions(2)
        self.assertEqual(removed_count, 3)

        # Verify only 2 versions remain
        versions = vm.list_versions()
        self.assertEqual(len(versions), 2)


if __name__ == "__main__":
    unittest.main()
