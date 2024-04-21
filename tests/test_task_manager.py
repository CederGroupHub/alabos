import time
import unittest
from multiprocessing import Process
from traceback import print_exc

from bson import ObjectId

from alab_management.device_view import DeviceTaskStatus, DeviceView
from alab_management.device_view.device import get_all_devices
from alab_management.sample_view import SampleView
from alab_management.sample_view.sample_view import SamplePositionStatus
from alab_management.scripts.cleanup_lab import cleanup_lab
from alab_management.scripts.setup_lab import setup_lab
from alab_management.task_manager.resource_requester import ResourceRequester
from alab_management.task_manager.task_manager import TaskManager


def launch_task_manager():
    try:
        task_manager = TaskManager()
        task_manager._TaskManager__skip_checking_task_id = True
        task_manager.run()
    except Exception:
        print_exc()
        raise


class TestTaskManager(unittest.TestCase):
    def setUp(self) -> None:
        time.sleep(0.5)
        cleanup_lab(
            all_collections=True,
            _force_i_know_its_dangerous=True,
            sim_mode=True,
            database_name="Alab_sim",
            user_confirmation="y",
        )
        setup_lab()
        self.devices = get_all_devices()
        self.device_view = DeviceView()
        self.sample_view = SampleView()
        self.resource_requester = ResourceRequester(task_id=ObjectId())
        self.process = Process(target=launch_task_manager)
        self.process.daemon = True
        self.process.start()
        time.sleep(0.5)

    def tearDown(self) -> None:
        self.process.terminate()
        cleanup_lab(
            all_collections=True,
            _force_i_know_its_dangerous=True,
            sim_mode=True,
            database_name="Alab_sim",
            user_confirmation="y",
        )
        time.sleep(0.5)

    def test_task_requester(self):
        furnace_type = self.devices["furnace_1"].__class__

        # 1
        result = self.resource_requester.request_resources(
            {furnace_type: {"inside": 1}}, timeout=4
        )
        _id = result.pop("request_id")
        self.assertDictEqual(
            {
                "devices": {furnace_type: "furnace_1"},
                "sample_positions": {furnace_type: {"inside": ["furnace_1/inside"]}},
                "error": None,
            },
            result,
        )
        self.assertEqual(
            self.device_view.get_status("furnace_1"), DeviceTaskStatus.OCCUPIED
        )
        self.assertEqual(
            self.sample_view.get_sample_position_status("furnace_1/inside"),
            (SamplePositionStatus.LOCKED, self.resource_requester.task_id),
        )
        self.resource_requester.release_resources(_id)
        time.sleep(0.5)
        self.assertEqual(
            self.device_view.get_status("furnace_1"), DeviceTaskStatus.IDLE
        )
        self.assertEqual(
            self.sample_view.get_sample_position_status("furnace_1/inside"),
            (SamplePositionStatus.EMPTY, None),
        )

        # 2
        result = self.resource_requester.request_resources(
            {furnace_type: {"inside": 1}}, timeout=4
        )
        _id = result.pop("request_id")
        self.assertDictEqual(
            {
                "devices": {furnace_type: "furnace_1"},
                "sample_positions": {furnace_type: {"inside": ["furnace_1/inside"]}},
                "error": None,
            },
            result,
        )
        self.assertEqual(
            self.device_view.get_status("furnace_1"), DeviceTaskStatus.OCCUPIED
        )
        self.assertEqual(
            self.sample_view.get_sample_position_status("furnace_1/inside"),
            (SamplePositionStatus.LOCKED, self.resource_requester.task_id),
        )
        self.resource_requester.release_resources(_id)
        self.assertEqual(
            self.device_view.get_status("furnace_1"), DeviceTaskStatus.IDLE
        )
        self.assertEqual(
            self.sample_view.get_sample_position_status("furnace_1/inside"),
            (SamplePositionStatus.EMPTY, None),
        )

        # 3
        result = self.resource_requester.request_resources(
            {furnace_type: {"inside": 1}}, timeout=4
        )
        _id = result.pop("request_id")
        self.assertDictEqual(
            {
                "devices": {furnace_type: "furnace_1"},
                "sample_positions": {furnace_type: {"inside": ["furnace_1/inside"]}},
                "error": None,
            },
            result,
        )
        self.resource_requester.release_resources(_id)

        # 4
        result = self.resource_requester.request_resources(
            {furnace_type: {}, None: {"furnace_temp": 4}}, timeout=4
        )
        _id = result.pop("request_id")

        self.assertDictEqual(
            {
                "devices": {furnace_type: "furnace_1"},
                "sample_positions": {
                    None: {
                        "furnace_temp": [
                            "furnace_temp/1",
                            "furnace_temp/2",
                            "furnace_temp/3",
                            "furnace_temp/4",
                        ]
                    }
                },
                "error": None,
            },
            result,
        )
        self.resource_requester.release_resources(_id)

        # 5
        result = self.resource_requester.request_resources(
            {
                furnace_type: {"inside": 1},
                None: {"furnace_temp": 4},
            },
            timeout=4,
        )
        _id = result.pop("request_id")

        self.assertDictEqual(
            {
                "devices": {furnace_type: "furnace_1"},
                "sample_positions": {
                    furnace_type: {"inside": ["furnace_1/inside"]},
                    None: {
                        "furnace_temp": [
                            "furnace_temp/1",
                            "furnace_temp/2",
                            "furnace_temp/3",
                            "furnace_temp/4",
                        ]
                    },
                },
                "error": None,
            },
            result,
        )
        self.resource_requester.release_resources(_id)

    def test_task_request_wrong_number(self):
        with self.assertRaises(ValueError):
            self.resource_requester.request_resources(
                {None: {"furnace_temp": 10}}, timeout=4
            )
