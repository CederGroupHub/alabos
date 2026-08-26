from unittest.mock import MagicMock, patch

import pytest

from alab_management.dashboard.manual_control import (
    APPROVE_RELEASE_OPTION,
    RELEASE_MANUAL_CLAIM_ACTION,
    build_claim_state,
    handle_manual_release_user_input_response,
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
