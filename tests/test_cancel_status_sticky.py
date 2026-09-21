"""Dashboard Cancel must not be overwritten by a late worker ERROR/FINISHING write."""

from datetime import datetime
from unittest.mock import MagicMock

from bson import ObjectId

from alab_management.task_view.task_enums import TaskStatus
from alab_management.task_view.task_view import TaskView


def test_update_status_does_not_overwrite_cancelled_with_error():
    task_id = ObjectId()
    collection = MagicMock()
    collection.find_one.return_value = {
        "_id": task_id,
        "status": TaskStatus.CANCELLED.name,
        "samples": [],
        "next_tasks": [],
        "prev_tasks": [],
        "last_updated": datetime.now(),
    }
    view = TaskView.__new__(TaskView)
    view._task_collection = collection
    view._gridfs = MagicMock()

    view.update_status(task_id=task_id, status=TaskStatus.ERROR)
    view.update_status(task_id=task_id, status=TaskStatus.FINISHING)
    view.update_status(task_id=task_id, status=TaskStatus.RUNNING)

    collection.update_one.assert_not_called()


def test_update_status_allows_rewriting_cancelled_as_cancelled():
    task_id = ObjectId()
    collection = MagicMock()
    collection.find_one.return_value = {
        "_id": task_id,
        "status": TaskStatus.CANCELLED.name,
        "samples": [],
        "next_tasks": [],
        "prev_tasks": [],
        "last_updated": datetime.now(),
    }
    view = TaskView.__new__(TaskView)
    view._task_collection = collection
    view._gridfs = MagicMock()

    view.update_status(task_id=task_id, status=TaskStatus.CANCELLED)

    collection.update_one.assert_called_once()
    update = collection.update_one.call_args.args[1]["$set"]
    assert update["status"] == TaskStatus.CANCELLED.name
