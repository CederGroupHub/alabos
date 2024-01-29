import time
from multiprocessing import Process
from traceback import print_exc
from unittest import TestCase

from bson import ObjectId

from alab_management.device_manager import DeviceManager, DevicesClient
from alab_management.scripts.cleanup_lab import cleanup_lab
from alab_management.scripts.setup_lab import setup_lab


def launch_device_manager():
    try:
        device_manager = DeviceManager(_check_status=False)
        device_manager.run()
    except Exception:
        print_exc()
        raise


class TestDeviceManager(TestCase):
    def setUp(self):
        cleanup_lab(all_collections=True, _force_i_know_its_dangerous=True, sim_mode=True, database_name="Alab_sim", user_confirmation="y")
        setup_lab()
        self.devices_client = DevicesClient(task_id=ObjectId(), timeout=5)
        self.process = Process(target=launch_device_manager)
        self.process.daemon = False
        self.process.start()
        time.sleep(1.5)

    def tearDown(self):
        self.process.terminate()
        cleanup_lab(all_collections=True, _force_i_know_its_dangerous=True, sim_mode=True, database_name="Alab_sim", user_confirmation="y")
        time.sleep(1)

    def test_rpc(self):
        furnace = self.devices_client["furnace_1"]

        self.assertEqual(300, furnace.get_temperature())
        self.assertIs(None, furnace.run_program((1, 2)))
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
