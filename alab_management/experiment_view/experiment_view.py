from enum import Enum, auto
from typing import List, Any, Dict, Optional, cast, Union

from bson import ObjectId

from ..db import get_collection
from .experiment import InputExperiment


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
        self._experiment_collection = get_collection("experiment")

    def create_experiment(self, experiment: InputExperiment) -> ObjectId:
        """
        Create an experiment in the database
        which is intended for raw experiment inserted by users. The
        lab manager will add sample id and task id for the samples and tasks

        Args:
            experiment: the required format of experiment, see also
              :py:class:`InputExperiment <alab_management.experiment_view.experiment.InputExperiment>`
        """
        # check the format of input args
        result = self._experiment_collection.insert_one({
            **experiment.dict(),
            "status": ExperimentStatus.PENDING.name,
        })

        return cast(ObjectId, result.inserted_id)

    def get_experiments_with_status(self, status: Union[str, ExperimentStatus]) -> List[Dict[str, Any]]:
        """
        Filter experiments by its status
        """
        if isinstance(status, str):
            status = ExperimentStatus[status]
        return cast(List[Dict[str, Any]], self._experiment_collection.find({"status": status.name}))

    def get_experiment(self, exp_id: ObjectId) -> Optional[Dict[str, Any]]:
        """
        Get an experiment by its id
        """
        experiment = self._experiment_collection.find_one({"_id": exp_id})
        return experiment

    def update_experiment_status(self, exp_id: ObjectId, status: ExperimentStatus):
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

        Later, we will use this method to assign sample & task id (done by
        :py:class:`LabManager <alab_management.lab_manager.LabManager>`)
        """
        experiment = self._experiment_collection.find_one({"_id": exp_id})

        if experiment is None:
            raise ValueError(f"Cannot find experiment with id: {exp_id}")

        if len(experiment["samples"]) != len(sample_ids):
            raise ValueError("Difference length of samples and input sample ids")

        if len(experiment["tasks"]) != len(task_ids):
            raise ValueError("Difference length of tasks and input task ids")

        self._experiment_collection.update_one({"_id": exp_id}, {"$set": {
            **{f"samples.{i}.sample_id": sample_id for i, sample_id in enumerate(sample_ids)},
            **{f"tasks.{j}.task_id": task_id for j, task_id in enumerate(task_ids)},
        }})
