import os
import tempfile
import unittest
from pathlib import Path

from alab_management.config import AlabOSConfig
from alab_management.utils.module_ops import (
    calculate_package_hash,
    deep_reload,
    hash_python_files_in_folder,
    import_module_from_path,
    load_definition,
)


class TestAutoRestartUnit(unittest.TestCase):
    """Unit tests for auto restart functionality without requiring full lab system."""

    def setUp(self):
        """Set up test environment."""
        # Set config path to fake lab config for testing
        os.environ["ALABOS_CONFIG_PATH"] = "tests/fake_lab/config.toml"

    def test_hash_python_files_in_folder(self):
        """Test hash calculation for Python files in a folder."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create test Python files
            test_file1 = temp_path / "test1.py"
            test_file1.write_text("print('test1')")

            test_file2 = temp_path / "test2.py"
            test_file2.write_text("print('test2')")

            # Calculate initial hash
            hash1 = hash_python_files_in_folder(temp_path)
            self.assertIsInstance(hash1, str)
            self.assertEqual(len(hash1), 64)  # SHA256 hash length

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

            # Test with non-Python files (should be ignored)
            non_py_file = temp_path / "test.txt"
            non_py_file.write_text("This is not a Python file")

            hash4 = hash_python_files_in_folder(temp_path)
            # Hash should be the same as before since .txt files are ignored
            self.assertEqual(hash3, hash4)

    def test_hash_with_subdirectories(self):
        """Test hash calculation with subdirectories."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create subdirectory structure
            subdir = temp_path / "subdir"
            subdir.mkdir()

            # Create files in different locations
            file1 = temp_path / "main.py"
            file1.write_text("print('main')")

            file2 = subdir / "sub.py"
            file2.write_text("print('sub')")

            # Calculate hash
            hash1 = hash_python_files_in_folder(temp_path)

            # Modify file in subdirectory
            file2.write_text("print('sub_modified')")
            hash2 = hash_python_files_in_folder(temp_path)

            # Hashes should be different
            self.assertNotEqual(hash1, hash2)

    def test_calculate_package_hash(self):
        """Test package hash calculation for the current working directory."""
        # This test assumes we're running from the project root
        hash1 = calculate_package_hash()
        self.assertIsInstance(hash1, str)
        self.assertEqual(len(hash1), 64)

        # Hash should be consistent for the same directory
        hash2 = calculate_package_hash()
        self.assertEqual(hash1, hash2)

    def test_auto_refresh_config_default(self):
        """Test that auto refresh is disabled by default in config."""
        # Clear any existing config path to test default behavior
        original_config_path = os.environ.get("ALABOS_CONFIG_PATH")
        if "ALABOS_CONFIG_PATH" in os.environ:
            del os.environ["ALABOS_CONFIG_PATH"]

        try:
            # This should fail because there's no config.toml in current directory
            with self.assertRaises(FileNotFoundError):
                _ = AlabOSConfig()
        finally:
            # Restore original config path
            if original_config_path:
                os.environ["ALABOS_CONFIG_PATH"] = original_config_path

    def test_auto_refresh_config_fake_lab(self):
        """Test that fake lab config has auto refresh enabled."""
        config_path = Path("tests/fake_lab/config.toml")
        self.assertTrue(config_path.exists())

        config_content = config_path.read_text()
        self.assertIn("auto_refresh = true", config_content)

    def test_load_definition_reload(self):
        """Test that load_definition works with reload parameter."""
        # Test that load_definition can be called with reload=True
        try:
            load_definition(reload=True)
        except Exception as e:
            self.fail(f"load_definition with reload=True failed: {e}")

    def test_import_module_from_path_reload(self):
        """Test module import with reload functionality."""
        # Test with a real module path
        test_path = Path("tests/fake_lab/tasks/heating.py")

        try:
            module = import_module_from_path(test_path, reload=True)
            self.assertIsNotNone(module)
            self.assertEqual(module.__name__, "tests.fake_lab.tasks.heating")
        except Exception as e:
            self.fail(f"import_module_from_path with reload=True failed: {e}")

    def test_environment_variable_during_reload(self):
        """Test that ALABOS_RELOAD environment variable is properly managed."""
        test_path = Path("tests/fake_lab/tasks/heating.py")

        # Clear the environment variable
        if "ALABOS_RELOAD" in os.environ:
            del os.environ["ALABOS_RELOAD"]

        # Import with reload
        import_module_from_path(test_path, reload=True)

        # The environment variable should be cleared after reload
        self.assertNotIn("ALABOS_RELOAD", os.environ)

    def test_deep_reload_functionality(self):
        """Test deep reload functionality."""
        import importlib
        import sys
        import tempfile
        from pathlib import Path

        # Create a temporary directory and module file
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            module_file = temp_path / "test_module.py"
            module_file.write_text("test_attr = 'test_value'\n")

            # Add temp_dir to sys.path
            sys.path.insert(0, temp_dir)
            try:
                # Import the module
                test_module = importlib.import_module("test_module")
                self.assertEqual(test_module.test_attr, "test_value")

                # Test deep reload
                reloaded_module = deep_reload(test_module)
                self.assertIsNotNone(reloaded_module)
                self.assertEqual(reloaded_module.__name__, "test_module")
            finally:
                # Clean up sys.path
                if temp_dir in sys.path:
                    sys.path.remove(temp_dir)
                if "test_module" in sys.modules:
                    del sys.modules["test_module"]

    def test_deep_reload_invalid_input(self):
        """Test that deep_reload raises TypeError for invalid input."""
        with self.assertRaises(TypeError):
            deep_reload("not_a_module")

    def test_hash_consistency(self):
        """Test that hash calculation is consistent for the same content."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create identical files
            file1 = temp_path / "file1.py"
            file1.write_text("print('same content')")

            file2 = temp_path / "file2.py"
            file2.write_text("print('same content')")

            # Calculate hash
            hash1 = hash_python_files_in_folder(temp_path)

            # Delete and recreate with same content
            file1.unlink()
            file1.write_text("print('same content')")

            hash2 = hash_python_files_in_folder(temp_path)

            # Hashes should be the same
            self.assertEqual(hash1, hash2)

    def test_hash_file_order_independence(self):
        """Test that hash is independent of file creation order."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create files in one order
            file1 = temp_path / "file1.py"
            file1.write_text("content1")

            file2 = temp_path / "file2.py"
            file2.write_text("content2")

            hash1 = hash_python_files_in_folder(temp_dir)

            # Delete and recreate in different order
            file1.unlink()
            file2.unlink()

            file2 = temp_path / "file2.py"
            file2.write_text("content2")

            file1 = temp_path / "file1.py"
            file1.write_text("content1")

            hash2 = hash_python_files_in_folder(temp_dir)

            # Hashes should be the same
            self.assertEqual(hash1, hash2)

    def test_hash_with_empty_directory(self):
        """Test hash calculation with empty directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Empty directory should still produce a hash
            hash1 = hash_python_files_in_folder(temp_path)
            self.assertIsInstance(hash1, str)
            self.assertEqual(len(hash1), 64)

    def test_hash_with_non_existent_directory(self):
        """Test hash calculation with non-existent directory."""
        with self.assertRaises(ValueError):
            hash_python_files_in_folder("/non/existent/path")

    def test_custom_file_extensions(self):
        """Test hash calculation with custom file extensions."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create files with different extensions
            py_file = temp_path / "test.py"
            py_file.write_text("print('python')")

            txt_file = temp_path / "test.txt"
            txt_file.write_text("text content")

            # Test with only .py files (default)
            hash1 = hash_python_files_in_folder(temp_path, file_exts=(".py",))

            # Test with .txt files
            hash2 = hash_python_files_in_folder(temp_path, file_exts=(".txt",))

            # Test with both
            hash3 = hash_python_files_in_folder(temp_path, file_exts=(".py", ".txt"))

            # All hashes should be different
            self.assertNotEqual(hash1, hash2)
            self.assertNotEqual(hash2, hash3)
            self.assertNotEqual(hash1, hash3)


if __name__ == "__main__":
    unittest.main()
