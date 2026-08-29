from unittest.mock import MagicMock, patch

import pytest

from alab_management.dashboard.manual_control import (
    APPROVE_RELEASE_OPTION,
    MANUAL_CONTROL_ATTRIBUTE,
    RELEASE_MANUAL_CLAIM_ACTION,
    build_claim_state,
    handle_manual_release_user_input_response,
)
from alab_management.dashboard.routes.status import (
    device_is_manually_claimed,
    parse_device_status,
)


def test_parse_device_status_manual_control_is_not_occupied():
    task_id = "abc123"
    assert (
        parse_device_status(
            "OCCUPIED",
            "RELEASED",
            {MANUAL_CONTROL_ATTRIBUTE: task_id},
            task_id=task_id,
        )
        == "MANUAL_CONTROL"
    )


def test_parse_device_status_stale_manual_attribute_stays_occupied():
    assert (
        parse_device_status(
            "OCCUPIED",
            "RELEASED",
            {MANUAL_CONTROL_ATTRIBUTE: "old-claim"},
            task_id="workflow-task",
        )
        == "OCCUPIED"
    )


def test_device_is_manually_claimed_requires_matching_task():
    task_id = "abc123"
    assert device_is_manually_claimed(
        {
            "task_id": task_id,
            "attributes": {MANUAL_CONTROL_ATTRIBUTE: task_id},
        }
    )
    assert not device_is_manually_claimed(
        {
            "task_id": "workflow-task",
            "attributes": {MANUAL_CONTROL_ATTRIBUTE: "abc123"},
        }
    )


def test_build_claim_state_manual_claim():
    with patch(
        "alab_management.dashboard.manual_control.get_pending_auto_release_request",
        return_value=None,
    ), patch(
        "alab_management.dashboard.manual_control.is_auto_occupied",
        return_value=False,
    ):
        assert (
            build_claim_state("DASH_capper", "OCCUPIED", True)
            == "Claimed by manual control"
        )


def test_build_claim_state_auto_waiting():
    with patch(
        "alab_management.dashboard.manual_control.get_pending_auto_release_request",
        return_value={"_id": "pending"},
    ):
        assert (
            build_claim_state("DASH_capper", "OCCUPIED", True)
            == "Automated run waiting for release"
        )


def test_build_claim_state_auto_occupied():
    with patch(
        "alab_management.dashboard.manual_control.is_auto_occupied",
        return_value=True,
    ):
        assert (
            build_claim_state("DASH_capper", "OCCUPIED", False)
            == "In use by automated run"
        )


def test_handle_manual_release_user_input_response_approves_release():
    release_mock = MagicMock()
    request_doc = {
        "request_context": {
            "action": RELEASE_MANUAL_CLAIM_ACTION,
            "device_name": "DASH_capper",
        }
    }
    with patch(
        "alab_management.dashboard.manual_control.release_manual_claim",
        release_mock,
    ):
        handle_manual_release_user_input_response(
            request_doc, APPROVE_RELEASE_OPTION
        )
    release_mock.assert_called_once_with("DASH_capper")


def test_handle_manual_release_user_input_response_denies_release():
    release_mock = MagicMock()
    request_doc = {
        "request_context": {
            "action": RELEASE_MANUAL_CLAIM_ACTION,
            "device_name": "DASH_capper",
        }
    }
    with patch(
        "alab_management.dashboard.manual_control.release_manual_claim",
        release_mock,
    ):
        handle_manual_release_user_input_response(
            request_doc, "Keep manual control"
        )
    release_mock.assert_not_called()
