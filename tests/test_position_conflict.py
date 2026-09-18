from unittest.mock import MagicMock, patch

from bson import ObjectId

from alab_management.dashboard.position_conflict import (
    CLEAR_POSITION_CONFLICT_ACTION,
    CLEAR_POSITIONS_OPTION,
    KEEP_WAITING_OPTION,
    clear_position_conflict_blockers,
    ensure_position_conflict_user_input,
    handle_position_conflict_user_input_response,
)


def _exact_occupied_diagnosis():
    return {
        "shortages": [
            {
                "prefix": "input_rack/slot/3",
                "exact": True,
                "needed": 1,
                "available": 0,
                "blockers": [
                    {
                        "position": "input_rack/slot/3",
                        "reason": "OCCUPIED",
                        "sample_id": "aaaaaaaaaaaaaaaaaaaaaaaa",
                        "sample_name": "ghost",
                        "task_id": None,
                    }
                ],
            }
        ],
        "allow_clear": True,
        "clearable_blockers": [
            {
                "position": "input_rack/slot/3",
                "reason": "OCCUPIED",
                "sample_id": "aaaaaaaaaaaaaaaaaaaaaaaa",
                "sample_name": "ghost",
                "task_id": None,
            }
        ],
    }


def _prefix_shortage_diagnosis():
    return {
        "shortages": [
            {
                "prefix": "input_rack/slot",
                "exact": False,
                "needed": 2,
                "available": 0,
                "blockers": [
                    {
                        "position": "input_rack/slot/1",
                        "reason": "OCCUPIED",
                        "sample_id": "bbbbbbbbbbbbbbbbbbbbbbbb",
                        "sample_name": "a",
                        "task_id": None,
                    }
                ],
            }
        ],
        "allow_clear": False,
        "clearable_blockers": [],
    }


def test_ensure_position_conflict_creates_clear_prompt_for_exact():
    insert_mock = MagicMock()
    task_id = ObjectId()
    request_id = ObjectId()
    with patch(
        "alab_management.dashboard.position_conflict.user_input_view.get_pending_request_by_context",
        return_value=None,
    ), patch(
        "alab_management.dashboard.position_conflict.user_input_view.insert_request",
        insert_mock,
    ):
        ensure_position_conflict_user_input(
            task_id=task_id,
            resource_request_id=request_id,
            diagnosis=_exact_occupied_diagnosis(),
        )

    insert_mock.assert_called_once()
    kwargs = insert_mock.call_args.kwargs
    assert CLEAR_POSITIONS_OPTION in kwargs["options"]
    assert KEEP_WAITING_OPTION in kwargs["options"]
    assert kwargs["category"] == "Sample Positions"
    assert kwargs["request_context_extra"]["action"] == CLEAR_POSITION_CONFLICT_ACTION
    assert kwargs["request_context_extra"]["allow_clear"] is True
    assert len(kwargs["request_context_extra"]["blockers"]) == 1


def test_ensure_position_conflict_dedupes_pending():
    insert_mock = MagicMock()
    with patch(
        "alab_management.dashboard.position_conflict.user_input_view.get_pending_request_by_context",
        return_value={"_id": ObjectId()},
    ), patch(
        "alab_management.dashboard.position_conflict.user_input_view.insert_request",
        insert_mock,
    ):
        ensure_position_conflict_user_input(
            task_id=ObjectId(),
            resource_request_id=ObjectId(),
            diagnosis=_exact_occupied_diagnosis(),
        )
    insert_mock.assert_not_called()


def test_ensure_position_conflict_prefix_notify_only():
    insert_mock = MagicMock()
    with patch(
        "alab_management.dashboard.position_conflict.user_input_view.get_pending_request_by_context",
        return_value=None,
    ), patch(
        "alab_management.dashboard.position_conflict.user_input_view.insert_request",
        insert_mock,
    ):
        ensure_position_conflict_user_input(
            task_id=ObjectId(),
            resource_request_id=ObjectId(),
            diagnosis=_prefix_shortage_diagnosis(),
        )

    kwargs = insert_mock.call_args.kwargs
    assert kwargs["options"] == [KEEP_WAITING_OPTION]
    assert kwargs["request_context_extra"]["allow_clear"] is False
    assert kwargs["request_context_extra"]["blockers"] == []


def test_handle_clear_calls_clear_blockers():
    clear_mock = MagicMock()
    blockers = [
        {
            "position": "input_rack/slot/3",
            "reason": "OCCUPIED",
            "sample_id": "aaaaaaaaaaaaaaaaaaaaaaaa",
            "sample_name": "ghost",
            "task_id": None,
        }
    ]
    request_doc = {
        "request_context": {
            "action": CLEAR_POSITION_CONFLICT_ACTION,
            "allow_clear": True,
            "blockers": blockers,
        }
    }
    with patch(
        "alab_management.dashboard.position_conflict.clear_position_conflict_blockers",
        clear_mock,
    ):
        handle_position_conflict_user_input_response(
            request_doc, CLEAR_POSITIONS_OPTION
        )
    clear_mock.assert_called_once_with(blockers)


def test_handle_keep_waiting_does_not_clear():
    clear_mock = MagicMock()
    request_doc = {
        "request_context": {
            "action": CLEAR_POSITION_CONFLICT_ACTION,
            "allow_clear": True,
            "blockers": [{"position": "input_rack/slot/3", "reason": "LOCKED"}],
        }
    }
    with patch(
        "alab_management.dashboard.position_conflict.clear_position_conflict_blockers",
        clear_mock,
    ):
        handle_position_conflict_user_input_response(
            request_doc, KEEP_WAITING_OPTION
        )
    clear_mock.assert_not_called()


def test_handle_clear_ignored_when_not_allow_clear():
    clear_mock = MagicMock()
    request_doc = {
        "request_context": {
            "action": CLEAR_POSITION_CONFLICT_ACTION,
            "allow_clear": False,
            "blockers": [],
        }
    }
    with patch(
        "alab_management.dashboard.position_conflict.clear_position_conflict_blockers",
        clear_mock,
    ):
        handle_position_conflict_user_input_response(
            request_doc, CLEAR_POSITIONS_OPTION
        )
    clear_mock.assert_not_called()


def test_clear_position_conflict_blockers_occupied_and_locked():
    sample_id = ObjectId()
    move_mock = MagicMock()
    release_mock = MagicMock()
    get_mock = MagicMock(return_value={"name": "pos"})
    locked_mock = MagicMock(return_value=True)

    with patch(
        "alab_management.dashboard.position_conflict.sample_view.move_sample",
        move_mock,
    ), patch(
        "alab_management.dashboard.position_conflict.sample_view.release_sample_position",
        release_mock,
    ), patch(
        "alab_management.dashboard.position_conflict.sample_view.get_sample_position",
        get_mock,
    ), patch(
        "alab_management.dashboard.position_conflict.sample_view.is_locked_position",
        locked_mock,
    ):
        clear_position_conflict_blockers(
            [
                {
                    "position": "input_rack/slot/3",
                    "reason": "OCCUPIED",
                    "sample_id": str(sample_id),
                },
                {
                    "position": "input_rack/slot/4",
                    "reason": "LOCKED",
                    "sample_id": None,
                },
            ]
        )

    move_mock.assert_called_once_with(sample_id, None)
    assert release_mock.call_count == 2
    release_mock.assert_any_call("input_rack/slot/3")
    release_mock.assert_any_call("input_rack/slot/4")


def test_ensure_skips_empty_diagnosis():
    insert_mock = MagicMock()
    with patch(
        "alab_management.dashboard.position_conflict.user_input_view.insert_request",
        insert_mock,
    ):
        ensure_position_conflict_user_input(
            task_id=ObjectId(),
            resource_request_id=ObjectId(),
            diagnosis={
                "shortages": [],
                "allow_clear": False,
                "clearable_blockers": [],
            },
        )
    insert_mock.assert_not_called()
