import os
from pathlib import Path
from unittest import TestCase

os.environ["ALAB_CONFIG"] = (Path(__file__).parent.parent /
                             "examples" / "fake_lab" / "config.toml").as_posix()

from alab_management import setup_lab, cleanup_lab
from alab_management.experiment_view import ExperimentView, InputExperiment


class TestExperimentView(TestCase):
    def setUp(self) -> None:
        cleanup_lab()
        setup_lab()
        self.experiment_view = ExperimentView()
        self.experiment_collection = self.experiment_view._experiment_collection

    def tearDown(self) -> None:
        cleanup_lab()
        self.experiment_collection.drop()

    def test_create_experiment(self):
        exp_template = InputExperiment(**{
            "name": "test",
            "samples": [{"name": "test_sample"}],
            "tasks": [{
                "type": "Heating",
                "parameters": {
                    "p_1": 1,
                    "p_2": 2,
                },
                "samples": {
                    "sample": "test_sample"
                }
            }]
        })

        exp_id = self.experiment_view.create_experiment(exp_template.copy())
        exp = self.experiment_view.get_experiment(exp_id)

        exp_dict = exp_template.dict()
        exp_dict["_id"] = exp_id
        exp_dict["status"] = "PENDING"

        self.assertDictEqual(exp_dict, exp)
