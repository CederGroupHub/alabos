from datetime import datetime, timedelta
from unittest.mock import MagicMock

from bson import ObjectId

from alab_management.user_input import (
    SUPERSEDED_RESPONSE,
    UserInputView,
    UserRequestStatus,
)


def _view_with_collection(collection):
    view = UserInputView.__new__(UserInputView)
    view._input_collection = collection
    view._task_view = MagicMock()
    view._experiment_view = MagicMock()
    view._alarm = MagicMock()
    return view


def test_insert_request_supersedes_same_device_and_prompt():
    collection = MagicMock()
    update_result = MagicMock()
    update_result.modified_count = 2
    collection.update_many.return_value = update_result
    view = _view_with_collection(collection)

    request_id = view.insert_request(
        prompt="Please set DASH_arm_JEEVES to remote control, then press OK to continue.",
        options=["OK"],
        maintenance=True,
        request_context_extra={"device": "DASH_arm_JEEVES"},
    )

    assert isinstance(request_id, ObjectId)
    collection.update_many.assert_called_once()
    query, update = collection.update_many.call_args.args
    assert query["prompt"].startswith("Please set DASH_arm_JEEVES")
    assert query["request_context.device"] == "DASH_arm_JEEVES"
    assert query["status"] == UserRequestStatus.PENDING.value
    assert update["$set"]["response"] == SUPERSEDED_RESPONSE
    collection.insert_one.assert_called_once()
    view._alarm.alert.assert_called_once()


def test_insert_request_skips_supersede_without_device():
    collection = MagicMock()
    view = _view_with_collection(collection)

    view.insert_request(
        prompt="Generic maintenance",
        options=["OK"],
        maintenance=True,
    )

    collection.update_many.assert_not_called()
    collection.insert_one.assert_called_once()


def test_collapse_duplicate_pending_keeps_newest():
    older_id = ObjectId()
    newer_id = ObjectId()
    other_id = ObjectId()
    now = datetime.now()
    collection = MagicMock()
    collection.find.return_value = [
        {
            "_id": older_id,
            "prompt": "Please set DASH_arm_JEEVES to remote control, then press OK to continue.",
            "status": UserRequestStatus.PENDING.value,
            "request_context": {"device": "DASH_arm_JEEVES", "maintenance": True},
            "last_updated": now - timedelta(minutes=10),
        },
        {
            "_id": newer_id,
            "prompt": "Please set DASH_arm_JEEVES to remote control, then press OK to continue.",
            "status": UserRequestStatus.PENDING.value,
            "request_context": {"device": "DASH_arm_JEEVES", "maintenance": True},
            "last_updated": now,
        },
        {
            "_id": other_id,
            "prompt": "Please set BFT_arm_PROMETHEUS to remote control, then press OK to continue.",
            "status": UserRequestStatus.PENDING.value,
            "request_context": {"device": "BFT_arm_PROMETHEUS", "maintenance": True},
            "last_updated": now,
        },
    ]
    update_result = MagicMock()
    update_result.modified_count = 1
    collection.update_many.return_value = update_result
    # Second find after collapse (get_all_pending_requests)
    collection.find.side_effect = [
        collection.find.return_value,
        [
            {
                "_id": newer_id,
                "prompt": "Please set DASH_arm_JEEVES to remote control, then press OK to continue.",
                "status": UserRequestStatus.PENDING.value,
                "request_context": {"device": "DASH_arm_JEEVES", "maintenance": True},
            },
            {
                "_id": other_id,
                "prompt": "Please set BFT_arm_PROMETHEUS to remote control, then press OK to continue.",
                "status": UserRequestStatus.PENDING.value,
                "request_context": {"device": "BFT_arm_PROMETHEUS", "maintenance": True},
            },
        ],
    ]
    view = _view_with_collection(collection)

    pending = view.get_all_pending_requests()

    assert len(pending) == 2
    collection.update_many.assert_called_once()
    query, update = collection.update_many.call_args.args
    assert query["_id"]["$in"] == [older_id]
    assert update["$set"]["response"] == SUPERSEDED_RESPONSE
