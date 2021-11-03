from typing import List, Any, Dict, Union

from bson import ObjectId

from alab_management.config import config
from alab_management.db import get_collection
from alab_management.experiment_view.experiment import ExperimentStatus


class ExperimentView:
    def __init__(self):
        self._experiment_collection = get_collection(config["experiment"]["experiment_collection"])

    def create_experiment(self, name: str, samples: List[str], tasks: List[Dict[str, Any]]):
        result = self._experiment_collection.insert_one({
            "name": name,
            "samples": samples,
            "tasks": tasks,
            "status": ExperimentStatus.PENDING,
        })

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
