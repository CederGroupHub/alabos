import os
from pathlib import Path
from unittest import TestCase

os.environ["ALAB_CONFIG"] = (Path(__file__).parent /
                             "fake_lab" / "config.toml").as_posix()

from bson import ObjectId

from alab_management import SampleView
from alab_management.scripts import setup_lab
from alab_management.scripts.cleanup_lab import _cleanup_lab


class TestSampleView(TestCase):
    def setUp(self) -> None:
        _cleanup_lab()
        setup_lab()
        self.sample_view = SampleView()
        self.sample_view._sample_collection.drop()

    def tearDown(self) -> None:
        _cleanup_lab()
        self.sample_view._sample_collection.drop()

    def test_create_sample(self):
        sample_id = self.sample_view.create_sample("test", position="furnace_table")
        sample = self.sample_view.get_sample(sample_id=sample_id)
        self.assertEqual("furnace_table", sample.position)
        self.assertEqual("test", sample.name)

        # try to create samples with same name
        sample_id = self.sample_view.create_sample("test", position="furnace_1.inside")
        sample = self.sample_view.get_sample(sample_id=sample_id)
        self.assertEqual("furnace_1.inside", sample.position)
        self.assertEqual("test", sample.name)

        # try to create samples with non-exist positions
        with self.assertRaises(ValueError):
            self.sample_view.create_sample("test_1", position="non-exist position")

        # try to create samples with the same position
        with self.assertRaises(ValueError):
            self.sample_view.create_sample("test_2", position="furnace_table")

    def test_get_sample(self):
        # try to get a non-exist sample
        sample = self.sample_view.get_sample(sample_id=ObjectId())
        self.assertIs(None, sample)

    def test_move_sample(self):
        sample_id = self.sample_view.create_sample("test", position=None)
        sample_id_2 = self.sample_view.create_sample("test", position=None)
        sample = self.sample_view.get_sample(sample_id=sample_id)
        self.assertEqual(None, sample.position)

        self.sample_view.move_sample(sample_id=sample_id, position="furnace_table")
        sample = self.sample_view.get_sample(sample_id=sample_id)
        self.assertEqual("furnace_table", sample.position)

        # try to move a non-exist sample
        with self.assertRaises(ValueError):
            self.sample_view.move_sample(sample_id=ObjectId(), position="furnace_table")

        # try to move a sample to where it is
        self.sample_view.move_sample(sample_id=sample_id,
                                     position=self.sample_view.get_sample(sample_id).position)
        sample = self.sample_view.get_sample(sample_id=sample_id)
        self.assertEqual("furnace_table", sample.position)

        # try to move a sample to an occupied position
        with self.assertRaises(ValueError):
            self.sample_view.move_sample(sample_id=sample_id_2, position="furnace_table")
        sample_2 = self.sample_view.get_sample(sample_id=sample_id_2)
        self.assertEqual(None, sample_2.position)

        # move the sample to None
        self.sample_view.move_sample(sample_id=sample_id, position=None)
        sample = self.sample_view.get_sample(sample_id=sample_id)
        self.assertEqual(None, sample.position)

    def test_lock_sample_position(self):
        task_id = ObjectId()
        self.sample_view.lock_sample_position(task_id=task_id, position="furnace_table")

        sample_id = self.sample_view.create_sample("test")

        self.assertEqual("LOCKED", self.sample_view.get_sample_position_status("furnace_table")[0].name)

        self.sample_view.release_sample_position("furnace_table")

        self.sample_view.move_sample(sample_id=sample_id, position="furnace_table")

        # try to lock a sample position that already has a sample
        with self.assertRaises(ValueError):
            self.sample_view.lock_sample_position(task_id=task_id, position="furnace_table")

        # try to lock a sample position with a sample that has the same task id
        self.sample_view.update_sample_task_id(sample_id=sample_id, task_id=task_id)
        self.sample_view.lock_sample_position(task_id=task_id, position="furnace_table")
        sample = self.sample_view.get_sample(sample_id=sample_id)
        self.assertEqual("furnace_table", sample.position)
        self.assertEqual("OCCUPIED", self.sample_view.get_sample_position_status("furnace_table")[0].name)

        self.sample_view.release_sample_position("furnace_table")

        self.sample_view.move_sample(sample_id=sample_id, position=None)

        # try to lock a sample position twice with same task id
        self.sample_view.lock_sample_position(task_id, position="furnace_table")
        self.sample_view.lock_sample_position(task_id, position="furnace_table")

        self.assertEqual("LOCKED", self.sample_view.get_sample_position_status("furnace_table")[0].name)

        # try to lock a sample position with different task id
        task_id_2 = ObjectId()
        with self.assertRaises(ValueError):
            self.sample_view.lock_sample_position(task_id_2, position="furnace_table")

    def test_request_sample_position_single(self):
        task_id = ObjectId()

        with self.sample_view.request_sample_positions(task_id, ["furnace_table", "furnace_1.inside"], timeout=5) \
                as sample_positions:
            self.assertFalse(sample_positions is None)
            for sample_position_prefix, sample_position in sample_positions.items():
                self.assertTrue(sample_position.startswith(sample_position_prefix))
                self.assertEqual("LOCKED", self.sample_view.get_sample_position_status(sample_position)[0].name)
                self.assertEqual(task_id, self.sample_view.get_sample_position_status(sample_position)[1])

        for sample_position in sample_positions.values():
            self.assertEqual("EMPTY", self.sample_view.get_sample_position_status(sample_position)[0].name)
            self.assertEqual(None, self.sample_view.get_sample_position_status(sample_position)[1])

    def test_request_device_timeout(self):
        task_id = ObjectId()
        task_id_2 = ObjectId()

        with self.sample_view.request_sample_positions(task_id, ["furnace_table", "furnace_1.inside"], timeout=1) \
                as sample_positions:
            self.assertFalse(sample_positions is None)
            with self.sample_view.request_sample_positions(task_id_2, ["furnace_table", "furnace_1.inside"], timeout=1) \
                    as _sample_positions:
                self.assertIs(None, _sample_positions)

    def test_request_devices_queue(self):
        import threading
        import time
        import pytest_reraise

        reraise_1 = pytest_reraise.Reraise()
        reraise_2 = pytest_reraise.Reraise()

        task_id = ObjectId()
        task_id_2 = ObjectId()

        @reraise_1.wrap
        def _request_1():
            start_time = time.perf_counter()
            with self.sample_view.request_sample_positions(task_id,
                                                           ["furnace_table", "furnace_1.inside"], timeout=100) \
                    as sample_positions:
                end_time = time.perf_counter()
                self.assertAlmostEqual(end_time - start_time, 0.0, delta=1.2)
                self.assertFalse(sample_positions is None)
                time.sleep(2)

        @reraise_2.wrap
        def _request_2():
            start_time = time.perf_counter()
            with self.sample_view.request_sample_positions(task_id_2,
                                                           ["furnace_table", "furnace_1.inside"], timeout=100) \
                    as sample_positions:
                end_time = time.perf_counter()
                self.assertAlmostEqual(end_time - start_time, 2.0, delta=1.2)
                self.assertFalse(sample_positions is None)

        t1 = threading.Thread(target=_request_1)
        t2 = threading.Thread(target=_request_2)

        t1.start()
        t2.start()

        t1.join()
        t2.join()

        reraise_1()
        reraise_2()

    def test_request_sample_positions_twice(self):
        task_id = ObjectId()

        self.assertEqual("EMPTY", self.sample_view.get_sample_position_status("furnace_table")[0].name)
        with self.sample_view.request_sample_positions(task_id, ["furnace_table", "furnace_1.inside"]):
            self.assertEqual("LOCKED", self.sample_view.get_sample_position_status("furnace_table")[0].name)
            with self.sample_view.request_sample_positions(task_id, ["furnace_table"], timeout=1) as sample_positions_:
                self.assertDictEqual({"furnace_table": "furnace_table"}, sample_positions_)
                self.assertEqual("LOCKED", self.sample_view.get_sample_position_status("furnace_table")[0].name)
                with self.sample_view.request_sample_positions(task_id, ["furnace_table"],
                                                               timeout=1) as sample_positions__:
                    self.assertDictEqual({"furnace_table": "furnace_table"}, sample_positions__)
                    self.assertEqual("LOCKED", self.sample_view.get_sample_position_status("furnace_table")[0].name)

                self.assertEqual("LOCKED", self.sample_view.get_sample_position_status("furnace_table")[0].name)

            self.assertEqual("LOCKED", self.sample_view.get_sample_position_status("furnace_table")[0].name)

        self.assertEqual("EMPTY", self.sample_view.get_sample_position_status("furnace_table")[0].name)
        self.assertEqual(None, self.sample_view.get_sample_position_status("furnace_table")[1])

    def test_request_sample_positions_occupied(self):
        task_id = ObjectId()
        sample_id = self.sample_view.create_sample("test", position=None)
        self.assertEqual("EMPTY", self.sample_view.get_sample_position_status("furnace_table")[0].name)
        self.sample_view.move_sample(sample_id, "furnace_table")
        self.assertEqual("OCCUPIED", self.sample_view.get_sample_position_status("furnace_table")[0].name)

        self.sample_view.update_sample_task_id(sample_id, task_id)

        with self.sample_view.request_sample_positions(task_id, ["furnace_table", "furnace_1.inside"]):
            self.assertEqual("OCCUPIED", self.sample_view.get_sample_position_status("furnace_table")[0].name)
            self.assertEqual(task_id, self.sample_view.get_sample_position_status("furnace_table")[1])

        self.assertEqual("OCCUPIED", self.sample_view.get_sample_position_status("furnace_table")[0].name)
        self.assertEqual(None, self.sample_view.get_sample_position("furnace_table")["task_id"])
