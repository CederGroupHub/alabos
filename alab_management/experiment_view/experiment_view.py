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
from .completed_experiment_view import CompletedExperimentView
from labgraph import Sample as LabgraphSample
from labgraph.errors import NotFoundInDatabaseError

completed_experiment_view = CompletedExperimentView()


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
        # add tasks to Labgraph
        # create samples in Labgraph
        # create experiment in database

        for task in experiment["tasks"]:
            task["task_id"] = ObjectId(task["task_id"])

        umbrella_sample = LabgraphSample.from_dict(experiment)
        if self.sample_view.exists(umbrella_sample.id):
            raise ValueError(
                f"Experiment id {umbrella_sample.id} already exists in the database! Please use another id. This experiment was not submitted."
            )

        if any(
            self.sample_view.exists(sample["_id"]) for sample in experiment["samples"]
        ):
            raise ValueError(
                f"Sample id already exists in the database! Please use another id. This experiment was not submitted."
            )

        umbrella_sample.tags.append("role::experiment")
        umbrella_sample["tasks"] = experiment["tasks"]
        umbrella_sample["samples"] = [
            {"sample_id": ObjectId(s["_id"]), "name": s["name"]}
            for s in experiment["samples"]
        ]
        umbrella_sample["status"]: ExperimentStatus = ExperimentStatus.PENDING.name
        exp_id = self.sample_view.add(umbrella_sample)

        for sample_dict in experiment["samples"]:
            sample_dict["node_contents"] = experiment["node_contents"]
            sample = LabgraphSample.from_dict(sample_dict)
            sample.tags.append("role::sample")
            sample["position"] = None
            sample["task_id"] = None
            self.sample_view.add(sample)

        for task in experiment["tasks"]:
            task["task_id"] = ObjectId(task["task_id"])
            # replace list index with objectid
            task["prev_tasks"] = [
                experiment["tasks"][i]["task_id"] for i in task["prev_tasks"]
            ]
            self.task_view.create_task(**task)

        return cast(ObjectId, exp_id)

    def get_experiments_with_status(
        self, status: Union[str, ExperimentStatus]
    ) -> List[LabgraphSample]:
        """
        Filter experiments by its status
        """
        if isinstance(status, str):
            status = ExperimentStatus[status]

        return self.sample_view.filter(
            {
                "tags": {"$in": ["role::experiment"]},
                "contents.status": status.name,
            }
        )
        # return cast(
        #     List[Dict[str, Any]],
        #     self._experiment_collection.find(
        #         {
        #             "status": status.name,
        #         }
        #     ),
        # )

    def get_experiment(self, exp_id: ObjectId) -> LabgraphSample:
        """
        Get an experiment by its id
        """
        experiment = self.sample_view.get(exp_id)
        return experiment

    def update_experiment_status(self, exp_id: ObjectId, status: ExperimentStatus):
        """
        Update the status of an experiment
        """
        experiment = self.get_experiment(exp_id=exp_id)
        experiment["status"] = status.name
        if status == ExperimentStatus.COMPLETED:
            experiment["completed_at"] = datetime.now()
        self.sample_view.update(experiment)

    def update_sample_task_id(
        self, exp_id, sample_ids: List[ObjectId], task_ids: List[ObjectId]
    ):
        """
        At the creation of experiment, the id of samples and tasks has not been assigned

        Later, we will use this method to assign sample & task id (done by
        :py:class:`LabView <alab_management.lab_view.LabView>`)
        """
        return  # TODO labgraph sets ids beforehand, shouldnt need this step
        # experiment = self._experiment_collection.find_one({"_id": exp_id})

        # if experiment is None:
        #     raise ValueError(f"Cannot find experiment with id: {exp_id}")

        # if len(experiment["samples"]) != len(sample_ids):
        #     raise ValueError("Difference length of samples and input sample ids")

        # if len(experiment["tasks"]) != len(task_ids):
        #     raise ValueError("Difference length of tasks and input task ids")

        # self._experiment_collection.update_one(
        #     {"_id": exp_id},
        #     {
        #         "$set": {
        #             **{
        #                 f"samples.{i}.sample_id": sample_id
        #                 for i, sample_id in enumerate(sample_ids)
        #             },
        #             **{
        #                 f"tasks.{j}.task_id": task_id
        #                 for j, task_id in enumerate(task_ids)
        #             },
        #         }
        #     },
        # )

    def get_experiment_by_task_id(self, task_id: ObjectId) -> LabgraphSample:
        """
        Get an experiment that contains a task with the given task_id
        """
        try:
            experiment = self.sample_view.filter(
                {
                    "tags": {"$in": ["role::experiment"]},
                    "contents.tasks.task_id": task_id,
                }
            )[0]
        except NotFoundInDatabaseError:
            raise ValueError(f"Cannot find experiment containing task_id: {task_id}")
        # experiment = self._experiment_collection.find_one({"tasks.task_id": task_id})
        return experiment

    def get_experiment_by_sample_id(
        self, sample_id: ObjectId
    ) -> Optional[Dict[str, Any]]:
        """
        Get an experiment that contains a sample with the given sample_id
        """
        experiment = self.sample_view.find_one(
            {
                "tags": {"$in": ["role::experiment"]},
                "contents.samples.sample_id": sample_id,
            }
        )
        return experiment
