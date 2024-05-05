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
        ) as (devices, sample_positions):
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
                self.sample_view.get_sample_position_status("furnace_1/inside/1")[0].name,
            )
            self.assertEqual(
                "LOCKED",
                self.sample_view.get_sample_position_status("furnace_table")[0].name,
            )
        time.sleep(0.5)
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

        with lab_view.request_resources({}, timeout=1) as (devices, sample_positions):
            self.assertDictEqual({}, devices)
            self.assertEqual({}, sample_positions)
