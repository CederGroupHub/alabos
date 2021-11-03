from datetime import datetime
from enum import Enum, auto
from threading import Lock
from typing import Any, Dict, List, Type, Union

from bson import ObjectId

from ..db import get_collection
from .task import get_all_tasks, BaseTask


class _MISSING: pass


_MISSING = _MISSING()


class TaskStatus(Enum):
    """
    The status of one task

    - ``WAITING``: the task cannot start now
    - ``READY``: the task is ready to submit
    - ``RUNNING``: the task is currently running
    - ``ERROR``: the task encountered some errors during execution
    - ``COMPLETED``: the task is completed
    """
    WAITING = auto()
    READY = auto()
    RUNNING = auto()
    ERROR = auto()
    COMPLETED = auto()


class TaskView:
    """
    Task view manages the status, parameters of a task
    """
    def __init__(self):
        self._task_collection = get_collection("tasks")
        self.operations_definition: Dict[str, Type[BaseTask]] = get_all_tasks()
        self._lock = Lock()

    def create_task(
            self, task_type: str,
            parameters: Dict[str, Any],
            prev_tasks: Union[ObjectId, List[ObjectId]] = _MISSING,
            next_tasks: Union[ObjectId, List[ObjectId]] = _MISSING,
    ) -> ObjectId:
        """
        Insert a task into the task collection

        Args:
            task_type: the type of task, which should be a type name of class inherited from
              :py:class:`BaseTask <alab_management.task_view.task.BaseTask>`
            parameters: the required tasks for this task
            prev_tasks: one or a list of ObjectId that refer to prev tasks of this task
              (which must be completed before current task)
            next_tasks: one or a list of ObjectId that refer to next tasks of this task
              (which cannot start until this task finishes)

        Returns:
            the assigned id for this task
        """
        if task_type not in self.operations_definition:
            raise ValueError(f"Unsupported task type: {task_type}")

        result = self._task_collection.insert_one({
            "type": task_type,
            "status": TaskStatus.WAITING.name,
            "parameters": parameters,
            "prev_tasks": prev_tasks if prev_tasks is not _MISSING else [],
            "next_tasks": next_tasks if next_tasks is not _MISSING else [],
            "created_at": datetime.now(),
            "last_updated": datetime.now(),
        })
        return result.inserted_id

    def get_task(self, task_id: ObjectId) -> Dict[str, Any]:
        """
        Get a task by its task id, which will return all the info stored in the database
        """
        result = self._task_collection.find_one({"_id": task_id})
        if result is None:
            raise ValueError(f"Cannot find task with id: {task_id}")
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
        result = self._task_collection.find_one({"_id": task_id})
        if result is None:
            raise ValueError(f"Cannot find task with id: {task_id}")
        try:
            self._lock.acquire()
            self._task_collection.update_one({"_id": task_id}, {"$set": {
                "status": status.name,
                "last_updated": datetime.now(),
            }})
        finally:
            self._lock.release()

        if status is TaskStatus.COMPLETED:
            self._mark_next_ready_tasks(task_id=task_id)

    def _mark_next_ready_tasks(self, task_id: ObjectId):
        """
        Check if one task's next tasks are ready
        """
        for next_task_id in self._task_collection.find({"_id": task_id}):
            next_task = self.get_task(task_id)
            next_task_parents_id = next_task["previous_tasks"]
            if next_task["status"] is TaskStatus.WAITING and \
                all(self.get_status(task_id=task_id_) is TaskStatus.COMPLETED
                    for task_id_ in next_task_parents_id):
                self.update_status(next_task_id, TaskStatus.READY)

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
            operation_type: Type[BaseTask] = self.operations_definition[task_entry["type"]]
            task_entry["task_id"] = task_entry.pop("_id")  # change the key name of `_id` to `task_id`
            ready_tasks.append({
                **task_entry,
                "type": operation_type,
            })
        return ready_tasks

    def update_task_dependency(self, task_id: ObjectId,
                               prev_tasks: Union[ObjectId, List[ObjectId]] = _MISSING,
                               next_tasks: Union[ObjectId, List[ObjectId]] = _MISSING):
        """
        Add prev tasks and next tasks to one task entry,
        which will not overwrite old pre_task and next_tasks

        Args:
            task_id: the id of task to be updated
            prev_tasks: one or a list of ids of ``prev_tasks``
            next_tasks: one or a list of ids of ``next_tasks``
        """
        result = self._task_collection.find_one({"_id": task_id})
        if result is None:
            raise ValueError(f"Cannot find task with id: {task_id}")

        if prev_tasks is _MISSING:
            prev_tasks = []
        elif isinstance(prev_tasks, ObjectId):
            prev_tasks = [prev_tasks]
        if next_tasks is _MISSING:
            next_tasks = []
        elif isinstance(next_tasks, ObjectId):
            next_tasks = [next_tasks]

        self._task_collection.update_one({"_id": task_id}, {"$addToSet": {
            "next_tasks": {"$each": next_tasks},
            "prev_tasks": {"$each": prev_tasks},
        }, "$set": {
            "last_updated": datetime.now(),
        }})
