import os
from pathlib import Path
from unittest import TestCase

from bson import ObjectId

os.environ["ALAB_CONFIG"] = (Path(__file__).parent /
                             "fake_lab" / "config.toml").as_posix()

from alab_management.task_view import TaskStatus
from alab_management import TaskView
from alab_management.scripts import cleanup_lab, setup_lab


class TestTaskView(TestCase):
    def setUp(self) -> None:
        cleanup_lab()
        setup_lab()
        self.task_view = TaskView()
        self.task_view._task_collection.drop()

    def tearDown(self) -> None:
        cleanup_lab()
        self.task_view._task_collection.drop()

    def test_create_task(self):
        task_dict = {
            "task_type": "Heating",
            "samples": {"sample": ObjectId()},
            "parameters": {"setpoints": [[10, 600]]}
        }

        task_dict_ = task_dict.copy()
        task_id = self.task_view.create_task(**task_dict_)
        task = self.task_view.get_task(task_id)
        self.assertEqual(task_dict_["task_type"], task["type"])
        self.assertDictEqual(task_dict_["samples"], task["samples"])
        self.assertDictEqual(task_dict_["parameters"], task["parameters"])
        self.assertEqual([], task["next_tasks"])
        self.assertEqual([], task["prev_tasks"])

        # test prev/next task
        task_dict_ = task_dict.copy()
        task_dict_["prev_tasks"] = None
        task_dict_["next_tasks"] = [ObjectId()]
        task_id = self.task_view.create_task(**task_dict_)
        task = self.task_view.get_task(task_id)
        self.assertListEqual([], task["prev_tasks"])
        self.assertListEqual(task_dict_["next_tasks"], task["next_tasks"])

        # test single objectId case
        task_dict_ = task_dict.copy()
        task_dict_["prev_tasks"] = ObjectId()
        task_dict_["next_tasks"] = ObjectId()
        task_id = self.task_view.create_task(**task_dict_)
        task = self.task_view.get_task(task_id)
        self.assertListEqual([task_dict_["prev_tasks"]], task["prev_tasks"])
        self.assertListEqual([task_dict_["next_tasks"]], task["next_tasks"])

        # test non exist task type
        task_dict_ = task_dict.copy()
        task_dict_["task_type"] = "NOT A TASK TYPE"
        with self.assertRaises(ValueError):
            self.task_view.create_task(**task_dict_)

    def test_get_task(self):
        non_exist_task_id = ObjectId()
        self.assertIs(None, self.task_view.get_task(non_exist_task_id))

    def test_update_status(self):
        task_dict = {
            "task_type": "Heating",
            "samples": {"sample": ObjectId()},
            "parameters": {"setpoints": [[10, 600]]}
        }
        task_id = self.task_view.create_task(**task_dict)
        task_id_2 = self.task_view.create_task(prev_tasks=task_id, **task_dict)
        self.assertIs(TaskStatus.WAITING, self.task_view.get_status(task_id=task_id))
        self.assertEqual(TaskStatus.WAITING, self.task_view.get_status(task_id_2))
        self.task_view.update_task_dependency(task_id=task_id, next_tasks=task_id_2)

        self.task_view.update_status(task_id=task_id, status=TaskStatus.READY)
        self.assertIs(TaskStatus.READY, self.task_view.get_status(task_id=task_id))

        self.task_view.update_status(task_id=task_id, status=TaskStatus.COMPLETED)
        self.assertEqual(TaskStatus.READY, self.task_view.get_status(task_id_2))

        # try non-exist task id
        fake_task_id = ObjectId()
        with self.assertRaises(ValueError):
            self.task_view.update_status(fake_task_id, TaskStatus.READY)

        with self.assertRaises(ValueError):
            self.task_view.get_status(fake_task_id)

    def test_get_ready_tasks(self):
        task_dict = {
            "task_type": "Heating",
            "samples": {"sample": ObjectId()},
            "parameters": {"setpoints": [[10, 600]]}
        }
        task_id_1 = self.task_view.create_task(**task_dict)
        task_id_2 = self.task_view.create_task(**task_dict)
        task_id_3 = self.task_view.create_task(**task_dict)

        self.task_view.update_status(task_id=task_id_1, status=TaskStatus.READY)
        self.task_view.update_status(task_id=task_id_2, status=TaskStatus.READY)
        self.task_view.update_status(task_id=task_id_3, status=TaskStatus.WAITING)

        ready_tasks = self.task_view.get_ready_tasks()

        self.assertSetEqual({task_id_1, task_id_2}, set(task["task_id"] for task in ready_tasks))
        self.assertListEqual(["Heating"] * 2, [task["type"].__name__ for task in ready_tasks])

    def test_update_task_dependency(self):
        task_dict = {
            "task_type": "Heating",
            "samples": {"sample": ObjectId()},
            "parameters": {"setpoints": [[10, 600]]}
        }
        task_id_1 = self.task_view.create_task(**task_dict)
        task_id_2 = self.task_view.create_task(**task_dict)
        task_id_3 = self.task_view.create_task(**task_dict)
        task_id_4 = self.task_view.create_task(**task_dict)
        task_id_5 = self.task_view.create_task(**task_dict)
        task_id_6 = self.task_view.create_task(**task_dict)

        # 1 -> 2 -> 3 -> 5
        #   \          /
        #      4 -> 6
        self.task_view.update_task_dependency(task_id_1, prev_tasks=[], next_tasks=[task_id_2, task_id_4])
        self.task_view.update_task_dependency(task_id_2, prev_tasks=task_id_1, next_tasks=[task_id_3])
        self.task_view.update_task_dependency(task_id_3, prev_tasks=[task_id_2], next_tasks=task_id_5)
        self.task_view.update_task_dependency(task_id_4, prev_tasks=[task_id_1], next_tasks=task_id_6)
        self.task_view.update_task_dependency(task_id_5, prev_tasks=[task_id_3, task_id_6], next_tasks=None)
        self.task_view.update_task_dependency(task_id_6, prev_tasks=task_id_4, next_tasks=[task_id_5])

        self.assertListEqual([], self.task_view.get_task(task_id_1)["prev_tasks"])
        self.assertListEqual([task_id_2, task_id_4], self.task_view.get_task(task_id_1)["next_tasks"])
        self.assertListEqual([task_id_1], self.task_view.get_task(task_id_2)["prev_tasks"])
        self.assertListEqual([task_id_3], self.task_view.get_task(task_id_2)["next_tasks"])
        self.assertListEqual([task_id_2], self.task_view.get_task(task_id_3)["prev_tasks"])
        self.assertListEqual([task_id_5], self.task_view.get_task(task_id_3)["next_tasks"])
        self.assertListEqual([task_id_1], self.task_view.get_task(task_id_4)["prev_tasks"])
        self.assertListEqual([task_id_6], self.task_view.get_task(task_id_4)["next_tasks"])
        self.assertListEqual([task_id_3, task_id_6], self.task_view.get_task(task_id_5)["prev_tasks"])
        self.assertListEqual([], self.task_view.get_task(task_id_5)["next_tasks"])
        self.assertListEqual([task_id_4], self.task_view.get_task(task_id_6)["prev_tasks"])
        self.assertListEqual([task_id_5], self.task_view.get_task(task_id_6)["next_tasks"])
