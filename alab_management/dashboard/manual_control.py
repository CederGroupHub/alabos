"""Shared helpers for Device Control manual claims."""

from __future__ import annotations

from typing import Any

from bson import ObjectId

from alab_management.dashboard.lab_views import device_view, user_input_view
from alab_management.user_input import UserRequestStatus

MANUAL_CONTROL_ATTRIBUTE = "manual_control_task_id"
RELEASE_MANUAL_CLAIM_ACTION = "release_manual_claim"
APPROVE_RELEASE_OPTION = "Release device to automated run"
DENY_RELEASE_OPTION = "Keep manual control"


def get_manual_claim_id(device_entry: dict[str, Any]) -> str | None:
    attributes = device_entry.get("attributes") or {}
    claim_id = attributes.get(MANUAL_CONTROL_ATTRIBUTE)
    if claim_id in ("", None):
        return None
    return str(claim_id)


def set_manual_claim_id(device_name: str, manual_task_id: str | None):
    attributes = dict(device_view.get_all_attributes(device_name=device_name) or {})
    if manual_task_id is None:
        attributes.pop(MANUAL_CONTROL_ATTRIBUTE, None)
    else:
        attributes[MANUAL_CONTROL_ATTRIBUTE] = manual_task_id
    device_view.set_all_attributes(device_name=device_name, attributes=attributes)


def is_manually_claimed(device_name: str) -> bool:
    device_entry = device_view.get_device(device_name=device_name)
    manual_claim_id = get_manual_claim_id(device_entry)
    return (
        manual_claim_id is not None
        and device_entry.get("task_id") is not None
        and str(device_entry["task_id"]) == manual_claim_id
    )


def is_auto_occupied(device_name: str) -> bool:
    device_entry = device_view.get_device(device_name=device_name)
    if device_entry.get("status") != "OCCUPIED":
        return False
    return not is_manually_claimed(device_name)


def get_pending_auto_release_request(device_name: str) -> dict[str, Any] | None:
    return user_input_view.get_pending_request_by_context(
        {
            "action": RELEASE_MANUAL_CLAIM_ACTION,
            "device_name": device_name,
        }
    )


def release_manual_claim(device_name: str):
    """Release a manual-control claim without requiring a dashboard token."""
    device_entry = device_view.get_device(device_name=device_name)
    manual_claim_id = get_manual_claim_id(device_entry)
    if manual_claim_id is None:
        raise ValueError(f"Device '{device_name}' is not claimed for manual control.")
    if device_entry.get("task_id") is None or str(device_entry["task_id"]) != manual_claim_id:
        raise ValueError(
            f"Device '{device_name}' is not currently held by the manual-control claim."
        )
    device_view.release_device(device_name=device_name)
    set_manual_claim_id(device_name, None)


def require_manual_claim(device_name: str, manual_task_id: str):
    device_entry = device_view.get_device(device_name=device_name)
    manual_claim = get_manual_claim_id(device_entry)
    if manual_claim is None:
        raise ValueError(f"Device '{device_name}' is not claimed for manual control.")
    if manual_claim != manual_task_id:
        raise ValueError("Manual claim token does not match the current device claim.")
    if device_entry.get("task_id") is None or str(device_entry["task_id"]) != manual_task_id:
        raise ValueError("Device occupier does not match the provided manual claim token.")


def release_manual_claim_with_token(device_name: str, manual_task_id: str):
    require_manual_claim(device_name, manual_task_id)
    release_manual_claim(device_name)


def build_claim_state(device_name: str, dashboard_status: str, is_manual_claim: bool) -> str:
    if is_manual_claim and get_pending_auto_release_request(device_name) is not None:
        return "Automated run waiting for release"
    if is_manual_claim:
        return "Claimed by manual control"
    if is_auto_occupied(device_name):
        return "In use by automated run"
    if dashboard_status != "IDLE":
        return "Unavailable"
    return "Unclaimed"


def handle_manual_release_user_input_response(request_doc: dict[str, Any], response: str):
    context = request_doc.get("request_context") or {}
    if context.get("action") != RELEASE_MANUAL_CLAIM_ACTION:
        return
    if response != APPROVE_RELEASE_OPTION:
        return
    release_manual_claim(context["device_name"])


def ensure_auto_release_user_input(
    *,
    device_name: str,
    task_id: ObjectId,
    resource_request_id: ObjectId,
    device_label: str | None = None,
):
    """Create a deduplicated user-input request to release manual control."""
    if not is_manually_claimed(device_name):
        return

    existing = user_input_view.get_pending_request_by_context(
        {
            "action": RELEASE_MANUAL_CLAIM_ACTION,
            "device_name": device_name,
            "task_id": task_id,
        }
    )
    if existing is not None:
        return

    label = device_label or device_name
    prompt = (
        f"The automated system needs {label} ({device_name}) for an experiment task, "
        "but it is currently under manual control in Device Control. "
        "Release manual control so the automated run can continue?"
    )
    user_input_view.insert_request(
        task_id=task_id,
        prompt=prompt,
        options=[APPROVE_RELEASE_OPTION, DENY_RELEASE_OPTION],
        category="Device Control",
        request_context_extra={
            "action": RELEASE_MANUAL_CLAIM_ACTION,
            "device_name": device_name,
            "resource_request_id": str(resource_request_id),
        },
    )
