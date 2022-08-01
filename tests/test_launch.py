import subprocess
import time
import unittest

import requests
from bson import ObjectId

from alab_management.experiment_view import ExperimentView
from alab_management.scripts.cleanup_lab import cleanup_lab
from alab_management.scripts.setup_lab import setup_lab
from alab_management.task_view import TaskView


class TestLaunch(unittest.TestCase):
    def setUp(self) -> None:
        time.sleep(2)
        cleanup_lab(all_collections=True, _force_i_know_its_dangerous=True)
        setup_lab()
        self.task_view = TaskView()
        self.experiment_view = ExperimentView()
        self.main_process = subprocess.Popen(["alabos", "launch", "--port", "8896"])
        self.worker_process = subprocess.Popen(
            ["alabos", "launch_worker", "--processes", "4", "--threads", "1"]
        )
        time.sleep(5)  # waiting for starting up

    def tearDown(self) -> None:
        self.main_process.terminate()
        self.worker_process.terminate()
        cleanup_lab(all_collections=True, _force_i_know_its_dangerous=True)

    def test_submit_experiment(self):
        experiment = {
            "name": "test",
            "samples": [{"name": "test_sample"}],
            "tasks": [
                {
                    "type": "Starting",
                    "prev_tasks": [],
                    "parameters": {
                        "dest": "furnace_table",
                    },
                    "samples": ["test_sample"],
                },
                {
                    "type": "Heating",
                    "prev_tasks": [0],
                    "parameters": {
                        "setpoints": ((1, 2),),
                    },
                    "samples": ["test_sample"],
                },
                {
                    "type": "Ending",
                    "prev_tasks": [1],
                    "parameters": {},
                    "samples": ["test_sample"],
                },
            ],
        }
        exp_ids = []
        for _ in range(3):
            resp = requests.post(
                "http://127.0.0.1:8896/api/experiment/submit", json=experiment
            )
            resp_json = resp.json()
            exp_id = ObjectId(resp_json["data"]["exp_id"])
            self.assertTrue("success", resp_json["status"])
            exp_ids.append(exp_id)
            time.sleep(3)
        time.sleep(5)
        self.assertEqual(9, self.task_view._task_collection.count_documents({}))
        self.assertTrue(
            all(
                task["status"] == "COMPLETED"
                for task in self.task_view._task_collection.find()
            )
        )
        self.assertTrue(
            all(
                task["result"] == task["_id"]
                for task in self.task_view._task_collection.find()
            )
        )

        for exp_id in exp_ids:
            self.assertEqual(
                "COMPLETED", self.experiment_view.get_experiment(exp_id)["status"]
            )
