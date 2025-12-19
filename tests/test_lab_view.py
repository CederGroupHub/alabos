import time
from multiprocessing import Process
from traceback import print_exc
from unittest import TestCase

from bson import ObjectId

from alab_management.device_view import DeviceView
from alab_management.lab_view import LabView
from alab_management.sample_view import SampleView
from alab_management.scripts.cleanup_lab import cleanup_lab
from alab_management.scripts.launch_lab import launch_resource_manager
from alab_management.scripts.setup_lab import setup_lab
from alab_management.task_manager.task_manager import TaskManager
from alab_management.task_view import TaskView


def launch_task_manager():
    try:
        task_manager = TaskManager()
        task_manager.run()
    except Exception:
        print(print_exc())
        raise


class TestLabView(TestCase):
    def setUp(self) -> None:
        cleanup_lab(
            all_collections=True,
            _force_i_know_its_dangerous=True,
            sim_mode=True,
            database_name="Alab_sim",
            user_confirmation="y",
        )
        setup_lab()
        self.device_view = DeviceView()
        self.device_list = self.device_view._device_list
        self.sample_view = SampleView()
        self.task_view = TaskView()
        self.process = Process(target=launch_resource_manager)
        self.process.daemon = True
        self.process.start()
        time.sleep(1)

    def tearDown(self) -> None:
        self.process.terminate()
        cleanup_lab(
            all_collections=True,
            _force_i_know_its_dangerous=True,
            sim_mode=True,
            database_name="Alab_sim",
            user_confirmation="y",
        )
        time.sleep(1)

    def test_request_resources(self):
        device_types = {
            device.__name__: device
            for device in {device.__class__ for device in self.device_list.values()}
        }
        Furnace = device_types["Furnace"]
        RobotArm = device_types["RobotArm"]

        task_id = self.task_view.create_task(
            **{
                "task_type": "Heating",
                "samples": {"sample": ObjectId()},
                "parameters": {"setpoints": [[10, 600]]},
            }
        )
        lab_view = LabView(task_id=task_id)

        with lab_view.request_resources(
            {
                Furnace: {"inside": 1},
                RobotArm: {},
                None: {
                    "furnace_table": 1,
                },
            },
            timeout=1,
        ) as (inner_devices, sample_positions):
            self.assertDictEqual(
                {
                    Furnace: {"inside": ["furnace_1/inside/1"]},
                    None: {"furnace_table": ["furnace_table"]},
                },
                sample_positions,
            )
            self.assertEqual("OCCUPIED", self.device_view.get_status("furnace_1").name)
            self.assertEqual("OCCUPIED", self.device_view.get_status("dummy").name)

            self.assertEqual(
                "LOCKED",
                self.sample_view.get_sample_position_status("furnace_1/inside/1")[
                    0
                ].name,
            )
            self.assertEqual(
                "LOCKED",
                self.sample_view.get_sample_position_status("furnace_table")[0].name,
            )
        self.assertEqual("IDLE", self.device_view.get_status("furnace_1").name)
        self.assertEqual("IDLE", self.device_view.get_status("dummy").name)

        self.assertEqual(
            "EMPTY",
            self.sample_view.get_sample_position_status("furnace_1/inside/1")[0].name,
        )
        self.assertEqual(
            "EMPTY",
            self.sample_view.get_sample_position_status("furnace_table")[0].name,
        )

    def test_request_resources_empty(self):
        task_id = self.task_view.create_task(
            **{
                "task_type": "Heating",
                "samples": {"sample": ObjectId()},
                "parameters": {"setpoints": [[10, 600]]},
            }
        )
        lab_view = LabView(task_id=task_id)

        with lab_view.request_resources({}, timeout=1) as (
            inner_devices,
            sample_positions,
        ):
            self.assertDictEqual({}, inner_devices)
            self.assertEqual({}, sample_positions)

    def test_request_resources_exact_positions(self):
        """Test exact_positions functionality with all use cases."""
        device_types = {
            device.__name__: device
            for device in {device.__class__ for device in self.device_list.values()}
        }
        Furnace = device_types["Furnace"]

        # Test 1: Prefix matching (default behavior) - should match multiple positions
        task_id_1 = self.task_view.create_task(
            **{
                "task_type": "Heating",
                "samples": {"sample": ObjectId()},
                "parameters": {"setpoints": [[10, 600]]},
            }
        )
        lab_view_1 = LabView(task_id=task_id_1)

        with lab_view_1.request_resources(
            {Furnace: {"inside": 2}}, timeout=1
        ) as (devices, positions):
            # Should get 2 positions matching prefix "furnace_X/inside"
            self.assertEqual(len(positions[Furnace]["inside"]), 2)
            # Both should start with "furnace_" and "/inside/"
            for pos in positions[Furnace]["inside"]:
                self.assertIn("/inside/", pos)
                self.assertTrue(pos.startswith("furnace_"))

        # Test 2: Exact matching with full position name (standalone position)
        # This is the main use case: prevent "input_rack/slot/1" from matching "input_rack/slot/10"
        task_id_2 = self.task_view.create_task(
            **{
                "task_type": "Heating",
                "samples": {"sample": ObjectId()},
                "parameters": {"setpoints": [[10, 600]]},
            }
        )
        lab_view_2 = LabView(task_id=task_id_2)

        with lab_view_2.request_resources(
            {None: {"furnace_table": 1}}, exact_positions={"furnace_table"}, timeout=1
        ) as (devices, positions):
            # Should get exactly "furnace_table" (not "furnace_table_2" if it existed)
            self.assertEqual(positions[None]["furnace_table"], ["furnace_table"])

        # Test 3: Exact matching prevents prefix collision
        # Request "furnace_temp/1" should NOT match "furnace_temp/10" or "furnace_temp/11"
        task_id_3 = self.task_view.create_task(
            **{
                "task_type": "Heating",
                "samples": {"sample": ObjectId()},
                "parameters": {"setpoints": [[10, 600]]},
            }
        )
        lab_view_3 = LabView(task_id=task_id_3)

        # First verify that prefix matching would match multiple positions
        with lab_view_3.request_resources(
            {None: {"furnace_temp": 2}}, timeout=1  # No exact_positions - uses prefix
        ) as (devices, positions):
            # Should get 2 positions (could be furnace_temp/1, furnace_temp/2, etc.)
            self.assertEqual(len(positions[None]["furnace_temp"]), 2)
            # Both should start with "furnace_temp/"
            for pos in positions[None]["furnace_temp"]:
                self.assertTrue(pos.startswith("furnace_temp/"))

        # Now test exact matching - request specific position
        task_id_3b = self.task_view.create_task(
            **{
                "task_type": "Heating",
                "samples": {"sample": ObjectId()},
                "parameters": {"setpoints": [[10, 600]]},
            }
        )
        lab_view_3b = LabView(task_id=task_id_3b)

        with lab_view_3b.request_resources(
            {None: {"furnace_temp/1": 1}}, exact_positions={"furnace_temp/1"}, timeout=1
        ) as (devices, positions):
            # Should get exactly "furnace_temp/1" (not "furnace_temp/10" or "furnace_temp/11")
            self.assertEqual(positions[None]["furnace_temp/1"], ["furnace_temp/1"])

        # Test 4: Invalid - exact matching with number > 1 should raise ValueError
        task_id_4 = self.task_view.create_task(
            **{
                "task_type": "Heating",
                "samples": {"sample": ObjectId()},
                "parameters": {"setpoints": [[10, 600]]},
            }
        )
        lab_view_4 = LabView(task_id=task_id_4)

        with self.assertRaises(ValueError) as context:
            with lab_view_4.request_resources(
                {Furnace: {"inside": 2}}, exact_positions={"inside"}, timeout=1
            ) as (devices, positions):
                pass
        self.assertIn("Exact position matching can only be used with number=1", str(context.exception))

        # Test 5: Mix of prefix and exact matching
        task_id_5 = self.task_view.create_task(
            **{
                "task_type": "Heating",
                "samples": {"sample": ObjectId()},
                "parameters": {"setpoints": [[10, 600]]},
            }
        )
        lab_view_5 = LabView(task_id=task_id_5)

        with lab_view_5.request_resources(
            {
                None: {
                    "furnace_table": 1,  # exact
                    "furnace_temp": 2,  # prefix (furnace_temp has 64 slots)
                }
            },
            exact_positions={"furnace_table"},
            timeout=1,
        ) as (devices, positions):
            # furnace_table should be exact (1 position)
            self.assertEqual(positions[None]["furnace_table"], ["furnace_table"])
            # furnace_temp should use prefix matching (2 positions)
            self.assertEqual(len(positions[None]["furnace_temp"]), 2)
            for pos in positions[None]["furnace_temp"]:
                self.assertTrue(pos.startswith("furnace_temp/"))

        # Test 6: Exact matching with full device position path
        # Request exact position "furnace_1/inside/1" should NOT match "furnace_1/inside/10"
        task_id_6 = self.task_view.create_task(
            **{
                "task_type": "Heating",
                "samples": {"sample": ObjectId()},
                "parameters": {"setpoints": [[10, 600]]},
            }
        )
        lab_view_6 = LabView(task_id=task_id_6)

        # Use the direct lock method to test exact position locking
        lab_view_6.lock_sample_position("furnace_1/inside/1")
        try:
            # Verify it's locked
            status, locked_by = self.sample_view.get_sample_position_status("furnace_1/inside/1")
            self.assertEqual(status.name, "LOCKED")
            self.assertEqual(locked_by, task_id_6)
            
            # Now try to request with prefix matching - should get a different slot
            with lab_view_6.request_resources(
                {"furnace_1": {"inside": 1}}, timeout=1  # Prefix matching
            ) as (devices, positions):
                pos = positions["furnace_1"]["inside"][0]
                # Should get a different slot since /1 is locked
                self.assertNotEqual(pos, "furnace_1/inside/1")
                self.assertTrue(pos.startswith("furnace_1/inside/"))
        finally:
            lab_view_6.release_sample_position("furnace_1/inside/1")

        # Test 6b: Request specific sample position from specific device by name with exact matching
        # This tests: {"furnace_1": {"inside/1": 1}}, exact_positions={"inside/1"}
        task_id_6b = self.task_view.create_task(
            **{
                "task_type": "Heating",
                "samples": {"sample": ObjectId()},
                "parameters": {"setpoints": [[10, 600]]},
            }
        )
        lab_view_6b = LabView(task_id=task_id_6b)

        # Request specific slot "inside/1" from specific device "furnace_1" with exact matching
        with lab_view_6b.request_resources(
            {"furnace_1": {"inside/1": 1}}, exact_positions={"inside/1"}, timeout=1
        ) as (devices, positions):
            # Should get exactly "furnace_1/inside/1" (not "furnace_1/inside/10")
            self.assertIn("furnace_1", devices)
            pos = positions["furnace_1"]["inside/1"][0]
            self.assertEqual(pos, "furnace_1/inside/1")
            
            # Verify it's locked
            status, locked_by = self.sample_view.get_sample_position_status("furnace_1/inside/1")
            self.assertEqual(status.name, "LOCKED")
            self.assertEqual(locked_by, task_id_6b)

        # Test 6c: Request specific sample position from specific device - prefix vs exact comparison
        # First test prefix matching (could match multiple)
        task_id_6c1 = self.task_view.create_task(
            **{
                "task_type": "Heating",
                "samples": {"sample": ObjectId()},
                "parameters": {"setpoints": [[10, 600]]},
            }
        )
        lab_view_6c1 = LabView(task_id=task_id_6c1)

        with lab_view_6c1.request_resources(
            {"furnace_1": {"inside/1": 1}}, timeout=1  # Prefix matching
        ) as (devices, positions):
            # With prefix matching, "inside/1" could match "inside/1", "inside/10", "inside/11", etc.
            # But since we only have inside/1 through inside/8, it should get one of those
            pos = positions["furnace_1"]["inside/1"][0]
            self.assertTrue(pos.startswith("furnace_1/inside/"))
            # Should be a valid slot number (1-8)
            slot_num = int(pos.split("/")[-1])
            self.assertGreaterEqual(slot_num, 1)
            self.assertLessEqual(slot_num, 8)

        # Now test exact matching - should get exactly "inside/1"
        task_id_6c2 = self.task_view.create_task(
            **{
                "task_type": "Heating",
                "samples": {"sample": ObjectId()},
                "parameters": {"setpoints": [[10, 600]]},
            }
        )
        lab_view_6c2 = LabView(task_id=task_id_6c2)

        with lab_view_6c2.request_resources(
            {"furnace_1": {"inside/1": 1}}, exact_positions={"inside/1"}, timeout=1
        ) as (devices, positions):
            # Should get exactly "furnace_1/inside/1"
            pos = positions["furnace_1"]["inside/1"][0]
            self.assertEqual(pos, "furnace_1/inside/1")

        # Test 6d: Request multiple specific positions from the same device
        task_id_6d = self.task_view.create_task(
            **{
                "task_type": "Heating",
                "samples": {"sample": ObjectId()},
                "parameters": {"setpoints": [[10, 600]]},
            }
        )
        lab_view_6d = LabView(task_id=task_id_6d)

        with lab_view_6d.request_resources(
            {
                "furnace_1": {
                    "inside/1": 1,
                    "inside/2": 1,
                }
            },
            exact_positions={"inside/1", "inside/2"},
            timeout=1,
        ) as (devices, positions):
            # Should get exactly both positions
            pos1 = positions["furnace_1"]["inside/1"][0]
            pos2 = positions["furnace_1"]["inside/2"][0]
            self.assertEqual(pos1, "furnace_1/inside/1")
            self.assertEqual(pos2, "furnace_1/inside/2")
            self.assertIn("furnace_1", devices)

        # Test 6e: Request specific position from device by type vs by name
        # When requesting by type, any available device of that type can be assigned
        # When requesting by name, only that specific device is used
        task_id_6e1 = self.task_view.create_task(
            **{
                "task_type": "Heating",
                "samples": {"sample": ObjectId()},
                "parameters": {"setpoints": [[10, 600]]},
            }
        )
        lab_view_6e1 = LabView(task_id=task_id_6e1)

        # Request by type - any furnace can be assigned
        with lab_view_6e1.request_resources(
            {Furnace: {"inside/1": 1}}, exact_positions={"inside/1"}, timeout=1
        ) as (devices, positions):
            # Should get a furnace (could be furnace_1, furnace_2, etc.)
            furnace_device = devices[Furnace]
            self.assertTrue(furnace_device.startswith("furnace_"))
            pos = positions[Furnace]["inside/1"][0]
            # Position should match the assigned device
            self.assertTrue(pos.startswith(f"{furnace_device}/inside/1"))
            # Should be exactly "inside/1" slot (not "inside/10")
            self.assertEqual(pos, f"{furnace_device}/inside/1")

        # Request by name - only that specific device
        task_id_6e2 = self.task_view.create_task(
            **{
                "task_type": "Heating",
                "samples": {"sample": ObjectId()},
                "parameters": {"setpoints": [[10, 600]]},
            }
        )
        lab_view_6e2 = LabView(task_id=task_id_6e2)

        with lab_view_6e2.request_resources(
            {"furnace_2": {"inside/1": 1}}, exact_positions={"inside/1"}, timeout=1
        ) as (devices, positions):
            # Should get exactly "furnace_2" (not any other furnace)
            self.assertIn("furnace_2", devices)
            pos = positions["furnace_2"]["inside/1"][0]
            self.assertEqual(pos, "furnace_2/inside/1")

        # Test 7: Multiple exact positions (standalone positions)
        task_id_7 = self.task_view.create_task(
            **{
                "task_type": "Heating",
                "samples": {"sample": ObjectId()},
                "parameters": {"setpoints": [[10, 600]]},
            }
        )
        lab_view_7 = LabView(task_id=task_id_7)

        with lab_view_7.request_resources(
            {
                None: {
                    "furnace_table": 1,
                    "furnace_temp/1": 1,
                },
            },
            exact_positions={"furnace_table", "furnace_temp/1"},
            timeout=1,
        ) as (devices, positions):
            # Both should be exact matches
            self.assertEqual(positions[None]["furnace_table"], ["furnace_table"])
            self.assertEqual(positions[None]["furnace_temp/1"], ["furnace_temp/1"])

        # Test 8: Verify exact matching works with positions that have similar prefixes
        # This is the main use case: "input_rack/slot/1" should NOT match "input_rack/slot/10"
        # We'll simulate this with furnace_temp positions
        task_id_8 = self.task_view.create_task(
            **{
                "task_type": "Heating",
                "samples": {"sample": ObjectId()},
                "parameters": {"setpoints": [[10, 600]]},
            }
        )
        lab_view_8 = LabView(task_id=task_id_8)

        # Request "furnace_temp/1" with exact matching
        with lab_view_8.request_resources(
            {None: {"furnace_temp/1": 1}}, exact_positions={"furnace_temp/1"}, timeout=1
        ) as (devices, positions):
            # Should get exactly "furnace_temp/1", not "furnace_temp/10" or "furnace_temp/11"
            pos = positions[None]["furnace_temp/1"][0]
            self.assertEqual(pos, "furnace_temp/1")
            
        # Verify that prefix matching would have matched multiple positions
        task_id_8b = self.task_view.create_task(
            **{
                "task_type": "Heating",
                "samples": {"sample": ObjectId()},
                "parameters": {"setpoints": [[10, 600]]},
            }
        )
        lab_view_8b = LabView(task_id=task_id_8b)
        
        with lab_view_8b.request_resources(
            {None: {"furnace_temp/1": 1}}, timeout=1  # No exact_positions - prefix match
        ) as (devices, positions):
            # With prefix matching, "furnace_temp/1" could match "furnace_temp/1", "furnace_temp/10", etc.
            # But the system should still return a valid position
            pos = positions[None]["furnace_temp/1"][0]
            self.assertTrue(pos.startswith("furnace_temp/"))

    def test_lock_sample_position_methods(self):
        """Test the new lock_sample_position and lock_exact_sample_positions methods."""
        task_id = self.task_view.create_task(
            **{
                "task_type": "Heating",
                "samples": {"sample": ObjectId()},
                "parameters": {"setpoints": [[10, 600]]},
            }
        )
        lab_view = LabView(task_id=task_id)

        # Test 1: lock_sample_position - lock a single exact position
        lab_view.lock_sample_position("furnace_table")
        status, locked_by = self.sample_view.get_sample_position_status("furnace_table")
        self.assertEqual(status.name, "LOCKED")
        self.assertEqual(locked_by, task_id)
        
        # Verify it's in the locked positions list
        locked_positions = lab_view.get_locked_sample_positions()
        self.assertIn("furnace_table", locked_positions)
        
        # Test 2: release_sample_position
        lab_view.release_sample_position("furnace_table")
        status, locked_by = self.sample_view.get_sample_position_status("furnace_table")
        self.assertEqual(status.name, "EMPTY")
        self.assertIsNone(locked_by)

        # Test 3: lock_exact_sample_positions context manager
        with lab_view.lock_exact_sample_positions(["furnace_table", "furnace_1/inside/1"]) as locked:
            self.assertEqual(locked, ["furnace_table", "furnace_1/inside/1"])
            
            # Verify both are locked
            status1, locked_by1 = self.sample_view.get_sample_position_status("furnace_table")
            status2, locked_by2 = self.sample_view.get_sample_position_status("furnace_1/inside/1")
            self.assertEqual(status1.name, "LOCKED")
            self.assertEqual(status2.name, "LOCKED")
            self.assertEqual(locked_by1, task_id)
            self.assertEqual(locked_by2, task_id)
            
            # Verify they're in locked positions
            locked_positions = lab_view.get_locked_sample_positions()
            self.assertIn("furnace_table", locked_positions)
            self.assertIn("furnace_1/inside/1", locked_positions)
        
        # After context exit, positions should be released
        status1, locked_by1 = self.sample_view.get_sample_position_status("furnace_table")
        status2, locked_by2 = self.sample_view.get_sample_position_status("furnace_1/inside/1")
        self.assertEqual(status1.name, "EMPTY")
        self.assertEqual(status2.name, "EMPTY")
        self.assertIsNone(locked_by1)
        self.assertIsNone(locked_by2)

        # Test 4: lock_exact_sample_positions with exception - should still release
        try:
            with lab_view.lock_exact_sample_positions(["furnace_table"]) as locked:
                self.assertEqual(locked, ["furnace_table"])
                # Verify locked
                status, locked_by = self.sample_view.get_sample_position_status("furnace_table")
                self.assertEqual(status.name, "LOCKED")
                raise ValueError("Test exception")
        except ValueError:
            pass
        
        # Should be released even after exception
        status, locked_by = self.sample_view.get_sample_position_status("furnace_table")
        self.assertEqual(status.name, "EMPTY")
        self.assertIsNone(locked_by)

        # Test 5: release_sample_position validation - can't release position not locked by this task
        other_task_id = self.task_view.create_task(
            **{
                "task_type": "Heating",
                "samples": {"sample": ObjectId()},
                "parameters": {"setpoints": [[10, 600]]},
            }
        )
        other_lab_view = LabView(task_id=other_task_id)
        
        # Lock with other task
        other_lab_view.lock_sample_position("furnace_table")
        
        # Try to release with current task - should fail
        with self.assertRaises(ValueError) as context:
            lab_view.release_sample_position("furnace_table")
        self.assertIn("not locked by this task", str(context.exception))
        
        # Clean up
        other_lab_view.release_sample_position("furnace_table")
