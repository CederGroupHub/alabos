"""
A wrapper over the ``experiment`` class.
"""

from datetime import datetime
from enum import Enum, auto
from typing import List, Any, Dict, Optional, cast, Union

from bson import ObjectId


from ..utils.data_objects import get_collection, get_completed_collection
from .experiment_view import ExperimentView
from alab_management.sample_view import SampleView, CompletedSampleView
from alab_management.task_view import TaskView, CompletedTaskView


class CompletedExperimentView:
    """
    Experiment view manages the experiment status, which is a collection of tasks and samples
    """

    def __init__(self):
        self._working_experiment_collection = get_collection("experiment")
        self._completed_experiment_collection = get_completed_collection("experiment")

        self.completed_sample_view = CompletedSampleView()
        self.completed_task_view = CompletedTaskView()

    def save_experiment(self, experiment_id: ObjectId):
        """
        Transfers an experiment from the working (standard) database to the completed database.
        This also transfers all samples and tasks associated with the experiment into the completed database.


        Args:
            experiment_id (ObjectId): id of the experiment to be transferred
        """
        experiment_dict = self._working_experiment_collection.find_one(
            ObjectId(experiment_id)
        )
        if experiment_dict is None:
            raise ValueError(
                f"Experiment with id {experiment_id} does not exist in the working database!"
            )

        for sample in experiment_dict["samples"]:
            self.completed_sample_view.save_sample(sample_id=sample["sample_id"])

        for task in experiment_dict["tasks"]:
            self.completed_task_view.save_task(task_id=task["task_id"])

        if self.exists(experiment_id):
            result = self._completed_experiment_collection.update_one(
                filter={"_id": ObjectId(experiment_id)},
                update={"$set": experiment_dict},
            )
        else:
            result = self._completed_experiment_collection.insert_one(experiment_dict)

    def save_all(self):
        """
        Saves all completed experiments in the working database to the completed database.
        """
        for experiment_dict in self._working_experiment_collection.find(
            {"status": "COMPLETED"}
        ):
            try:
                self.save_experiment(experiment_dict["_id"])
            except:
                print(f"Error saving experiment {experiment_dict['_id']}")

    def exists(self, experiment_id: Union[ObjectId, str]) -> bool:
        """Check if an experiment exists in the completed experiment database

        Args:
            experiment_id (ObjectId): id of the experiment within completed experiment collection

        Returns:
            bool: True if sample exists in the database
        """
        return (
            self._completed_experiment_collection.count_documents(
                {"_id": ObjectId(experiment_id)}
            )
            > 0
        )
