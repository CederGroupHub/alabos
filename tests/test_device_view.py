import time
from contextlib import contextmanager
from unittest import TestCase

from bson import ObjectId

from alab_management.device_view import DeviceView
from alab_management.scripts.cleanup_lab import cleanup_lab
from alab_management.scripts.setup_lab import setup_lab


def occupy_devices(devices, device_view: DeviceView, task_id: ObjectId):
    for device in devices.values():
        device_view.occupy_device(device["name"], task_id=task_id)


def release_devices(devices, device_view: DeviceView):
    for device in devices.values():
        if device["need_release"]:
            device_view.release_device(device["name"])


class TestDeviceView(TestCase):
    def setUp(self):
        cleanup_lab(all_collections=True, _force_i_know_its_dangerous=True)
        setup_lab()
        self.device_view = DeviceView()
        self.device_list = self.device_view._device_list
        self.device_names = [
            device_name for device_name in self.device_view._device_list
        ]

    def tearDown(self):
        cleanup_lab(all_collections=True, _force_i_know_its_dangerous=True)

    @contextmanager
    def request_devices(self, device_list, task_id: ObjectId, _timeout=None):
        cnt = 0
        devices = self.device_view.request_devices(
            task_id=task_id, device_types_str=device_list
        )
        while _timeout is not None and devices is None and _timeout >= cnt / 10:
            devices = self.device_view.request_devices(
                task_id=task_id, device_types_str=device_list
            )
            cnt += 1
            time.sleep(0.1)

        if devices is not None:
            occupy_devices(devices, self.device_view, task_id)
        yield {
            t: d["name"] for t, d in devices.items()
        } if devices is not None else None
        if devices is not None:
            release_devices(devices, self.device_view)

    def test_get_status(self):
        device_name = "furnace_1"
        self.assertEqual("IDLE", self.device_view.get_status(device_name).name)

        device_name = "non-exist device name"
        with self.assertRaises(ValueError):
            self.device_view.get_status(device_name)

    def test_occupy_device(self):
        device_name = self.device_names[0]
        task_id = ObjectId()
        self.assertEqual([], self.device_view.get_devices_by_task(task_id=task_id))
        self.device_view.occupy_device(device=device_name, task_id=task_id)
        self.assertEqual(
            [self.device_list[device_name]],
            self.device_view.get_devices_by_task(task_id=task_id),
        )
        self.assertEqual("OCCUPIED", self.device_view.get_status(device_name).name)
        self.assertEqual(task_id, self.device_view.get_device(device_name)["task_id"])
        self.device_view.occupy_device(device=device_name, task_id=task_id)
        self.device_view.release_device(device_name=device_name)
        self.assertEqual("IDLE", self.device_view.get_status(device_name).name)
        self.assertEqual(None, self.device_view.get_device(device_name)["task_id"])

    def test_release_device(self):
        device_name = self.device_names[0]

        # make sure it is idle
        self.assertEqual("IDLE", self.device_view.get_status(device_name).name)

        # if we release it twice, no error should be raised
        self.device_view.release_device(device_name=device_name)
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
        device_types = list(
            {device.__class__.__name__ for device in self.device_list.values()}
        )
        task_id = ObjectId()

        devices = self.device_view.request_devices(
            task_id, device_types_str=device_types
        )
        occupy_devices(devices, device_view=self.device_view, task_id=task_id)
        self.assertFalse(devices is None)
        for device_type, device in devices.items():
            self.assertIn(device_type, device_types)
            self.assertIn(device["name"], self.device_names)
            self.assertEqual(
                self.device_view.get_device(device["name"])["type"], device_type
            )
            self.assertEqual(
                "OCCUPIED", self.device_view.get_status(device["name"]).name
            )
            self.assertEqual(
                task_id, self.device_view.get_device(device["name"])["task_id"]
            )

        release_devices(devices, device_view=self.device_view)

        for device in devices.values():
            self.assertEqual("IDLE", self.device_view.get_status(device["name"]).name)
            self.assertEqual(
                None, self.device_view.get_device(device["name"])["task_id"]
            )

    def test_request_device_timeout(self):
        device_types = list(
            {device.__class__.__name__ for device in self.device_list.values()}
        )
        task_id = ObjectId()
        task_id_2 = ObjectId()

        devices = self.device_view.request_devices(
            task_id, device_types_str=device_types
        )
        self.assertFalse(devices is None)
        occupy_devices(devices, device_view=self.device_view, task_id=task_id)
        self.assertIs(
            None,
            self.device_view.request_devices(task_id_2, device_types_str=device_types),
        )
        release_devices(devices, device_view=self.device_view)

    def test_request_device_twice(self):
        device_types = list(
            {device.__class__.__name__ for device in self.device_list.values()}
        )
        task_id = ObjectId()

        with self.request_devices(device_types, task_id) as devices:
            for device in devices.values():
                self.assertEqual("OCCUPIED", self.device_view.get_status(device).name)
                self.assertEqual(
                    task_id, self.device_view.get_device(device)["task_id"]
                )

            with self.request_devices(device_types, task_id) as devices_:
                for device in devices_.values():
                    self.assertEqual(
                        "OCCUPIED", self.device_view.get_status(device).name
                    )
                    self.assertEqual(
                        task_id, self.device_view.get_device(device)["task_id"]
                    )
                with self.request_devices(device_types, task_id) as devices__:
                    for device in devices__.values():
                        self.assertEqual(
                            "OCCUPIED", self.device_view.get_status(device).name
                        )
                        self.assertEqual(
                            task_id, self.device_view.get_device(device)["task_id"]
                        )
            for device in devices.values():
                self.assertEqual("OCCUPIED", self.device_view.get_status(device).name)
                self.assertEqual(
                    task_id, self.device_view.get_device(device)["task_id"]
                )

        for device in devices.values():
            self.assertEqual("IDLE", self.device_view.get_status(device).name)
            self.assertEqual(None, self.device_view.get_device(device)["task_id"])
