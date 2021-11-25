import os
from pathlib import Path
from unittest import TestCase

from bson import ObjectId

os.environ["ALAB_CONFIG"] = (Path(__file__).parent /
                             "fake_lab" / "config.toml").as_posix()

from alab_management.lab_manager import LabManager
from alab_management import DeviceView, SampleView
from alab_management.scripts import setup_lab
from alab_management.scripts.cleanup_lab import _cleanup_lab


class TestLabManager(TestCase):
    def setUp(self) -> None:
        _cleanup_lab()
        setup_lab()
        self.device_view = DeviceView()
        self.device_list = self.device_view._device_list
        self.sample_view = SampleView()
        self.sample_view._sample_collection.drop()

    def tearDown(self) -> None:
        _cleanup_lab()
        self.sample_view._sample_collection.drop()

    def test_request_resources(self):
        device_types = {device.__name__: device
                        for device in {device.__class__ for device in self.device_list.values()}}
        Furnace = device_types["Furnace"]
        RobotArm = device_types["RobotArm"]

        task_id = ObjectId()
        lab_manager = LabManager(task_id=task_id, device_view=self.device_view, sample_view=self.sample_view)

        with lab_manager.request_resources({Furnace: ["$/inside"], RobotArm: [], None: [{"prefix": "furnace_table",
                                                                                         "number": 1}]}) \
                as (devices, sample_positions):
            self.assertDictEqual({Furnace: self.device_list["furnace_1"], RobotArm: self.device_list["dummy"]}, devices)
            self.assertDictEqual({Furnace: {"$/inside": ["furnace_1/inside"]}, RobotArm: {},
                                  None: {"furnace_table": ["furnace_table"]}}, sample_positions)
            self.assertEqual("OCCUPIED", self.device_view.get_status("furnace_1").name)
            self.assertEqual("OCCUPIED", self.device_view.get_status("dummy").name)

            self.assertEqual("LOCKED", self.sample_view.get_sample_position_status("furnace_1/inside")[0].name)
            self.assertEqual("LOCKED", self.sample_view.get_sample_position_status("furnace_table")[0].name)

        self.assertEqual("IDLE", self.device_view.get_status("furnace_1").name)
        self.assertEqual("IDLE", self.device_view.get_status("dummy").name)

        self.assertEqual("EMPTY", self.sample_view.get_sample_position_status("furnace_1/inside")[0].name)
        self.assertEqual("EMPTY", self.sample_view.get_sample_position_status("furnace_table")[0].name)
