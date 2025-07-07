#!/usr/bin/env python3
"""
Simple test script to demonstrate auto hot restart functionality.

This script shows how the auto restart feature works by:
1. Monitoring file changes
2. Calculating package hashes
3. Demonstrating the refresh process

Run this script to see the auto restart functionality in action.
"""

import os
import tempfile
from pathlib import Path

from alab_management.config import AlabOSConfig
from alab_management.utils.module_ops import (
    calculate_package_hash,
    hash_python_files_in_folder,
)


def test_auto_restart_demo():
    """Demonstrate the auto restart functionality."""
    print("=== Auto Hot Restart Demo ===\n")

    # Set config path to fake lab config for testing
    os.environ["ALABOS_CONFIG_PATH"] = "tests/fake_lab/config.toml"

    # Check if auto refresh is enabled
    config = AlabOSConfig()
    auto_refresh = config["general"].get("auto_refresh", False)
    print(f"Auto refresh enabled: {auto_refresh}")

    if not auto_refresh:
        print(
            "Note: Auto refresh is disabled. Enable it in your config.toml to use this feature."
        )
        print(
            "Add 'auto_refresh = true' to the [general] section of your config file.\n"
        )

    # Show current package hash
    print("Current package hash:")
    current_hash = calculate_package_hash()
    print(f"  {current_hash}")

    # Test with a temporary directory
    print("\n=== Testing File Change Detection ===")

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create initial files
        print(f"Creating test files in: {temp_path}")

        file1 = temp_path / "test1.py"
        file1.write_text("print('Hello World')")

        file2 = temp_path / "test2.py"
        file2.write_text("def test_function():\n    return 'test'")

        # Calculate initial hash
        hash1 = hash_python_files_in_folder(temp_path)
        print(f"Initial hash: {hash1}")

        # Modify a file
        print("\nModifying test1.py...")
        file1.write_text("print('Hello World - Modified')")

        hash2 = hash_python_files_in_folder(temp_path)
        print(f"Hash after modification: {hash2}")

        if hash1 != hash2:
            print("✓ Hash changed - file modification detected!")
        else:
            print("✗ Hash unchanged - file modification not detected!")

        # Add a new file
        print("\nAdding new file test3.py...")
        file3 = temp_path / "test3.py"
        file3.write_text("print('New file')")

        hash3 = hash_python_files_in_folder(temp_path)
        print(f"Hash after adding file: {hash3}")

        if hash2 != hash3:
            print("✓ Hash changed - new file detected!")
        else:
            print("✗ Hash unchanged - new file not detected!")

        # Test with non-Python files
        print("\nAdding non-Python file test.txt...")
        txt_file = temp_path / "test.txt"
        txt_file.write_text("This is a text file")

        hash4 = hash_python_files_in_folder(temp_path)
        print(f"Hash after adding .txt file: {hash4}")

        if hash3 == hash4:
            print("✓ Hash unchanged - .txt files are ignored (as expected)")
        else:
            print("✗ Hash changed - .txt files are not being ignored!")

    print("\n=== Auto Restart Process ===")
    print("When auto restart is enabled and file changes are detected:")
    print("1. Task manager stops launching new tasks")
    print("2. Resource manager stops allocating new resources")
    print("3. Device manager pauses all devices")
    print("4. System waits for running tasks to finish")
    print("5. All devices are disconnected")
    print("6. Device and task definitions are re-imported")
    print("7. Devices are reconnected")
    print("8. Device manager resumes all devices")
    print("9. Resource manager resumes allocating resources")
    print("10. Task manager resumes launching new tasks")

    print("\n=== Limitations ===")
    print("• Only Python source code files are monitored")
    print("• External libraries are not monitored")
    print("• New devices/tasks require manual restart")
    print("• Running tasks continue with old definitions")
    print("• Changes are reflected in newly launched tasks")

    print("\n=== Demo Complete ===")


if __name__ == "__main__":
    test_auto_restart_demo()
