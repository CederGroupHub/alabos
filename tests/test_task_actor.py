import subprocess
import time
import unittest
from importlib import util
from pathlib import Path

import requests
from bson import ObjectId

from alab_management.experiment_view import ExperimentView
from alab_management.scripts.cleanup_lab import cleanup_lab
from alab_management.scripts.setup_lab import setup_lab
from alab_management.task_view import TaskView
from alab_management.task_view.task import LargeResult

SUBMISSION_API = "http://127.0.0.1:8896/api/experiment/submit"


class TestTaskActor(unittest.TestCase):
    def setUp(self) -> None:
        time.sleep(0.5)
        cleanup_lab(
            all_collections=True,
            _force_i_know_its_dangerous=True,
            sim_mode=True,
            database_name="Alab_sim",
            user_confirmation="y",
        )
        setup_lab()
        self.task_view = TaskView()
        self.experiment_view = ExperimentView()
        self.main_process = subprocess.Popen(
            ["alabos", "launch", "--port", "8896"], shell=False
        )
        self.worker_process = subprocess.Popen(
            ["alabos", "launch_worker", "--processes", "8", "--threads", "16"],
            shell=False,
        )
        time.sleep(2)  # waiting for starting up

        if self.main_process.poll() is not None:
            raise RuntimeError("Main process failed to start")
        if self.worker_process.poll() is not None:
            raise RuntimeError("Worker process failed to start")

    def tearDown(self) -> None:
        self.main_process.terminate()
        self.worker_process.terminate()
        subprocess.run(
            "lsof -ti :8896 | xargs kill -9 2>/dev/null || true",
            check=False,
            shell=True,
        )
        subprocess.run(
            "ps aux | grep 'dramatiq' | grep 'alab_management.task_actor' | awk '{print $2}' | xargs -r kill",
            check=False,
            shell=True,
        )
        subprocess.run("pkill -f 'alabos launch_worker'", check=False, shell=True)
        time.sleep(5)
        cleanup_lab(
            all_collections=True,
            _force_i_know_its_dangerous=True,
            sim_mode=True,
            database_name="Alab_sim",
            user_confirmation="y",
        )

    def test_experiment_with_large_result(self):
        # run an experiment with large result
        def compose_exp(exp_name):
            return {
                "name": exp_name,
                "tags": [],
                "metadata": {},
                "samples": [{"name": "test_sample", "tags": [], "metadata": {}}],
                "tasks": [
                    {
                        "type": "Starting",
                        "prev_tasks": [],
                        "parameters": {
                            "dest": "furnace_temp",
                            "priority": 100,
                        },
                        "samples": ["test_sample"],
                    },
                    {
                        "type": "TakePicture",
                        "prev_tasks": [0],
                        "parameters": {},
                        "samples": ["test_sample"],
                    },
                ],
            }

        exp_name = "Experiment with large result"
        experiment = compose_exp(exp_name)
        resp = requests.post(SUBMISSION_API, json=experiment)
        resp_json = resp.json()
        exp_id = ObjectId(resp_json["data"]["exp_id"])
        self.assertTrue("success", resp_json["status"])
        time.sleep(15)
        # check if large result is stored successfully in database and can be retrieved
        ## get the experiment
        experiment = self.experiment_view.get_experiment(exp_id)
        ## get the task
        tasks = experiment["tasks"]
        ## find the task with type "TakePicture"
        task_id = next(
            task["task_id"] for task in tasks if task["type"] == "TakePicture"
        )
        task = self.task_view.get_task(task_id)
        ## check if the result is stored correctly
        self.assertTrue(task["result"]["picture"]["local_path"] is not None)
        self.assertTrue(task["result"]["picture"]["storage_type"] == "gridfs")
        self.assertTrue(task["result"]["picture"]["identifier"] is not None)
        self.assertTrue(task["result"]["picture"]["file_like_data"] is None)
        # try to retrieve the large result
        self.assertTrue(LargeResult(**task["result"]["picture"]).check_if_stored())
        # read the zip file
        file_path = (
            Path(
                util.find_spec("alab_management").origin.split("__init__.py")[0]
            ).parent
            / "tests"
            / "fake_lab"
            / "large_file_example.zip"
        )
        with open(file_path, "rb") as f:
            file_content = f.read()
        self.assertEqual(
            LargeResult(**task["result"]["picture"]).retrieve(), file_content
        )

    def test_no_specification(self):
        # run an experiment with large result
        def compose_exp(exp_name):
            return {
                "name": exp_name,
                "tags": [],
                "metadata": {},
                "samples": [{"name": "test_sample", "tags": [], "metadata": {}}],
                "tasks": [
                    {
                        "type": "Starting",
                        "prev_tasks": [],
                        "parameters": {
                            "dest": "furnace_temp",
                        },
                        "samples": ["test_sample"],
                    },
                    {
                        "type": "TakePictureWithoutSpecifiedResult",
                        "prev_tasks": [0],
                        "parameters": {},
                        "samples": ["test_sample"],
                    },
                ],
            }

        exp_name = "Experiment with large result"
        experiment = compose_exp(exp_name)
        resp = requests.post(SUBMISSION_API, json=experiment)
        resp_json = resp.json()
        exp_id = ObjectId(resp_json["data"]["exp_id"])
        self.assertTrue("success", resp_json["status"])
        time.sleep(15)
        # check if large result is stored successfully in database and can be retrieved
        ## get the experiment
        experiment = self.experiment_view.get_experiment(exp_id)
        ## get the task
        tasks = experiment["tasks"]
        ## find the task with type "TakePicture"
        task_id = next(
            task["task_id"]
            for task in tasks
            if task["type"] == "TakePictureWithoutSpecifiedResult"
        )
        task = self.task_view.get_task(task_id)
        ## check if the result is stored correctly
        self.assertTrue(task["result"]["picture"]["local_path"] is not None)
        self.assertTrue(task["result"]["picture"]["storage_type"] == "gridfs")
        self.assertTrue(task["result"]["picture"]["identifier"] is not None)
        self.assertTrue(task["result"]["picture"]["file_like_data"] is None)
        # try to retrieve the large result
        self.assertTrue(LargeResult(**task["result"]["picture"]).check_if_stored())
        # read the zip file
        file_path = (
            Path(
                util.find_spec("alab_management").origin.split("__init__.py")[0]
            ).parent
            / "tests"
            / "fake_lab"
            / "large_file_example.zip"
        )
        with open(file_path, "rb") as f:
            file_content = f.read()
        self.assertEqual(
            LargeResult(**task["result"]["picture"]).retrieve(), file_content
        )

    def test_incorrect_schema(self):
        # check if the result is not consistent with the schema
        ## run an experiment with large result
        def compose_exp(exp_name):
            return {
                "name": exp_name,
                "tags": [],
                "metadata": {},
                "samples": [{"name": "test_sample", "tags": [], "metadata": {}}],
                "tasks": [
                    {
                        "type": "Starting",
                        "prev_tasks": [],
                        "parameters": {
                            "dest": "furnace_temp",
                        },
                        "samples": ["test_sample"],
                    },
                    {
                        "type": "TakePictureMissingResult",
                        "prev_tasks": [0],
                        "parameters": {},
                        "samples": ["test_sample"],
                    },
                ],
            }

        exp_name = "Experiment with large result"
        experiment = compose_exp(exp_name)
        resp = requests.post(SUBMISSION_API, json=experiment)
        resp_json = resp.json()
        exp_id = ObjectId(resp_json["data"]["exp_id"])
        self.assertTrue("success", resp_json["status"])
        time.sleep(15)
        # check no exception is raised if the schema is not correct
        ## get the experiment
        experiment = self.experiment_view.get_experiment(exp_id)
        ## get the task
        tasks = experiment["tasks"]
        ## find the task with type "TakePictureMissingResult"
        task_id = next(
            task["task_id"]
            for task in tasks
            if task["type"] == "TakePictureMissingResult"
        )
        task = self.task_view.get_task(task_id)
        ## check if the result is still stored correctly
        self.assertTrue(task["result"]["timestamp"] is not None)
        self.assertSetEqual(set(task["result"].keys()), {"timestamp"})
        ## check that the task is completed
        self.assertEqual(task["status"], "COMPLETED")
