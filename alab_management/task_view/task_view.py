"""
Tasks view is a convienent wrapper over the ``tasks`` collection in the database. It
provides some convenience methods to query and manipulate the tasks collection.
"""

from datetime import datetime
from typing import Any, Dict, List, Literal, Type, Union, Optional, cast

from bson import ObjectId

from alab_management.task_view.task import get_all_tasks, BaseTask
from alab_management.utils.data_objects import (
    get_collection,
    get_labgraph_mongodb,
    make_bsonable,
    get_lock,
)
from alab_management.task_view.task_enums import TaskStatus
from alab_management.labgraph_types.placeholders import (
    PLACEHOLDER_ACTOR_FOR_TASKS_THAT_HAVENT_RUN_YET,
)
from .completed_task_view import CompletedTaskView
from labgraph.data.nodes import BaseNode, BaseNodeWithActor
from labgraph.views.base import BaseNodeView
from labgraph import Action, Analysis, Measurement, Material, views
from labgraph.views.base import NotFoundInDatabaseError

completed_task_view = CompletedTaskView()


class LabgraphNodeView:
    def __init__(self):
        labgraph_mongodb_instance = get_labgraph_mongodb()
        self.action_view = views.ActionView(
            labgraph_mongodb_instance=labgraph_mongodb_instance
        )
        self.measurement_view = views.MeasurementView(
            labgraph_mongodb_instance=labgraph_mongodb_instance
        )
        self.analysis_view = views.AnalysisView(
            labgraph_mongodb_instance=labgraph_mongodb_instance
        )
        self.material_view = views.MaterialView(
            labgraph_mongodb_instance=labgraph_mongodb_instance
        )

        self.views: Dict[str, BaseNodeView] = {
            "Action": self.action_view,
            "Measurement": self.measurement_view,
            "Analysis": self.analysis_view,
            "Material": self.material_view,
        }

    def get_node(
        self,
        node_id: ObjectId,
        node_type: Literal["Action", "Measurement", "Analysis", "Material"],
    ) -> BaseNode:
        """
        Get a node by its node id, which will return all the info stored in the database

        Args:
            node_id: the node_id of interest. If not found, will return ``None``
        """
        node_id = ObjectId(node_id)
        view = self.views.get(node_type)

        return view.get_by_id(id=node_id)

    def update_node(self, node: BaseNode):
        view = self.views.get(node.__class__.__name__)
        view.update(entry=node, no_version_update=True)


class TaskView:
    """
    Task view manages the status, parameters of a task
    """

    def __init__(self):
        self._labgraph_view = LabgraphNodeView()
        self._lock = get_lock("tasks")
        self._tasks_definition: Dict[str, Type[BaseTask]] = get_all_tasks()
        self._task_collection = get_collection("tasks")

    def create_task(
        self,
        task_id: ObjectId,
        labgraph_node_type: Literal["Action", "Measurement", "Analysis"],
        name: str,
        parameters: Dict[str, Any],
        samples: List[ObjectId],
        prev_tasks: List[ObjectId],
        **extras,
    ) -> ObjectId:
        """
        Insert a task into the task collection

        Args:
            task_id (ObjectId): the id of the node in labgraph
            labgraph_node_type (str): type of node this task corresponds to
            name: the name of task, which should be a class name inherited from
              :py:class:`BaseTask <alab_management.task_view.task.BaseTask>`
            parameters: the required keyword arguments for this task
            samples: the samples that this task will handle, which will be passed to Task object
              the same as parameters.
            prev_tasks: one or a list of ObjectId that refer to prev tasks of this task
              (which must be completed before current task)

        Returns:
            the assigned id for this task
        """
        if name not in self._tasks_definition:
            raise ValueError(f"Unsupported task: {name}")

        prev_tasks = prev_tasks or []
        prev_tasks = prev_tasks if isinstance(prev_tasks, list) else [prev_tasks]

        for prev_task_id in prev_tasks:
            self.get_task_node(task_id=prev_task_id)  # will raise error if not found

        entry = {
            "_id": task_id,
            "name": name,
            "status": TaskStatus.WAITING.name,
            # "samples": samples,
            "parameters": parameters,
            "prev_tasks": prev_tasks,
            # "created_at": datetime.now(),
            # "last_updated": datetime.now(),
            "labgraph_node_type": labgraph_node_type,
            # "message": "",
        }

        node = self._labgraph_view.get_node(task_id, labgraph_node_type)
        node["status"] = TaskStatus.WAITING.name
        node["samples"] = samples
        node["message"] = ""
        self._labgraph_view.update_node(node)
        result = self._task_collection.insert_one(entry)

        return cast(ObjectId, result.inserted_id)

    def create_subtask(self, task_id, name, samples: List[str], parameters: dict):
        """
        Create a subtask entry for a task.
        """
        task = self.get_task_node(task_id=task_id)
        node = self._labgraph_view.get_node(task_id, task["labgraph_node_type"])

        subtask_id = ObjectId()
        node["subtasks"] = node.get("subtasks", [])
        node["subtasks"].append(
            {
                "subtask_id": subtask_id,
                "name": name,
                "samples": samples,
                "status": TaskStatus.INITIATED.name,
                "parameters": parameters,
                "created_at": datetime.now(),
                "last_updated": datetime.now(),
            }
        )
        self._labgraph_view.update_node(node)

        # self._task_collection.update_one(
        #     {"_id": task_id},
        #     {
        #         "$set": {
        #             "subtasks": subtasks,
        #             "last_updated": datetime.now(),
        #         }
        #     },
        # )
        return subtask_id

    def get_task_node(self, task_id: ObjectId) -> BaseNodeWithActor:
        """
        Get a task by its task id, which will return all the info stored in the database

        Args:
            task_id: the task_id of interest. If not found, will return ``None``
        """

        task_id = ObjectId(task_id)
        result = self.get_task_entry(task_id=task_id)
        node_type = result["labgraph_node_type"]
        try:
            node = self._labgraph_view.get_node(node_id=task_id, node_type=node_type)
        except NotFoundInDatabaseError:
            raise ValueError(
                f"No task node of type {node_type} exists with provided task id: {task_id}"
            )

        return node

    def get_task_entry(self, task_id: ObjectId) -> Dict[str, Any]:
        result = self._task_collection.find_one({"_id": ObjectId(task_id)})
        if not result:
            raise ValueError(f"No task found with id: {task_id}")
        return result

    def get_status(self, task_id: ObjectId) -> TaskStatus:
        """
        Get the status of a task
        """
        task = self.get_task_node(task_id=task_id)
        return TaskStatus[task["status"]]

    def get_next_task_ids(self, task_id: ObjectId) -> List[ObjectId]:
        return [
            task["_id"]
            for task in self._task_collection.find(
                {
                    "prev_tasks": {"$in": [task_id]},
                }
            )
        ]

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
        task_id = ObjectId(task_id)
        node = self.get_task_node(
            task_id=task_id,
        )
        node["status"] = status.name
        self._task_collection.update_one(
            {"_id": task_id},
            {
                "$set": {
                    "status": status.name,
                }
            },
        )

        if status == TaskStatus.RUNNING and "started_at" not in node.keys():
            node["started_at"] = datetime.now()
        elif status == TaskStatus.COMPLETED:
            node["completed_at"] = datetime.now()

        self._labgraph_view.update_node(node)
        if status is TaskStatus.COMPLETED:
            # try to figure out tasks that is READY
            for next_task_id in self.get_next_task_ids(task_id):
                self.try_to_mark_task_ready(task_id=next_task_id)
            self._task_collection.update_one(
                {"_id": task_id}, {"$unset": {"task_actor_id": 1}}
            )
            self._labgraph_view.update_node(node)

        if status in [TaskStatus.CANCELLED, TaskStatus.ERROR]:
            # any downstream tasks should be:
            # 1. cancelled if they depend _only on this task_
            # 2. made independent of this task. This includes removing affected samples from the downstream task
            samples_in_this_task = [s["sample_id"] for s in node["samples"]]
            for next_task_id in self.get_next_task_ids(task_id):
                next_task = self.get_task_node(
                    task_id=next_task_id,
                )
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
            self._task_collection.update_one(
                {"_id": task_id}, {"$unset": {"task_actor_id": 1}}
            )

    def add_actor_to_task(self, task_id: ObjectId, actor_name: str):
        """
        Add a task actor to the database
        """
        actor_view = views.ActorView(labgraph_mongodb_instance=get_labgraph_mongodb())
        actor = actor_view.get_by_name(name=actor_name)[0]

        task_node = self.get_task_node(task_id=task_id)

        task_node.add_actor(actor=actor)
        if PLACEHOLDER_ACTOR_FOR_TASKS_THAT_HAVENT_RUN_YET in task_node.actor:
            task_node.remove_actor(
                actor=PLACEHOLDER_ACTOR_FOR_TASKS_THAT_HAVENT_RUN_YET
            )
        self._labgraph_view.update_node(task_node)

    def update_subtask_status(
        self, task_id: ObjectId, subtask_id: ObjectId, status: TaskStatus
    ):
        """
        Update the status of a subtask
        """
        node = self.get_task_node(
            task_id=task_id,
        )

        subtasks = node.get("subtasks", [])
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
        self._labgraph_view.update_node(node)

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
        node = self.get_task_node(task_id=task_id)

        if name is None:
            node["result"] = make_bsonable(value)
        else:
            result = node.get("result", {})
            result[name] = make_bsonable(value)
            node["result"] = result
        self._labgraph_view.update_node(node)

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
        node = self.get_task_node(task_id=task_id)
        subtasks = node.get("subtasks", [])

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

        self._labgraph_view.update_node(node)

    def try_to_mark_task_ready(self, task_id: ObjectId):
        """
        Check if one task's parent tasks are all completed,
        if so, mark it as READY
        """
        task_id = ObjectId(task_id)
        node = self.get_task_node(task_id)
        entry = self._task_collection.find_one({"_id": task_id})
        if entry is None:
            raise ValueError(f"Cannot find task entry with id: {task_id}")

        prev_task_ids = entry["prev_tasks"]
        if node["status"] == TaskStatus.WAITING.name and all(
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
        return [entry for entry in self._task_collection.find({"status": status.name})]

    def encode_task(self, name: str) -> BaseTask:
        """
        Translate task's name into corresponding python class.
        """
        task_class_object: Type[BaseTask] = self._tasks_definition[name]
        return task_class_object

    def set_message(self, task_id: ObjectId, message: str):
        """
        Set message for one task. This is displayed on the dashboard.
        """

        node = self.get_task_node(task_id)
        node["message"] = message
        self._labgraph_view.update_node(node)

        # self._task_collection.update_one(
        #     {"_id": task_id},
        #     {
        #         "$set": {
        #             "message": message,
        #             "last_updated": datetime.now(),
        #         }
        #     },
        # )

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
