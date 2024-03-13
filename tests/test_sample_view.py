import time
from contextlib import contextmanager
from unittest import TestCase

from bson import ObjectId

from alab_management.sample_view import SampleView
from alab_management.scripts.cleanup_lab import cleanup_lab
from alab_management.scripts.setup_lab import setup_lab


def occupy_sample_positions(sample_positions, sample_view: SampleView, task_id: ObjectId):
    for sample_positions_ in sample_positions.values():
        for sample_position_ in sample_positions_:
            sample_view.lock_sample_position(task_id, sample_position_["name"])


def release_sample_positions(sample_positions, sample_view: SampleView):
    for sample_positions_ in sample_positions.values():
        for sample_position in sample_positions_:
            if sample_position["need_release"]:
                sample_view.release_sample_position(sample_position["name"])


class TestSampleView(TestCase):
    def setUp(self) -> None:
        cleanup_lab(
            all_collections=True,
            _force_i_know_its_dangerous=True,
            sim_mode=True,
            database_name="Alab_sim",
            user_confirmation="y",
        )
        setup_lab()
        self.sample_view = SampleView()
        self.sample_view._sample_collection.drop()

    def tearDown(self) -> None:
        cleanup_lab(
            all_collections=True,
            _force_i_know_its_dangerous=True,
            sim_mode=True,
            database_name="Alab_sim",
            user_confirmation="y",
        )
        self.sample_view._sample_collection.drop()

    @contextmanager
    def request_sample_positions(self, sample_positions_list, task_id: ObjectId, _timeout=None):
        cnt = 0
        sample_positions = self.sample_view.request_sample_positions(task_id=task_id, sample_positions=sample_positions_list)
        while _timeout is not None and sample_positions is None and _timeout >= cnt / 10:
            sample_positions = self.sample_view.request_sample_positions(task_id=task_id, sample_positions=sample_positions_list)
            cnt += 1
            time.sleep(0.1)

        if sample_positions is not None:
            occupy_sample_positions(sample_positions, self.sample_view, task_id)
        yield (
            {prefix: [sp["name"] for sp in sps] for prefix, sps in sample_positions.items()}
            if sample_positions is not None
            else None
        )
        if sample_positions is not None:
            release_sample_positions(sample_positions, self.sample_view)

    def test_create_sample(self):
        sample_id = self.sample_view.create_sample("test", position="furnace_table")
        sample = self.sample_view.get_sample(sample_id=sample_id)
        self.assertEqual("furnace_table", sample.position)
        self.assertEqual("test", sample.name)

        # try to create samples with same name
        sample_id = self.sample_view.create_sample("test", position="furnace_1/inside")
        sample = self.sample_view.get_sample(sample_id=sample_id)
        self.assertEqual("furnace_1/inside", sample.position)
        self.assertEqual("test", sample.name)

        # try to create samples with non-exist positions
        with self.assertRaises(ValueError):
            self.sample_view.create_sample("test_1", position="non-exist position")

        # try to create samples with the same position
        with self.assertRaises(ValueError):
            self.sample_view.create_sample("test_2", position="furnace_table")

    def test_get_sample(self):
        # try to get a non-exist sample
        with self.assertRaises(ValueError):
            self.sample_view.get_sample(sample_id=ObjectId())

    def test_update_sample_metadata(self):
        sample_id = self.sample_view.create_sample("test_sample", position=None, metadata={"test_param": "test_value"})
        self.sample_view.update_sample_metadata(sample_id=sample_id, metadata={"test_param2": "test_value2"})
        sample = self.sample_view.get_sample(sample_id=sample_id)
        self.assertDictEqual({"test_param": "test_value", "test_param2": "test_value2"}, sample.metadata)

        # try to update a non-exist sample
        with self.assertRaises(ValueError):
            self.sample_view.update_sample_metadata(sample_id=ObjectId(), metadata={"test_param": "test_value"})

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
        self.sample_view.move_sample(
            sample_id=sample_id,
            position=self.sample_view.get_sample(sample_id).position,
        )
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

        self.assertListEqual([], self.sample_view.get_sample_positions_by_task(task_id))
        self.sample_view.lock_sample_position(task_id=task_id, position="furnace_table")

        sample_id = self.sample_view.create_sample("test")

        self.assertEqual(
            "LOCKED",
            self.sample_view.get_sample_position_status("furnace_table")[0].name,
        )
        self.assertListEqual(["furnace_table"], self.sample_view.get_sample_positions_by_task(task_id))

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
        self.assertEqual(
            "OCCUPIED",
            self.sample_view.get_sample_position_status("furnace_table")[0].name,
        )

        self.sample_view.release_sample_position("furnace_table")

        self.sample_view.move_sample(sample_id=sample_id, position=None)

        # try to lock a sample position twice with same task id
        self.sample_view.lock_sample_position(task_id, position="furnace_table")
        self.sample_view.lock_sample_position(task_id, position="furnace_table")

        self.assertEqual(
            "LOCKED",
            self.sample_view.get_sample_position_status("furnace_table")[0].name,
        )

        # try to lock a sample position with different task id
        task_id_2 = ObjectId()
        with self.assertRaises(ValueError):
            self.sample_view.lock_sample_position(task_id_2, position="furnace_table")

    def test_request_sample_position_single(self):
        task_id = ObjectId()

        with self.request_sample_positions(["furnace_table", "furnace_1/inside"], task_id) as sample_positions:
            self.assertFalse(sample_positions is None)
            for sample_position_prefix, sample_position in sample_positions.items():
                self.assertTrue(sample_position[0].startswith(sample_position_prefix))
                self.assertEqual(
                    "LOCKED",
                    self.sample_view.get_sample_position_status(sample_position[0])[0].name,
                )
                self.assertEqual(
                    task_id,
                    self.sample_view.get_sample_position_status(sample_position[0])[1],
                )

        for sample_position in sample_positions.values():
            self.assertEqual(
                "EMPTY",
                self.sample_view.get_sample_position_status(sample_position[0])[0].name,
            )
            self.assertEqual(None, self.sample_view.get_sample_position_status(sample_position[0])[1])

    def test_request_device_timeout(self):
        task_id = ObjectId()
        task_id_2 = ObjectId()

        with self.request_sample_positions(["furnace_table", "furnace_1/inside"], task_id) as sample_positions:
            self.assertFalse(sample_positions is None)
            with self.request_sample_positions(["furnace_table", "furnace_1/inside"], task_id_2) as _sample_positions:
                self.assertIs(None, _sample_positions)

    def test_request_sample_positions_twice(self):
        task_id = ObjectId()

        self.assertEqual(
            "EMPTY",
            self.sample_view.get_sample_position_status("furnace_table")[0].name,
        )
        with self.request_sample_positions(
            [
                "furnace_table",
                "furnace_1/inside",
                {"prefix": "furnace_temp", "number": 3},
            ],
            task_id,
        ):
            self.assertEqual(
                "LOCKED",
                self.sample_view.get_sample_position_status("furnace_table")[0].name,
            )
            self.assertEqual(
                "LOCKED",
                self.sample_view.get_sample_position_status("furnace_temp/1")[0].name,
            )
            with self.request_sample_positions(["furnace_table", "furnace_temp/1"], task_id) as sample_positions_:
                self.assertDictEqual(
                    {
                        "furnace_table": ["furnace_table"],
                        "furnace_temp/1": ["furnace_temp/1"],
                    },
                    sample_positions_,
                )
                self.assertEqual(
                    "LOCKED",
                    self.sample_view.get_sample_position_status("furnace_table")[0].name,
                )
                with self.request_sample_positions(["furnace_table"], task_id) as sample_positions__:
                    self.assertDictEqual({"furnace_table": ["furnace_table"]}, sample_positions__)
                    self.assertEqual(
                        "LOCKED",
                        self.sample_view.get_sample_position_status("furnace_table")[0].name,
                    )

                self.assertEqual(
                    "LOCKED",
                    self.sample_view.get_sample_position_status("furnace_table")[0].name,
                )

            self.assertEqual(
                "LOCKED",
                self.sample_view.get_sample_position_status("furnace_table")[0].name,
            )

        self.assertEqual(
            "EMPTY",
            self.sample_view.get_sample_position_status("furnace_table")[0].name,
        )
        self.assertEqual(None, self.sample_view.get_sample_position_status("furnace_table")[1])

    def test_request_sample_positions_occupied(self):
        task_id = ObjectId()
        sample_id = self.sample_view.create_sample("test", position=None)
        self.assertEqual(
            "EMPTY",
            self.sample_view.get_sample_position_status("furnace_table")[0].name,
        )
        self.sample_view.move_sample(sample_id, "furnace_table")
        self.assertEqual(
            "OCCUPIED",
            self.sample_view.get_sample_position_status("furnace_table")[0].name,
        )

        self.sample_view.update_sample_task_id(sample_id, task_id)

        with self.request_sample_positions(["furnace_table", "furnace_1/inside"], task_id):
            self.assertEqual(
                "OCCUPIED",
                self.sample_view.get_sample_position_status("furnace_table")[0].name,
            )
            self.assertEqual(task_id, self.sample_view.get_sample_position_status("furnace_table")[1])

        self.assertEqual(
            "OCCUPIED",
            self.sample_view.get_sample_position_status("furnace_table")[0].name,
        )
        self.assertEqual(None, self.sample_view.get_sample_position("furnace_table")["task_id"])

    def test_request_multiple_sample_positions(self):
        task_id = ObjectId()

        for j in range(1, 5):
            with self.request_sample_positions([{"prefix": "furnace_temp", "number": j}], task_id) as sample_positions:
                self.assertFalse(sample_positions is None)
                for sample_position_prefix, sample_position in sample_positions.items():
                    for i in range(j):
                        self.assertTrue(sample_position[i].startswith(sample_position_prefix))
                        self.assertEqual(
                            "LOCKED",
                            self.sample_view.get_sample_position_status(sample_position[i])[0].name,
                        )
                        self.assertEqual(
                            task_id,
                            self.sample_view.get_sample_position_status(sample_position[i])[1],
                        )

            for sample_position in sample_positions.values():
                for i in range(j):
                    self.assertEqual(
                        "EMPTY",
                        self.sample_view.get_sample_position_status(sample_position[i])[0].name,
                    )
                    self.assertEqual(
                        None,
                        self.sample_view.get_sample_position_status(sample_position[i])[1],
                    )

        # try when requesting sample positions more than we have in the lab
        with self.assertRaises(ValueError), self.request_sample_positions([{"prefix": "furnace_temp", "number": 5}], task_id):
            pass

    def test_request_multiple_sample_positions_multiple_tasks(self):
        task_id_1 = ObjectId()
        task_id_2 = ObjectId()

        with self.request_sample_positions([{"prefix": "furnace_temp", "number": 2}], task_id_1) as sample_positions:
            self.assertEqual(2, len(sample_positions["furnace_temp"]))
            self.assertTrue(sample_positions["furnace_temp"][0].startswith("furnace_temp"))
            self.assertTrue(sample_positions["furnace_temp"][1].startswith("furnace_temp"))
            with self.request_sample_positions([{"prefix": "furnace_temp", "number": 2}], task_id_2) as sample_positions_:
                self.assertEqual(2, len(sample_positions_["furnace_temp"]))
                self.assertTrue(sample_positions_["furnace_temp"][0].startswith("furnace_temp"))
                self.assertTrue(sample_positions_["furnace_temp"][1].startswith("furnace_temp"))
            with self.request_sample_positions([{"prefix": "furnace_temp", "number": 4}], task_id_2) as sample_positions_:
                self.assertIs(None, sample_positions_)
