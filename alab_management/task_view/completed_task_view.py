from typing import cast, Union
from bson import ObjectId

from ..utils.data_objects import get_collection, get_completed_collection


class CompletedTaskView:
    def __init__(self):
        self._working_task_collection = get_collection("tasks")
        self._completed_task_collection = get_completed_collection("tasks")

    def save_task(self, task_id: ObjectId):
        """
        Saves a task dictionary to the completed database. This should be copying a task from
        the working database to the completed database.
        """
        # if self.exists(task_id):
        #     raise ValueError(
        #         f"Sample with id {task_id} already exists in the completed database!"
        #     )

        task_dict = self._working_task_collection.find_one({"_id": ObjectId(task_id)})
        if task_dict is None:
            raise ValueError(
                f"Sample with id {task_id} does not exist in the database!"
            )
        if self.exists(task_id):
            result = self._completed_task_collection.update_one(
                filter={"_id": ObjectId(task_id)},
                update={"$set": task_dict},
                upsert=True,
            )
        else:
            result = self._completed_task_collection.insert_one(task_dict)

    def exists(self, task_id: Union[ObjectId, str]) -> bool:
        """
        Check if a task exists in the database

        Args:
            task_id (Union[ObjectId, str]): id of the task within task collection.
              If a string is passed, it will be converted to ObjectId

        Returns:
            True if task exists in the database
        """
        return (
            self._completed_task_collection.count_documents({"_id": ObjectId(task_id)})
            > 0
        )

    def get_task(self, task_id: ObjectId):
        """
        Get a task from the database
        """
        task_dict = self._completed_task_collection.find_one({"_id": ObjectId(task_id)})
        if task_dict is None:
            raise ValueError(
                f"Task with id {task_id} does not exist in the completed task database!"
            )

        return task_dict
