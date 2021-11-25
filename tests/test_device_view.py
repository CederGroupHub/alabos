import os
from pathlib import Path
from unittest import TestCase

os.environ["ALAB_CONFIG"] = (Path(__file__).parent /
                             "fake_lab" / "config.toml").as_posix()

from bson import ObjectId

from alab_management import DeviceView
from alab_management.scripts import setup_lab
from alab_management.scripts.cleanup_lab import _cleanup_lab


class TestDeviceView(TestCase):
    def setUp(self):
        _cleanup_lab()
        setup_lab()
        self.device_view = DeviceView()
        self.device_list = self.device_view._device_list
        self.device_names = [device_name for device_name in self.device_view._device_list]

    def tearDown(self):
        _cleanup_lab()

    def test_get_status(self):
        device_name = "furnace_1"
        self.assertEqual("IDLE", self.device_view.get_status(device_name).name)

        device_name = "non-exist device name"
        with self.assertRaises(ValueError):
            self.device_view.get_status(device_name)

    def test_occupy_device(self):
        device_name = self.device_names[0]
        task_id = ObjectId()
        self.device_view.occupy_device(device=device_name, task_id=task_id)
        self.assertEqual("OCCUPIED", self.device_view.get_status(device_name).name)
        self.assertEqual(task_id, self.device_view.get_device(device_name)["task_id"])
        self.device_view.occupy_device(device=device_name, task_id=task_id)
        self.device_view.release_device(device=device_name)
        self.assertEqual("IDLE", self.device_view.get_status(device_name).name)
        self.assertEqual(None, self.device_view.get_device(device_name)["task_id"])

    def test_release_device(self):
        device_name = self.device_names[0]

        # make sure it is idle
        self.assertEqual("IDLE", self.device_view.get_status(device_name).name)

        # if we release it twice, no error should be raised
        self.device_view.release_device(device=device_name)
        self.assertEqual("IDLE", self.device_view.get_status(device_name).name)

    def test_occupied_device_twice(self):
        device_name = self.device_names[0]

        # make sure it is idle
        self.assertEqual("IDLE", self.device_view.get_status(device_name).name)

        task_id_1 = ObjectId()
        task_id_2 = ObjectId()
        self.device_view.occupy_device(device=device_name, task_id=task_id_1)

        # if we occupy device with the same task id, no error shall be raised
        self.device_view.occupy_device(device=device_name, task_id=task_id_1)

        # but if we occupy device with different task id, a ``ValueError`` shall
        # be raised
        with self.assertRaises(ValueError):
            self.device_view.occupy_device(device_name, task_id=task_id_2)

    def test_request_devices_single(self):
        device_types = list({device.__class__ for device in self.device_list.values()})
        task_id = ObjectId()

        with self.device_view.request_devices(task_id, device_types, timeout=5) as devices:
            self.assertFalse(devices is None)
            for device_type, device in devices.items():
                self.assertIn(device_type, device_types)
                self.assertIn(device.name, self.device_list)
                self.assertIsInstance(device, device_type)
                self.assertEqual("OCCUPIED", self.device_view.get_status(device.name).name)
                self.assertEqual(task_id, self.device_view.get_device(device.name)["task_id"])

        for device in devices.values():
            self.assertEqual("IDLE", self.device_view.get_status(device.name).name)
            self.assertEqual(None, self.device_view.get_device(device.name)["task_id"])

    def test_request_device_timeout(self):
        device_types = list({device.__class__ for device in self.device_list.values()})
        task_id = ObjectId()
        task_id_2 = ObjectId()

        with self.device_view.request_devices(task_id, device_types, timeout=1) as devices:
            self.assertFalse(devices is None)
            with self.device_view.request_devices(task_id_2, device_types, timeout=1) as _devices:
                self.assertIs(None, _devices)

    def test_request_device_twice(self):
        device_types = list({device.__class__ for device in self.device_list.values()})
        task_id = ObjectId()

        with self.device_view.request_devices(task_id, device_types) as devices:
            for device in devices.values():
                self.assertEqual("OCCUPIED", self.device_view.get_status(device.name).name)
                self.assertEqual(task_id, self.device_view.get_device(device.name)["task_id"])

            with self.device_view.request_devices(task_id, device_types, timeout=1) as devices_:
                for device in devices_.values():
                    self.assertEqual("OCCUPIED", self.device_view.get_status(device.name).name)
                    self.assertEqual(task_id, self.device_view.get_device(device.name)["task_id"])
                with self.device_view.request_devices(task_id, device_types, timeout=1) as devices__:
                    for device in devices__.values():
                        self.assertEqual("OCCUPIED", self.device_view.get_status(device.name).name)
                        self.assertEqual(task_id, self.device_view.get_device(device.name)["task_id"])
            for device in devices.values():
                self.assertEqual("OCCUPIED", self.device_view.get_status(device.name).name)
                self.assertEqual(task_id, self.device_view.get_device(device.name)["task_id"])

        for device in devices.values():
            self.assertEqual("IDLE", self.device_view.get_status(device.name).name)
            self.assertEqual(None, self.device_view.get_device(device.name)["task_id"])

    def test_request_devices_queue(self):
        import threading
        import time
        import pytest_reraise

        reraise_1 = pytest_reraise.Reraise()
        reraise_2 = pytest_reraise.Reraise()

        device_types = list({device.__class__ for device in self.device_list.values()})
        task_id = ObjectId()
        task_id_2 = ObjectId()

        @reraise_1.wrap
        def _request_1():
            start_time = time.perf_counter()
            with self.device_view.request_devices(task_id, device_types, timeout=100) as devices:
                end_time = time.perf_counter()
                self.assertAlmostEqual(end_time - start_time, 0.0, delta=1.2)
                self.assertFalse(devices is None)
                time.sleep(2)

        @reraise_2.wrap
        def _request_2():
            start_time = time.perf_counter()
            with self.device_view.request_devices(task_id_2, device_types, timeout=100) as devices:
                end_time = time.perf_counter()
                self.assertAlmostEqual(end_time - start_time, 1.0, delta=1.2)
                self.assertFalse(devices is None)

        t1 = threading.Thread(target=_request_1)
        t2 = threading.Thread(target=_request_2)

        t1.start()
        time.sleep(1)
        t2.start()

        t1.join()
        t2.join()

        reraise_1()
        reraise_2()
