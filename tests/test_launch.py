import time
import unittest
from multiprocessing import Process

import requests
from bson import ObjectId

from alab_management.experiment_view import ExperimentView
from alab_management.scripts.cleanup_lab import cleanup_lab
from alab_management.scripts.launch_lab import launch_dashboard, \
    launch_experiment_manager, launch_executor
from alab_management.scripts.setup_lab import setup_lab
from alab_management.task_view import TaskView


class TestLaunch(unittest.TestCase):
    def setUp(self) -> None:
        cleanup_lab(all_collections=True, _force_i_know_its_dangerous=True)
        setup_lab()
        self.task_view = TaskView()
        self.experiment_view = ExperimentView()
        self.dashboard_process = Process(target=launch_dashboard, args=("127.0.0.1", 8896, False))
        self.experiment_manager_process = Process(target=launch_experiment_manager)
        self.executor_process = Process(target=launch_executor)
        self.dashboard_process.start()
        self.experiment_manager_process.start()
        self.executor_process.start()
        time.sleep(5)  # waiting for starting up

    def tearDown(self) -> None:
        self.dashboard_process.terminate()
        self.experiment_manager_process.terminate()
        self.executor_process.terminate()
        self.dashboard_process.join()
        self.experiment_manager_process.join()
        self.executor_process.join()
        cleanup_lab(all_collections=True, _force_i_know_its_dangerous=True)

    def test_submit_experiment(self):
        experiment = {
            "name": "test",
            "samples": [{"name": "test_sample"}],
            "tasks": [{
                "type": "Starting",
                "next_tasks": [1],
                "parameters": {
                    "dest": "furnace_table",
                },
                "samples": {
                    "sample": "test_sample",
                }
            }, {
                "type": "Heating",
                "next_tasks": [2],
                "parameters": {
                    "setpoints": ((1, 2),),
                },
                "samples": {
                    "sample": "test_sample",
                }
            }, {
                "type": "Ending",
                "next_tasks": [],
                "parameters": {},
                "samples": {
                    "sample": "test_sample",
                }
            }]
        }

        resp = requests.post("http://127.0.0.1:8896/api/experiment/submit", json=experiment)
        resp_json = resp.json()
        exp_id = ObjectId(resp_json["data"]["exp_id"])
        self.assertTrue("success", resp_json["status"])
        time.sleep(10)
        self.assertTrue(all(task["status"] == "COMPLETED"
                            for task in self.task_view._task_collection.find()))
        self.assertEqual("COMPLETED", self.experiment_view.get_experiment(exp_id)["status"])
