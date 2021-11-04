from enum import Enum, auto
from typing import List, Any, Dict, Optional

from bson import ObjectId

from alab_management.config import config
from alab_management.db import get_collection
from alab_management.experiment_view.experiment import Experiment


class ExperimentStatus(Enum):
    """
    The status of experiment

    - ``PENDING``: The experiment has not been processed by experiment manager
    - ``RUNNING``: The experiment has been submitted and put in the queue
    - ``COMPLETED``: The experiment has been completed
    """
    PENDING = auto()
    RUNNING = auto()
    COMPLETED = auto()


class ExperimentView:
    """
    Experiment view manages the experiment status, which is a collection of tasks and samples
    """
    def __init__(self):
        self._experiment_collection = get_collection(config["experiment"]["experiment_collection"])

    def create_experiment(self, experiment: Experiment) -> ObjectId:
        """
        Create an experiment in the database
        Args:
            experiment: the experiment object
        """
        result = self._experiment_collection.insert_one(experiment.dict())

        return result.inserted_id

    def get_experiments_with_status(self, status: ExperimentStatus) -> List[Dict[str, Any]]:
        """
        Filter experiments by its status
        """
        return self._experiment_collection.find({"status": status.name})

    def get_experiment(self, exp_id: ObjectId) -> Optional[Dict[str, Any]]:
        """
        Get an experiment by its id
        """
        experiment = self._experiment_collection.find_one({"_id": exp_id})
        return experiment

    def set_experiment_status(self, exp_id: ObjectId, status: ExperimentStatus):
        """
        Update the status of a experiment
        """
        experiment = self._experiment_collection.find_one({"_id": exp_id})

        if experiment is None:
            raise ValueError(f"Cannot find experiment with id: {exp_id}")

        self._experiment_collection.update_one({"_id": exp_id}, {"$set": {
            "status": status.name,
        }})

    def update_sample_task_id(self, exp_id, sample_ids: List[ObjectId],
                              task_ids: List[ObjectId]):
        """
        At the creation of experiment, the id of samples and tasks has not been assigned

        Later, we will use this method to assign sample & task id
        """
        experiment = self._experiment_collection.find_one({"_id": exp_id})

        if experiment is None:
            raise ValueError(f"Cannot find experiment with id: {exp_id}")

        self._experiment_collection.update_one({"_id": exp_id}, {"$set": {
            **{f"samples.{i}.sample_id": sample_id for i, sample_id in enumerate(sample_ids)},
            **{f"tasks.{j}.task_id": task_id for j, task_id in enumerate(task_ids)},
        }})
