from enum import Enum, auto
from typing import List, Any, Dict

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
    def __init__(self):
        self._experiment_collection = get_collection(config["experiment"]["experiment_collection"])

    def create_experiment(self, name: str, samples: List[str], tasks: List[Dict[str, Any]]):
        """
        Create an experiment in the database
        Args:
            name: the name of current experiment
            samples: list of sample names that will be handled in the experiment
            tasks: the list of tasks that are included in this experiment, which should have
                strucutre: {"task_id": ``ObjectId``, "parameters": ``Dict[str, Any]``, "samples": ``List[str]``,
                "type": ``str``}

        Returns:

        """

        # first validate the format of Experiment
        exp = Experiment(**{
            "name": name,
            "samples": [{"name": sample_name} for sample_name in samples],
            "tasks": tasks,
            "status": ExperimentStatus.PENDING.name,
        })
        result = self._experiment_collection.insert_one(exp.dict())

        return result.inserted_id

    def get_experiments_with_status(self, status: ExperimentStatus) -> List[Dict[str, Any]]:
        return self._experiment_collection.find({"status": status.name})

    def get_experiment(self, exp_id: ObjectId) -> Dict[str, Any]:
        experiment = self._experiment_collection.find_one({"_id": exp_id})

        if experiment is None:
            raise ValueError(f"Cannot find experiment with id: {exp_id}")

        return experiment

    def set_experiment_status(self, exp_id: ObjectId, status: ExperimentStatus):
        experiment = self._experiment_collection.find_one({"_id": exp_id})

        if experiment is None:
            raise ValueError(f"Cannot find experiment with id: {exp_id}")

        self._experiment_collection.update_one({"_id": exp_id}, {"$set": {
            "status": status.name,
        }})

    def assign_sample_task_id(self, exp_id, sample_ids: List[ObjectId],
                              task_ids: List[ObjectId]):
        experiment = self._experiment_collection.find_one({"_id": exp_id})

        if experiment is None:
            raise ValueError(f"Cannot find experiment with id: {exp_id}")

        self._experiment_collection.update_one({"_id": exp_id}, {"$set": {
            **{f"samples.{i}.sample_id": sample_id for i, sample_id in enumerate(sample_ids)},
            **{f"tasks.{j}.task_id": task_id for j, task_id in enumerate(task_ids)},
        }})
