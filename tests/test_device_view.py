from pathlib import Path
from unittest import TestCase
import os

os.environ["ALAB_CONFIG"] = (Path(__file__).parent / ".." /
                             "alab_management" / "config.default.toml").as_posix()
from bson import ObjectId

from alab_management.lab_status import DeviceView


class TestDeviceView(TestCase):
    def setUp(self):
        self.device_view = DeviceView()

    def test_get_status(self):
        device_name = "furnace_1"
        self.assertEqual(self.device_view.get_status(device_name).name, "UNKNOWN")

        device_name = "non-exist device name"
        with self.assertRaises(ValueError):
            self.device_view.get_status(device_name)

    def test_set_status(self):
        device_name = "furnace_1"
        sample_id = ObjectId()
        task_id = ObjectId()
        self.device_view.set_status(device_name=device_name, status="IDLE")
        self.assertEqual(self.device_view.get_status(device_name).name, "IDLE")
        self.device_view.set_status(device_name=device_name, status="UNKNOWN", sample_id=None, task_id=None)
        self.assertEqual(self.device_view.get_device_info(device_name)["status"], "UNKNOWN")
        self.assertEqual(self.device_view.get_device_info(device_name)["sample_id"], None)
        self.assertEqual(self.device_view.get_device_info(device_name)["task_id"], None)

        self.device_view.set_status(device_name=device_name, status="IDLE", sample_id=sample_id)
        self.assertEqual(self.device_view.get_status(device_name).name, "IDLE")
        self.assertEqual(self.device_view.get_device_info(device_name)["task_id"], None)
        self.assertEqual(self.device_view.get_device_info(device_name)["sample_id"], sample_id)
        self.device_view.set_status(device_name=device_name, status="UNKNOWN", sample_id=None, task_id=None)
        self.assertEqual(self.device_view.get_device_info(device_name)["status"], "UNKNOWN")
        self.assertEqual(self.device_view.get_device_info(device_name)["sample_id"], None)
        self.assertEqual(self.device_view.get_device_info(device_name)["task_id"], None)

        self.device_view.set_status(device_name=device_name, status="IDLE", sample_id=sample_id, task_id=task_id)
        self.assertEqual(self.device_view.get_status(device_name).name, "IDLE")
        self.assertEqual(self.device_view.get_device_info(device_name)["task_id"], task_id)
        self.assertEqual(self.device_view.get_device_info(device_name)["sample_id"], sample_id)
        self.device_view.set_status(device_name=device_name, status="UNKNOWN", sample_id=None, task_id=None)
        self.assertEqual(self.device_view.get_device_info(device_name)["status"], "UNKNOWN")
        self.assertEqual(self.device_view.get_device_info(device_name)["sample_id"], None)
        self.assertEqual(self.device_view.get_device_info(device_name)["task_id"], None)
