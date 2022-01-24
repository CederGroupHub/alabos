from unittest import TestCase

from bson import ObjectId

from alab_management.experiment_view import ExperimentView, InputExperiment, ExperimentStatus
from alab_management.scripts.cleanup_lab import cleanup_lab
from alab_management.scripts.setup_lab import setup_lab


class TestExperimentView(TestCase):
    def setUp(self) -> None:
        cleanup_lab()
        setup_lab()
        self.experiment_view = ExperimentView()
        self.experiment_collection = self.experiment_view._experiment_collection
        self.experiment_collection.drop()

    def tearDown(self) -> None:
        cleanup_lab()
        self.experiment_collection.drop()

    def test_create_experiment(self):
        exp_template = InputExperiment(**{
            "name": "test",
            "samples": [{"name": "test_sample"}],
            "tasks": [{
                "type": "Heating",
                "prev_tasks": [],
                "parameters": {
                    "p_1": 1,
                    "p_2": 2,
                },
                "samples": {
                    "sample": "test_sample"
                }
            }]
        })
        exp_id = self.experiment_view.create_experiment(exp_template)
        exp = self.experiment_view.get_experiment(exp_id)

        exp_dict = exp_template.dict()
        exp_dict["_id"] = exp_id
        exp_dict["status"] = "PENDING"

        self.assertDictEqual(exp_dict, exp)

    def test_get_experiment(self):
        # try non exist exp id
        self.assertIs(None, self.experiment_view.get_experiment(ObjectId()))

    def test_update_experiment_with_status(self):
        exp_template = InputExperiment(**{
            "name": "test",
            "samples": [{"name": "test_sample"}],
            "tasks": [{
                "type": "Heating",
                "prev_tasks": [],
                "parameters": {
                    "p_1": 1,
                    "p_2": 2,
                },
                "samples": {
                    "sample": "test_sample"
                }
            }]
        })

        exp_id = self.experiment_view.create_experiment(exp_template)
        self.assertEqual("PENDING", self.experiment_view.get_experiment(exp_id)["status"])

        self.experiment_view.update_experiment_status(exp_id, ExperimentStatus.RUNNING)
        self.assertEqual("RUNNING", self.experiment_view.get_experiment(exp_id)["status"])

        # try non exist exp id
        with self.assertRaises(ValueError):
            self.experiment_view.update_experiment_status(ObjectId(), ExperimentStatus.RUNNING)

    def test_get_experiments_with_status(self):
        exp_template = InputExperiment(**{
            "name": "test",
            "samples": [{"name": "test_sample"}],
            "tasks": [{
                "type": "Heating",
                "prev_tasks": [],
                "parameters": {
                    "p_1": 1,
                    "p_2": 2,
                },
                "samples": {
                    "sample": "test_sample"
                }
            }]
        })

        exp_id_1 = self.experiment_view.create_experiment(exp_template)
        exp_id_2 = self.experiment_view.create_experiment(exp_template)
        exp_id_3 = self.experiment_view.create_experiment(exp_template)

        self.assertListEqual(
            [exp_id_1, exp_id_2, exp_id_3],
            [exp["_id"] for exp in self.experiment_view.get_experiments_with_status(ExperimentStatus.PENDING)]
        )

        self.experiment_view.update_experiment_status(exp_id_1, ExperimentStatus.RUNNING)
        self.experiment_view.update_experiment_status(exp_id_2, ExperimentStatus.RUNNING)

        self.assertListEqual(
            [exp_id_1, exp_id_2],
            [exp["_id"] for exp in self.experiment_view.get_experiments_with_status(ExperimentStatus.RUNNING)]
        )

        self.experiment_view.update_experiment_status(exp_id_1, ExperimentStatus.COMPLETED)
        self.assertListEqual(
            [exp_id_1],
            [exp["_id"] for exp in self.experiment_view.get_experiments_with_status(ExperimentStatus.COMPLETED)]
        )

    def test_update_sample_task_id(self):
        sample_ids = [ObjectId()]
        task_ids = [ObjectId()]
        exp_template = InputExperiment(**{
            "name": "test",
            "samples": [{"name": "test_sample"}],
            "tasks": [{
                "type": "Heating",
                "prev_tasks": [],
                "parameters": {
                    "p_1": 1,
                    "p_2": 2,
                },
                "samples": {
                    "sample": "test_sample"
                }
            }]
        })

        exp_id = self.experiment_view.create_experiment(exp_template)
        self.experiment_view.update_sample_task_id(exp_id, sample_ids, task_ids)
        self.assertListEqual(sample_ids, [sample["sample_id"]
                                          for sample in self.experiment_view.get_experiment(exp_id)["samples"]])
        self.assertListEqual(task_ids, [sample["task_id"]
                                        for sample in self.experiment_view.get_experiment(exp_id)["tasks"]])

        # try different length task ids
        exp_id = self.experiment_view.create_experiment(exp_template)
        with self.assertRaises(ValueError):
            self.experiment_view.update_sample_task_id(exp_id, sample_ids, [ObjectId() for _ in range(2)])

        # try different length sample ids
        exp_id = self.experiment_view.create_experiment(exp_template)
        with self.assertRaises(ValueError):
            self.experiment_view.update_sample_task_id(exp_id, [ObjectId() for _ in range(2)], task_ids)

        # try non exist exp id
        with self.assertRaises(ValueError):
            self.experiment_view.update_sample_task_id(ObjectId(), sample_ids, task_ids)
