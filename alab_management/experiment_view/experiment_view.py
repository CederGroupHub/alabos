"""
A wrapper over the ``experiment`` class.
"""

from datetime import datetime
from enum import Enum, auto
from typing import List, Any, Dict, Optional, cast, Union

from bson import ObjectId

from .experiment import InputExperiment
from ..utils.data_objects import get_collection, get_labgraph_mongodb
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
        self._experiment_collection = get_collection("experiments")
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

        if any(
            self.sample_view.exists(sample["_id"]) for sample in experiment["samples"]
        ):
            raise ValueError(
                f"Sample id already exists in the database! Please use another id. This experiment was not submitted."
            )

        if self._experiment_collection.count_documents({"_id": experiment["_id"]}) > 0:
            raise ValueError(
                f"Experiment id already exists in the database! Please use another id. This experiment was not submitted."
            )

        sample_objects = []
        sample_list = []
        sample_name_to_id = {}
        for sample_dict in experiment["samples"]:
            sample_dict["node_contents"] = experiment["node_contents"]
            sample = LabgraphSample.from_dict(
                sample_dict, labgraph_mongodb_instance=get_labgraph_mongodb()
            )
            sample["experiment_info"] = {
                "name": experiment["name"],
                "experiment_id": ObjectId(experiment["_id"]),
                "description": experiment["description"],
            }
            sample["position"] = None
            sample["task_id"] = None
            sample_objects.append(sample)
            sample_list.append(
                {
                    "sample_id": sample.id,
                    "name": sample.name,
                }
            )
            sample_name_to_id[sample.name] = sample.id

        self.sample_view.add_many_samples(sample_objects)
        for task in experiment["tasks"]:
            task["prev_tasks"] = [
                ObjectId(experiment["tasks"][idx]["task_id"])
                for idx in task["prev_tasks"]
            ]
            task["samples"] = [
                {"name": sample_name, "sample_id": sample_name_to_id[sample_name]}
                for sample_name in task["samples"]
            ]
            task["task_id"] = ObjectId(task["task_id"])
            self.task_view.create_task(**task)
        now = datetime.now()
        exp_id = self._experiment_collection.insert_one(
            {
                "_id": ObjectId(experiment["_id"]),
                "name": experiment["name"],
                "description": experiment["description"],
                "tags": experiment["tags"],
                "tasks": experiment["tasks"],
                "samples": sample_list,
                "metadata": experiment["contents"],
                "status": ExperimentStatus.PENDING.name,
                "created_at": now,
                "updated_at": now,
            }
        )
        return cast(ObjectId, exp_id.inserted_id)

    def get_experiments_with_status(
        self, status: Union[str, ExperimentStatus]
    ) -> Dict[str, Any]:
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

    def get_experiment(self, exp_id: ObjectId) -> Dict[str, Any]:
        """
        Get an experiment by its id
        """
        experiment = self._experiment_collection.find_one({"_id": ObjectId(exp_id)})
        return experiment

    def start_experiment_for_the_first_time(self, exp_id: ObjectId):
        """
        Start an experiment for the first time. This method will update the status of
        the experiment to ``RUNNING`` and set the ``started_at`` field to the current time.

        This is made distinct from `self.update_experiment_status` in case we later implement experiment PAUSE/RUNNING.
        """
        self._experiment_collection.update_one(
            {"_id": ObjectId(exp_id)},
            {
                "$set": {
                    "status": ExperimentStatus.RUNNING.name,
                    "started_at": datetime.now(),
                }
            },
        )

    def update_experiment_status(self, exp_id: ObjectId, status: ExperimentStatus):
        """
        Update the status of an experiment
        """
        update_dict = {
            "status": status.name,
            "updated_at": datetime.now(),
        }

        if status == ExperimentStatus.COMPLETED:
            update_dict["completed_at"] = datetime.now()

        self._experiment_collection.update_one(
            {"_id": ObjectId(exp_id)}, {"$set": update_dict}
        )

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

    def get_experiment_by_task_id(self, task_id: ObjectId) -> Dict[str, Any]:
        """
        Get an experiment that contains a task with the given task_id
        """
        result = self._experiment_collection.find_one(
            {"tasks.task_id": ObjectId(task_id)}
        )
        if result is None:
            raise ValueError(f"Cannot find experiment containing task_id: {task_id}")
        return result

    def get_experiment_by_sample_id(
        self, sample_id: ObjectId
    ) -> Optional[Dict[str, Any]]:
        """
        Get an experiment that contains a sample with the given sample_id
        """
        result = self._experiment_collection.find_one(
            {"samples.sample_id": ObjectId(sample_id)}
        )
        if result is None:
            raise ValueError(
                f"Cannot find experiment containing sample_id: {sample_id}"
            )
        return result
