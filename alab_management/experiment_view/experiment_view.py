"""
A wrapper over the ``experiment`` class.
"""

from datetime import datetime
from enum import Enum, auto
from typing import List, Any, Dict, Optional, cast, Union

from bson import ObjectId

from .experiment import InputExperiment
from ..utils.data_objects import get_collection
from alab_management.sample_view import SampleView
from alab_management.task_view import TaskView


class ExperimentStatus(Enum):
    """
    The status of experiment

    - ``PENDING``: The experiment has not been processed by experiment manager
    - ``RUNNING``: The experiment has been submitted and put in the queue
    - ``COMPLETED``: The experiment has been completed
    - ``ERROR``: The experiment has failed somewhere
    """

    PENDING = auto()
    RUNNING = auto()
    COMPLETED = auto()
    ERROR = auto()


class ExperimentView:
    """
    Experiment view manages the experiment status, which is a collection of tasks and samples
    """

    def __init__(self):
        self._experiment_collection = get_collection("experiment")
        self.sample_view = SampleView()
        self.task_view = TaskView()

    def create_experiment(self, experiment: InputExperiment) -> ObjectId:
        """
        Create an experiment in the database
        which is intended for raw experiment inserted by users. The
        lab manager will add sample id and task id for the samples and tasks

        Args:
            experiment: the required format of experiment, see also
              :py:class:`InputExperiment <alab_management.experiment_view.experiment.InputExperiment>`
        """
        # NOTE: format of experiment dict is checked in api endpoint upstream of this method

        # confirm that no task/sample id's already exist in the database. This is possible when users manually set these id's
        for sample in experiment.samples:
            if sample.sample_id is None:
                continue  # ALabOS will assign a sample id, this is always safe
            if self.sample_view.exists(sample_id=sample.sample_id):
                raise ValueError(
                    f"Sample id {sample.sample_id} already exists in the database! Please use another id. This experiment was not submitted."
                )

        for task in experiment.tasks:
            if task.task_id is None:
                continue
            if self.task_view.exists(task_id=task.task_id):
                raise ValueError(
                    f"Task id {task.task_id} already exists in the database! Please use another id. This experiment was not submitted."
                )

        # all good, lets submit the experiment into ALabOS!
        result = self._experiment_collection.insert_one(
            {
                **experiment.dict(),
                "submitted_at": datetime.now(),
                "status": ExperimentStatus.PENDING.name,
            }
        )

        return cast(ObjectId, result.inserted_id)

    def get_experiments_with_status(
        self, status: Union[str, ExperimentStatus]
    ) -> List[Dict[str, Any]]:
        """
        Filter experiments by its status
        """
        if isinstance(status, str):
            status = ExperimentStatus[status]
        return cast(
            List[Dict[str, Any]],
            self._experiment_collection.find(
                {
                    "status": status.name,
                }
            ),
        )

    def get_experiment(self, exp_id: ObjectId) -> Optional[Dict[str, Any]]:
        """
        Get an experiment by its id
        """
        experiment = self._experiment_collection.find_one({"_id": exp_id})
        if experiment is None:
            raise ValueError(f"Cannot find an experiment with id: {exp_id}")
        return experiment

    def update_experiment_status(self, exp_id: ObjectId, status: ExperimentStatus):
        """
        Update the status of an experiment
        """
        experiment = self.get_experiment(exp_id=exp_id)

        update_dict = {"status": status.name}
        if status == ExperimentStatus.COMPLETED:
            update_dict["completed_at"] = datetime.now()
        self._experiment_collection.update_one(
            {"_id": exp_id},
            {"$set": update_dict},
        )

    def update_sample_task_id(
        self, exp_id, sample_ids: List[ObjectId], task_ids: List[ObjectId]
    ):
        """
        At the creation of experiment, the id of samples and tasks has not been assigned

        Later, we will use this method to assign sample & task id (done by
        :py:class:`LabView <alab_management.lab_view.LabView>`)
        """
        experiment = self._experiment_collection.find_one({"_id": exp_id})

        if experiment is None:
            raise ValueError(f"Cannot find experiment with id: {exp_id}")

        if len(experiment["samples"]) != len(sample_ids):
            raise ValueError("Difference length of samples and input sample ids")

        if len(experiment["tasks"]) != len(task_ids):
            raise ValueError("Difference length of tasks and input task ids")

        self._experiment_collection.update_one(
            {"_id": exp_id},
            {
                "$set": {
                    **{
                        f"samples.{i}.sample_id": sample_id
                        for i, sample_id in enumerate(sample_ids)
                    },
                    **{
                        f"tasks.{j}.task_id": task_id
                        for j, task_id in enumerate(task_ids)
                    },
                }
            },
        )

    def get_experiment_by_task_id(self, task_id: ObjectId) -> Optional[Dict[str, Any]]:
        """
        Get an experiment that contains a task with the given task_id
        """
        experiment = self._experiment_collection.find_one({"tasks.task_id": task_id})
        if experiment is None:
            raise ValueError(f"Cannot find experiment containing task_id: {task_id}")
        return experiment

    def get_experiment_by_sample_id(
        self, sample_id: ObjectId
    ) -> Optional[Dict[str, Any]]:
        """
        Get an experiment that contains a sample with the given sample_id
        """
        experiment = self._experiment_collection.find_one(
            {"samples.sample_id": sample_id}
        )
        return experiment
