"""
Tasks view is a convienent wrapper over the ``tasks`` collection in the database. It
provides some convenience methods to query and manipulate the tasks collection.
"""

from datetime import datetime
from enum import Enum, auto
from typing import Any, Dict, List, Type, Union, Optional, cast

from bson import ObjectId
import bson
import numpy as np

from alab_management.task_view.task import get_all_tasks, BaseTask
from alab_management.utils.data_objects import get_collection, make_bsonable, get_lock
from alab_management.task_view.task_enums import TaskStatus
from .completed_task_view import CompletedTaskView

completed_task_view = CompletedTaskView()


class TaskView:
    """
    Task view manages the status, parameters of a task
    """

    def __init__(self):
        self._task_collection = get_collection("tasks")
        self._lock = get_lock("tasks")
        self._tasks_definition: Dict[str, Type[BaseTask]] = get_all_tasks()

    def create_task(
        self,
        task_type: str,
        samples: List[ObjectId],
        parameters: Dict[str, Any],
        prev_tasks: Optional[Union[ObjectId, List[ObjectId]]] = None,
        next_tasks: Optional[Union[ObjectId, List[ObjectId]]] = None,
        task_id: Optional[ObjectId] = None,
    ) -> ObjectId:
        """
        Insert a task into the task collection

        Args:
            task_type: the type of task, which should be a type name of class inherited from
              :py:class:`BaseTask <alab_management.task_view.task.BaseTask>`
            samples: the samples that this task will handle, which will be passed to Task object
              the same as parameters.
            parameters: the required tasks for this task
            prev_tasks: one or a list of ObjectId that refer to prev tasks of this task
              (which must be completed before current task)
            next_tasks: one or a list of ObjectId that refer to next tasks of this task
              (which cannot start until this task finishes)

        Returns:
            the assigned id for this task
        """
        if task_type not in self._tasks_definition:
            raise ValueError(f"Unsupported task type: {task_type}")

        prev_tasks = prev_tasks or []
        prev_tasks = prev_tasks if isinstance(prev_tasks, list) else [prev_tasks]
        next_tasks = next_tasks or []
        next_tasks = next_tasks if isinstance(next_tasks, list) else [next_tasks]

        for related_task_id in prev_tasks + next_tasks:
            self.get_task(task_id=related_task_id)  # will raise error if not found

        entry = {
            "type": task_type,
            "status": TaskStatus.WAITING.name,
            "samples": samples,
            "parameters": parameters,
            "prev_tasks": prev_tasks,
            "next_tasks": next_tasks,
            "created_at": datetime.now(),
            "last_updated": datetime.now(),
            "message": "",
        }
        if isinstance(task_id, ObjectId):
            entry["_id"] = task_id
        result = self._task_collection.insert_one(entry)

        return cast(ObjectId, result.inserted_id)

    def create_subtask(
        self, task_id, subtask_type, samples: List[str], parameters: dict
    ):
        """
        Create a subtask entry for a task.
        """
        task = self.get_task(task_id=task_id)
        subtask_id = ObjectId()

        subtasks = task.get("subtasks", [])
        subtasks.append(
            {
                "subtask_id": subtask_id,
                "type": subtask_type,
                "samples": samples,
                "status": TaskStatus.INITIATED.name,
                "parameters": parameters,
                "created_at": datetime.now(),
                "last_updated": datetime.now(),
            }
        )

        self._task_collection.update_one(
            {"_id": task_id},
            {
                "$set": {
                    "subtasks": subtasks,
                    "last_updated": datetime.now(),
                }
            },
        )
        return subtask_id

    def get_task(self, task_id: ObjectId, encode: bool = False) -> Dict[str, Any]:
        """
        Get a task by its task id, which will return all the info stored in the database

        Args:
            task_id: the task_id of interest. If not found, will return ``None``
            encode: whether to encode the task using ``self.encode_task`` method
        """
        result = self._task_collection.find_one({"_id": task_id})

        if result is None:
            # try to get a completed task entry
            try:
                result = completed_task_view.get_task(task_id=task_id)
            except ValueError:
                result = None  # couldn't find it here either

        if result is None:
            raise ValueError(f"No task exists with provided task id: {task_id}")

        if encode:
            result = self.encode_task(result)
        return result

    def get_task_with_sample(self, sample_id: ObjectId) -> Optional[Dict[str, Any]]:
        """
        Get a task that contains the sample with the provided id
        """
        result = self._task_collection.find({"samples.sample_id": sample_id})
        if result is None:
            raise ValueError(
                f"No task exists containing provided sample id: {sample_id}"
            )
        return list(result)

    def get_status(self, task_id: ObjectId) -> TaskStatus:
        """
        Get the status of a task
        """
        task = self.get_task(task_id=task_id)
        return TaskStatus[task["status"]]

    def update_status(self, task_id: ObjectId, status: TaskStatus):
        """
        Update the status of one task

        If the status is ``COMPLETED``, we will also try to
        mark its next tasks to ``READY``, if all of its previous
        tasks are completed.

        Args:
            task_id: the id of task to be updated
            status: the new status of the task
        """
        task = self.get_task(task_id=task_id, encode=False)

        update_dict = {
            "status": status.name,
            "last_updated": datetime.now(),
        }
        if status == TaskStatus.RUNNING and "started_at" not in task:
            update_dict["started_at"] = datetime.now()
        elif status == TaskStatus.COMPLETED:
            update_dict["completed_at"] = datetime.now()

        self._task_collection.update_one(
            {"_id": task_id},
            {"$set": update_dict},
        )

        if status is TaskStatus.COMPLETED:
            # try to figure out tasks that is READY
            for next_task_id in task["next_tasks"]:
                self.try_to_mark_task_ready(task_id=next_task_id)

        if status in [TaskStatus.CANCELLED, TaskStatus.ERROR]:
            # any downstream tasks should be:
            # 1. cancelled if they depend _only on this task_
            # 2. made independent of this task. This includes removing affected samples from the downstream task
            samples_in_this_task = [s["sample_id"] for s in task["samples"]]
            for next_task_id in task["next_tasks"]:
                next_task = self.get_task(task_id=next_task_id, encode=False)
                if len(next_task["prev_tasks"]) == 1:
                    self.update_status(
                        task_id=next_task_id, status=TaskStatus.CANCELLED
                    )
                    self.set_message(
                        task_id=next_task_id,
                        message="Cancelled due to an upstream task being cancelled or throwing an error.",
                    )
                else:
                    # drop any samples that were lost in the cancelled task
                    samples_to_remain_in_downstream_task = [
                        entry
                        for entry in next_task["samples"]
                        if entry["sample_id"] not in samples_in_this_task
                    ]
                    if len(samples_to_remain_in_downstream_task) == 0:
                        # This is probably impossible (if we have 0 samples remaining,this task should exclusive depends on the cancelled task and have been caught above), but just in case...
                        self.update_status(
                            task_id=next_task_id, status=TaskStatus.CANCELLED
                        )
                    else:
                        self._task_collection.update_one(
                            {"_id": next_task_id},
                            {
                                "$pull": {
                                    "prev_tasks": task_id,
                                },
                                "$set": {
                                    "samples": samples_to_remain_in_downstream_task,
                                    "last_updated": datetime.now(),
                                },
                            },
                        )
                        self.try_to_mark_task_ready(
                            task_id=next_task_id
                        )  # in case it was only waiting on task we just cancelled

    def update_subtask_status(
        self, task_id: ObjectId, subtask_id: ObjectId, status: TaskStatus
    ):
        """
        Update the status of a subtask
        """
        task = self.get_task(task_id=task_id, encode=False)
        subtasks = task.get("subtasks", [])
        found = False
        for subtask in subtasks:
            if subtask["subtask_id"] == subtask_id:
                found = True
                subtask["status"] = status.name
                subtask["last_updated"] = datetime.now()
                if status == TaskStatus.RUNNING and "started_at" not in subtask:
                    subtask["started_at"] = datetime.now()
                elif status == TaskStatus.COMPLETED:
                    subtask["completed_at"] = datetime.now()
                break
        if not found:
            raise ValueError(
                f"No subtask found with id: {subtask_id} within task: {task_id}"
            )

        self._task_collection.update_one(
            {"_id": task_id},
            {"$set": {"subtasks": subtasks}},
        )

    def update_result(
        self, task_id: ObjectId, name: Optional[str] = None, value: Any = None
    ):
        """
        Update result to completed job.

        Args:
            task_id: the id of task to be updated
            name: the name of the result to be updated. If ``None``, will update the entire ``result`` field. Otherwise, will update the field ``result.name``.
            value: the value to be stored. This must be bson-encodable (ie can be written into MongoDB!)
        """
        _ = self.get_task(
            task_id=task_id
        )  # just to confirm that task_id exists in collection

        # if value is None:
        #     raise ValueError("Must provide a value to update result with!")

        if name is None:
            update_path = "result"
        else:
            update_path = f"result.{name}"

        self._task_collection.update_one(
            {"_id": task_id},
            {
                "$set": {
                    update_path: make_bsonable(value),
                    "last_updated": datetime.now(),
                }
            },
        )

    def update_subtask_result(
        self, task_id: ObjectId, subtask_id: ObjectId, result: Any
    ):
        """
        Update result of completed subtask within task job.

        Args:
            task_id: the id of task to be updated
            subtask_id: the id of subtask within task to be updated
            result: the result returned by the task (which can be dumped into MongoDB)
        """
        task = self.get_task(task_id=task_id)
        subtasks = task.get("subtasks", [])

        found = False
        for subtask in subtasks:
            if subtask["subtask_id"] == subtask_id:
                found = True
                subtask["result"] = result
                subtask["last_updated"] = datetime.now()
                break
        if not found:
            raise ValueError(
                f"No subtask found with id: {subtask_id} within task: {task_id}"
            )

        self._task_collection.update_one(
            {"_id": task_id},
            {
                "$set": {
                    "subtasks": subtasks,
                    "last_updated": datetime.now(),
                }
            },
        )

    def try_to_mark_task_ready(self, task_id: ObjectId):
        """
        Check if one task's parent tasks are all completed,
        if so, mark it as READY
        """
        task = self.get_task(task_id)

        prev_task_ids = task["prev_tasks"]
        if task["status"] == TaskStatus.WAITING.name and all(
            self.get_status(task_id=task_id_) is TaskStatus.COMPLETED
            for task_id_ in prev_task_ids
        ):
            self.update_status(task_id, TaskStatus.READY)

    def get_ready_tasks(self) -> List[Dict[str, Any]]:
        """
        Return a list of ready tasks

        Returns:
            List of task entry: {"task_id": ``ObjectId``,
            "type": :py:class:`BaseTask <alab_management.task_view.task.BaseTask>`}
        """
        return self.get_tasks_by_status(status=TaskStatus.READY)

    def get_tasks_by_status(self, status: TaskStatus) -> List[Dict[str, Any]]:
        """
        Return a list of tasks with given status

        Returns:
            List of task entry: {"task_id": ``ObjectId``,
            "type": :py:class:`BaseTask <alab_management.task_view.task.BaseTask>`}
        """
        result = self._task_collection.find({"status": status.name})

        tasks: List[Dict[str, Any]] = []
        for task_entry in result:
            tasks.append(self.encode_task(task_entry))
        return tasks

    def encode_task(self, task_entry: Dict[str, Any]) -> Dict[str, Any]:
        """
        Rename _id to task_id
        Translate task's type into corresponding python class.
        """
        operation_type: Type[BaseTask] = self._tasks_definition[task_entry["type"]]
        task_entry["task_id"] = task_entry.pop(
            "_id"
        )  # change the key name of `_id` to `task_id`
        return {
            **task_entry,
            "type": operation_type,
        }

    def update_task_dependency(
        self,
        task_id: ObjectId,
        prev_tasks: Optional[Union[ObjectId, List[ObjectId]]] = None,
        next_tasks: Optional[Union[ObjectId, List[ObjectId]]] = None,
    ):
        """
        Add prev tasks and next tasks to one task entry,
        which will not overwrite old pre_task and next_tasks

        Args:
            task_id: the id of task to be updated
            prev_tasks: one or a list of ids of ``prev_tasks``
            next_tasks: one or a list of ids of ``next_tasks``
        """
        result = self.get_task(task_id=task_id, encode=False)

        prev_tasks = prev_tasks if prev_tasks is not None else []
        prev_tasks = prev_tasks if isinstance(prev_tasks, list) else [prev_tasks]
        next_tasks = next_tasks if next_tasks is not None else []
        next_tasks = next_tasks if isinstance(next_tasks, list) else [next_tasks]

        for prev_task in prev_tasks:
            if self.get_task(task_id=prev_task) is None:
                raise ValueError(f"Non-exist task id: {prev_task}")

        for next_task in next_tasks:
            if self.get_task(task_id=next_task) is None:
                raise ValueError(f"Non-exist task id: {next_task}")

        self._task_collection.update_one(
            {"_id": task_id},
            {
                "$push": {
                    "next_tasks": {"$each": next_tasks},
                    "prev_tasks": {"$each": prev_tasks},
                },
                "$set": {
                    "last_updated": datetime.now(),
                },
            },
        )

    def set_message(self, task_id: ObjectId, message: str):
        """
        Set message for one task. This is displayed on the dashboard.
        """
        self._task_collection.update_one(
            {"_id": task_id},
            {
                "$set": {
                    "message": message,
                    "last_updated": datetime.now(),
                }
            },
        )

    def set_task_actor_id(self, task_id: ObjectId, message_id: str):
        """
        Set task actor id for the task when it is submitted.

        Args:
            task_id: the task id of the task
            message_id: a uid generated by dramatiq (message_id)
        """
        self._task_collection.update_one(
            {"_id": task_id},
            {
                "$set": {
                    "task_actor_id": message_id,
                    "last_updated": datetime.now(),
                }
            },
        )

    def mark_task_as_cancelling(self, task_id: ObjectId):
        """
        Try to cancel a task by marking the task as TaskStatus.CANCELLING

        If the status is not in [READY, INITIATED, WAITING, PAUSED, READY, RUNNING],
        the request will be ignored and returned.

        The task manager will handle it.
        """
        current_status = self.get_status(task_id=task_id)

        if current_status in [
            TaskStatus.READY,
            TaskStatus.INITIATED,
            TaskStatus.WAITING,
            TaskStatus.REQUESTING_RESOURCES,
            TaskStatus.PAUSED,
            TaskStatus.READY,
            TaskStatus.RUNNING,
        ]:
            self.update_status(
                task_id=ObjectId(task_id),
                status=TaskStatus.CANCELLING,
            )

    def exists(self, task_id: Union[ObjectId, str]) -> bool:
        """
        Check if a task id exists
        """
        return self._task_collection.count_documents({"_id": ObjectId(task_id)}) > 0
