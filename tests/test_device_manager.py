import time
from threading import Thread
from unittest import TestCase

from bson import ObjectId

from alab_management.device_manager import DeviceManager, DevicesClient
from alab_management.scripts.cleanup_lab import cleanup_lab
from alab_management.scripts.setup_lab import setup_lab


def launch_device_manager():
    from alab_management.utils.module_ops import load_definition

    load_definition()
    device_manager = DeviceManager(_check_status=False)
    device_manager.run()


class TestDeviceManager(TestCase):
    def setUp(self):
        cleanup_lab()
        setup_lab()
        self.devices_client = DevicesClient(task_id=ObjectId(), timeout=5)
        self.process = Thread(target=launch_device_manager)
        self.process.daemon = True
        self.process.start()
        time.sleep(1.5)

    def tearDown(self):
        cleanup_lab()

    def test_rpc(self):
        furnace = self.devices_client["furnace_1"]

        self.assertEqual(300, furnace.get_temperature())
        with self.assertRaises(AttributeError):
            furnace.not_exist_func()
        f = furnace.sample_positions
        self.assertEqual("<method furnace_1.sample_positions>", str(f))

        # try __getitem__
        with self.assertRaises(AttributeError):
            _ = f[0]

        # try __eq__
        with self.assertRaises(AttributeError):
            _ = f == {"aaa": 1}

        # try to call a property
        with self.assertRaises(TypeError):
            f()
