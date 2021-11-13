import os
from pathlib import Path
from unittest import TestCase

os.environ["ALAB_CONFIG"] = (Path(__file__).parent /
                             "fake_lab" / "config.toml").as_posix()

from alab_management.task_view import TaskStatus
from alab_management.experiment_view import InputExperiment
from alab_management import ExperimentManager
from alab_management.scripts import cleanup_lab, setup_lab


class TestExperimentManager(TestCase):
    def setUp(self) -> None:
        cleanup_lab()
        setup_lab()
        self.experiment_manager = ExperimentManager()
        self.experiment_manager.sample_view._sample_collection.drop()
        self.experiment_manager.task_view._task_collection.drop()
        self.experiment_manager.experiment_view._experiment_collection.drop()

    def tearDown(self) -> None:
        cleanup_lab()
        self.experiment_manager.sample_view._sample_collection.drop()
        self.experiment_manager.task_view._task_collection.drop()
        self.experiment_manager.experiment_view._experiment_collection.drop()

    def test_handle_pending_experiments(self):
        exp_template = InputExperiment(**{
            "name": "test",
            "samples": [{"name": "test_sample"}, {"name": "test_sample_2"}],
            "tasks": [{
                "type": "Heating",
                "next_tasks": [1],
                "parameters": {
                    "p_1": 1,
                    "p_2": 2,
                },
                "samples": {
                    "sample": "test_sample"
                }
            }, {
                "type": "Heating",
                "next_tasks": [],
                "parameters": {
                    "p_1": 1,
                    "p_2": 2,
                },
                "samples": {
                    "sample": "test_sample_2"
                }
            }]
        })

        exp_id_1 = self.experiment_manager.experiment_view.create_experiment(exp_template)
        exp_id_2 = self.experiment_manager.experiment_view.create_experiment(exp_template)

        self.assertEqual("PENDING", self.experiment_manager.experiment_view.get_experiment(exp_id_1)["status"])
        self.assertEqual("PENDING", self.experiment_manager.experiment_view.get_experiment(exp_id_2)["status"])

        self.experiment_manager.handle_pending_experiments()

        self.assertEqual("RUNNING", self.experiment_manager.experiment_view.get_experiment(exp_id_1)["status"])
        self.assertEqual("RUNNING", self.experiment_manager.experiment_view.get_experiment(exp_id_2)["status"])

        exp = self.experiment_manager.experiment_view.get_experiment(exp_id_1)
        self.assertTrue(exp["samples"][0]["sample_id"] is not None)
        self.assertTrue(exp["samples"][1]["sample_id"] is not None)
        self.assertTrue(exp["tasks"][0]["task_id"] is not None)
        self.assertTrue(exp["tasks"][1]["task_id"] is not None)

        task_id_1 = exp["tasks"][0]["task_id"]
        task_id_2 = exp["tasks"][1]["task_id"]

        task_1 = self.experiment_manager.task_view.get_task(task_id_1)
        task_2 = self.experiment_manager.task_view.get_task(task_id_2)

        self.assertListEqual([task_id_2], task_1["next_tasks"])
        self.assertListEqual([task_id_1], task_2["prev_tasks"])

        self.assertEqual(exp["samples"][0]["sample_id"], task_1["samples"]["sample"])
        self.assertEqual(exp["samples"][1]["sample_id"], task_2["samples"]["sample"])

    def test_mark_completed_experiments(self):
        exp_template = InputExperiment(**{
            "name": "test",
            "samples": [{"name": "test_sample"}, {"name": "test_sample_2"}],
            "tasks": [{
                "type": "Heating",
                "next_tasks": [1],
                "parameters": {
                    "p_1": 1,
                    "p_2": 2,
                },
                "samples": {
                    "sample": "test_sample"
                }
            }, {
                "type": "Heating",
                "next_tasks": [],
                "parameters": {
                    "p_1": 1,
                    "p_2": 2,
                },
                "samples": {
                    "sample": "test_sample_2"
                }
            }]
        })

        exp_id_1 = self.experiment_manager.experiment_view.create_experiment(exp_template)
        exp_id_2 = self.experiment_manager.experiment_view.create_experiment(exp_template)

        self.experiment_manager.mark_completed_experiments()

        self.assertEqual("PENDING", self.experiment_manager.experiment_view.get_experiment(exp_id_1)["status"])
        self.assertEqual("PENDING", self.experiment_manager.experiment_view.get_experiment(exp_id_2)["status"])

        self.experiment_manager.handle_pending_experiments()
        self.experiment_manager.mark_completed_experiments()

        self.assertEqual("RUNNING", self.experiment_manager.experiment_view.get_experiment(exp_id_1)["status"])
        self.assertEqual("RUNNING", self.experiment_manager.experiment_view.get_experiment(exp_id_2)["status"])

        exp = self.experiment_manager.experiment_view.get_experiment(exp_id_1)

        task_id_1 = exp["tasks"][0]["task_id"]
        task_id_2 = exp["tasks"][1]["task_id"]

        self.experiment_manager.task_view.update_status(task_id_1, TaskStatus.COMPLETED)
        self.experiment_manager.mark_completed_experiments()

        self.assertEqual("RUNNING", self.experiment_manager.experiment_view.get_experiment(exp_id_1)["status"])
        self.assertEqual("RUNNING", self.experiment_manager.experiment_view.get_experiment(exp_id_2)["status"])

        self.experiment_manager.task_view.update_status(task_id_2, TaskStatus.COMPLETED)
        self.experiment_manager.mark_completed_experiments()

        self.assertEqual("COMPLETED", self.experiment_manager.experiment_view.get_experiment(exp_id_1)["status"])
        self.assertEqual("RUNNING", self.experiment_manager.experiment_view.get_experiment(exp_id_2)["status"])

