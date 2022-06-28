"""
Tasks view is a convienent wrapper over the ``tasks`` collection in the database. It
provides some convenience methods to query and manipulate the tasks collection.
"""

from datetime import datetime
from enum import Enum, auto
from typing import Any, Dict, List, Type, Union, Optional, cast

from bson import ObjectId

from .task import get_all_tasks, BaseTask
from ..utils.data_objects import get_collection


class TaskStatus(Enum):
    """
    The status of one task

    - ``WAITING``: the task cannot start now
    - ``READY``: the task is ready to submit
    - ``PAUSED``: the task is hold for a while
    - ``RUNNING``: the task is currently running
    - ``ERROR``: the task encountered some errors during execution
    - ``COMPLETED``: the task is completed
    """

    WAITING = auto()
    PAUSED = auto()
    STOPPED = auto()
    READY = auto()
    REQUESTING_RESOURCE = auto()
    RUNNING = auto()
    ERROR = auto()
    COMPLETED = auto()


class TaskView:
    """
    Task view manages the status, parameters of a task
    """

    def __init__(self):
        self._task_collection = get_collection("tasks")
        self._tasks_definition: Dict[str, Type[BaseTask]] = get_all_tasks()

    def create_task(
        self,
        task_type: str,
        samples: Dict[str, ObjectId],
        parameters: Dict[str, Any],
        prev_tasks: Optional[Union[ObjectId, List[ObjectId]]] = None,
        next_tasks: Optional[Union[ObjectId, List[ObjectId]]] = None,
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

        prev_tasks = prev_tasks if prev_tasks is not None else []
        prev_tasks = prev_tasks if isinstance(prev_tasks, list) else [prev_tasks]
        next_tasks = next_tasks if next_tasks is not None else []
        next_tasks = next_tasks if isinstance(next_tasks, list) else [next_tasks]

        for prev_task in prev_tasks:
            if self.get_task(task_id=prev_task) is None:
                raise ValueError(
                    f"No task exists with provided previous task id: {prev_task}"
                )

        for next_task in next_tasks:
            if self.get_task(task_id=next_task) is None:
                raise ValueError(
                    f"No task exists with provided next task id: {next_task}"
                )

        result = self._task_collection.insert_one(
            {
                "type": task_type,
                "status": TaskStatus.WAITING.name,
                "samples": samples,
                "parameters": parameters,
                "prev_tasks": prev_tasks,
                "next_tasks": next_tasks,
                "created_at": datetime.now(),
                "last_updated": datetime.now(),
            }
        )
        return cast(ObjectId, result.inserted_id)

    def get_task(
        self, task_id: ObjectId, encode: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        Get a task by its task id, which will return all the info stored in the database

        Args:
            task_id: the task_id of interest. If not found, will return ``None``
            encode: whether to encode the task using ``self.encode_task`` method
        """
        result = self._task_collection.find_one({"_id": task_id})
        if result is None:
            raise ValueError(f"No task exists with provided task id: {task_id}")
        if encode:
            result = self.encode_task(result)
        return result

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
        result = self.get_task(task_id=task_id, encode=False)
        self._task_collection.update_one(
            {"_id": task_id},
            {
                "$set": {
                    "status": status.name,
                    "last_updated": datetime.now(),
                }
            },
        )

        if status is TaskStatus.COMPLETED:
            # try to figure out tasks that is READY
            for next_task_id in result["next_tasks"]:
                self.try_to_mark_task_ready(task_id=next_task_id)

    def update_result(self, task_id: ObjectId, task_result: Any):
        """
        Update result to completed job.

        Args:
            task_id: the id of task to be updated
            task_result: the result returned by the task (which can be dumped into MongoDB)
        """
        result = self.get_task(
            task_id=task_id
        )  # just to confirm that task_id exists in collection

        self._task_collection.update_one(
            {"_id": task_id},
            {
                "$set": {
                    "result": task_result,
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
        result = self._task_collection.find({"status": TaskStatus.READY.name})

        ready_tasks: List[Dict[str, Any]] = []
        for task_entry in result:
            ready_tasks.append(self.encode_task(task_entry))
        return ready_tasks

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
