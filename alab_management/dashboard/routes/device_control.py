"""Curated manual-control routes for selected lab devices."""

from __future__ import annotations

from typing import Any

from bson import ObjectId
from bson.errors import InvalidId
from flask import Blueprint, request

from alab_management.dashboard.lab_views import device_view
from alab_management.device_manager import DevicesClient

device_control_bp = Blueprint(
    "/device-control", __name__, url_prefix="/api/device-control"
)

MANUAL_CONTROL_ATTRIBUTE = "manual_control_task_id"

BLOCKED_COMMANDS: dict[str, set[str]] = {
    "DASH_capper": {"open_top_gripper", "close_top_gripper"},
}

DEVICE_CATALOG = [
    {
        "device_name": "DASH_capper",
        "label": "Capper",
        "description": "PLC-backed capper with bottom gripper and spin motor.",
        "implementation_status": "implemented",
        "not_implemented_reason": None,
    },
    {
        "device_name": "DASH_ball_dispenser",
        "label": "Ball Dispenser",
        "description": "Dispenses individual milling balls into a positioned container.",
        "implementation_status": "implemented",
        "not_implemented_reason": None,
    },
    {
        "device_name": "DASH_shaker",
        "label": "Shaker",
        "description": "Vertical shaker and gripper used for powder mixing workflows.",
        "implementation_status": "implemented",
        "not_implemented_reason": None,
    },
    {
        "device_name": "DASH_scale",
        "label": "Scale",
        "description": "Ohaus scale for mass reads and tare operations.",
        "implementation_status": "implemented",
        "not_implemented_reason": None,
    },
    {
        "device_name": "DASH_acrylic_disk_dispenser",
        "label": "Acrylic Disk Dispenser",
        "description": "Cap/disk dispenser hardware present in DASH.",
        "implementation_status": "not_implemented",
        "not_implemented_reason": "Out of v1 scope and needs hardware validation first.",
    },
    {
        "device_name": "DASH_vial_labeler",
        "label": "Vial Labeler",
        "description": "Label printer present in DASH.",
        "implementation_status": "not_implemented",
        "not_implemented_reason": "Out of v1 scope and still workflow-coupled.",
    },
    {
        "device_name": "DASH_aeris_xrd",
        "label": "Aeris XRD",
        "description": "Aeris XRD diffractometer present in DASH.",
        "implementation_status": "not_implemented",
        "not_implemented_reason": "Out of v1 scope and requires hardware-specific validation first.",
    },
]

COMMAND_REGISTRY = {
    "DASH_capper": {
        "probe_plc": {
            "label": "Probe PLC",
            "mode": "read",
            "params": {},
            "target_method": "probe_plc",
        },
        "get_state": {
            "label": "Get State",
            "mode": "read",
            "params": {},
            "target_method": "get_state",
        },
        "open_bottom_gripper": {
            "label": "Open Bottom Gripper",
            "mode": "actuate",
            "params": {},
            "target_method": "open_bottom_gripper",
        },
        "close_bottom_gripper": {
            "label": "Close Bottom Gripper",
            "mode": "actuate",
            "params": {},
            "target_method": "close_bottom_gripper",
        },
        "cw_motor": {
            "label": "CW Motor",
            "mode": "actuate",
            "params": {
                "rpm": {"type": "int", "required": True, "min": 1},
                "revolutions": {"type": "float", "required": True, "min": 0.1},
            },
            "target_method": "cw_motor",
        },
        "ccw_motor": {
            "label": "CCW Motor",
            "mode": "actuate",
            "params": {
                "rpm": {"type": "int", "required": True, "min": 1},
                "revolutions": {"type": "float", "required": True, "min": 0.1},
            },
            "target_method": "ccw_motor",
        },
    },
    "DASH_ball_dispenser": {
        "get_state": {
            "label": "Get State",
            "mode": "read",
            "params": {},
            "target_method": "get_state",
        },
        "is_running": {
            "label": "Is Running?",
            "mode": "read",
            "params": {},
            "target_method": "is_running",
        },
        "dispense_one": {
            "label": "Dispense One",
            "mode": "actuate",
            "params": {},
            "target_method": "dispense_one",
        },
    },
    "DASH_shaker": {
        "get_state": {
            "label": "Get State",
            "mode": "read",
            "params": {},
            "target_method": "get_state",
        },
        "is_running": {
            "label": "Is Shaking?",
            "mode": "read",
            "params": {},
            "target_method": "is_running",
        },
        "open_gripper": {
            "label": "Open Gripper",
            "mode": "actuate",
            "params": {},
            "target_method": "open_gripper",
        },
        "close_gripper": {
            "label": "Close Gripper",
            "mode": "actuate",
            "params": {},
            "target_method": "close_gripper",
        },
        "shake": {
            "label": "Shake",
            "mode": "actuate",
            "params": {
                "duration_seconds": {
                    "type": "float",
                    "required": True,
                    "min": 0.1,
                    "default": 60,
                },
                "frequency": {
                    "type": "int",
                    "required": True,
                    "min": 1,
                    "max": 70,
                    "default": 51,
                },
                "close_gripper": {
                    "type": "bool",
                    "required": True,
                    "default": True,
                },
            },
            "target_method": "shake",
        },
        "stop": {
            "label": "Stop Shaking",
            "mode": "actuate",
            "params": {},
            "target_method": "stop",
        },
        "reset": {
            "label": "Reset",
            "mode": "actuate",
            "params": {},
            "target_method": "reset",
        },
    },
    "DASH_scale": {
        "get_mass_in_mg": {
            "label": "Get Mass (mg)",
            "mode": "read",
            "params": {},
            "target_method": "get_mass_in_mg",
        },
        "tare": {
            "label": "Tare",
            "mode": "actuate",
            "params": {},
            "target_method": "tare",
        },
    },
}


def _parse_dashboard_status(task_status: str, pause_status: str) -> str:
    if pause_status == "PAUSED":
        return "PAUSED"
    if pause_status == "REQUESTED":
        return "PAUSE_REQUESTED"
    return task_status


def _get_manual_claim_id(device_entry: dict[str, Any]) -> str | None:
    attributes = device_entry.get("attributes") or {}
    claim_id = attributes.get(MANUAL_CONTROL_ATTRIBUTE)
    if claim_id in ("", None):
        return None
    return str(claim_id)


def _set_manual_claim_id(device_name: str, manual_task_id: str | None):
    attributes = dict(device_view.get_all_attributes(device_name=device_name) or {})
    if manual_task_id is None:
        attributes.pop(MANUAL_CONTROL_ATTRIBUTE, None)
    else:
        attributes[MANUAL_CONTROL_ATTRIBUTE] = manual_task_id
    device_view.set_all_attributes(device_name=device_name, attributes=attributes)


def _normalize_result(value: Any):
    if isinstance(value, dict):
        return {str(key): _normalize_result(val) for key, val in value.items()}
    if isinstance(value, list):
        return [_normalize_result(item) for item in value]
    if isinstance(value, tuple):
        return [_normalize_result(item) for item in value]
    if hasattr(value, "value"):
        return value.value
    return value


def _coerce_value(value: Any, schema: dict[str, Any], field_name: str):
    value_type = schema["type"]
    if value_type == "int":
        try:
            coerced = int(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Parameter '{field_name}' must be an integer.") from exc
    elif value_type == "float":
        try:
            coerced = float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Parameter '{field_name}' must be a number.") from exc
    elif value_type == "bool":
        if isinstance(value, bool):
            coerced = value
        elif isinstance(value, str) and value.lower() in {"true", "false"}:
            coerced = value.lower() == "true"
        else:
            raise ValueError(f"Parameter '{field_name}' must be true or false.")
    else:
        coerced = value

    if "min" in schema and coerced < schema["min"]:
        raise ValueError(
            f"Parameter '{field_name}' must be >= {schema['min']}."
        )
    return coerced


def _validate_params(command_entry: dict[str, Any], params: dict[str, Any] | None):
    params = params or {}
    schema = command_entry["params"]
    unknown = sorted(set(params) - set(schema))
    if unknown:
        raise ValueError(f"Unexpected parameters: {', '.join(unknown)}")

    validated = {}
    for field_name, field_schema in schema.items():
        if field_name not in params:
            if field_schema.get("required"):
                raise ValueError(f"Missing required parameter '{field_name}'.")
            continue
        validated[field_name] = _coerce_value(
            params[field_name], field_schema, field_name
        )
    return validated


def _serialize_command(device_name: str, command_name: str, command: dict[str, Any]):
    return {
        "device_name": device_name,
        "command_name": command_name,
        "label": command["label"],
        "mode": command["mode"],
        "params": command["params"],
    }


def _get_catalog_entry(device_name: str):
    for entry in DEVICE_CATALOG:
        if entry["device_name"] == device_name:
            return entry
    raise ValueError(f"Unknown device '{device_name}'.")


def _get_device_runtime(device_name: str) -> dict[str, Any]:
    device_entry = device_view.get_device(device_name=device_name)
    manual_claim_id = _get_manual_claim_id(device_entry)
    dashboard_status = _parse_dashboard_status(
        device_entry["status"], device_entry["pause_status"]
    )
    is_manual_claim = (
        manual_claim_id is not None
        and device_entry.get("task_id") is not None
        and str(device_entry["task_id"]) == manual_claim_id
    )
    return {
        "dashboard_status": dashboard_status,
        "task_status": device_entry["status"],
        "pause_status": device_entry["pause_status"],
        "message": device_entry.get("message", ""),
        "task_id": str(device_entry["task_id"]) if device_entry.get("task_id") else None,
        "manual_task_id": manual_claim_id if is_manual_claim else None,
        "manual_claimed": is_manual_claim,
        "claim_state": (
            "Claimed by manual control"
            if is_manual_claim
            else "Unavailable"
            if dashboard_status != "IDLE"
            else "Unclaimed"
        ),
    }


def _require_implemented_device(device_name: str):
    if device_name not in COMMAND_REGISTRY:
        raise ValueError(f"Device '{device_name}' is not implemented in Device Control v1.")


def _require_manual_claim(device_name: str, manual_task_id: str):
    device_entry = device_view.get_device(device_name=device_name)
    manual_claim = _get_manual_claim_id(device_entry)
    if manual_claim is None:
        raise ValueError(f"Device '{device_name}' is not claimed for manual control.")
    if manual_claim != manual_task_id:
        raise ValueError("Manual claim token does not match the current device claim.")
    if device_entry.get("task_id") is None or str(device_entry["task_id"]) != manual_task_id:
        raise ValueError("Device occupier does not match the provided manual claim token.")


def _run_device_command(
    device_name: str,
    method: str,
    *,
    mode: str,
    manual_task_id: str | None,
    validated_params: dict[str, Any],
):
    """Run a device method through the Device Manager's connected drivers."""
    if mode == "actuate":
        if not manual_task_id:
            raise ValueError("Actuation commands require a manual device claim.")
        task_id = ObjectId(str(manual_task_id))
        require_occupation = True
    else:
        task_id = ObjectId()
        require_occupation = False

    client = DevicesClient(task_id=task_id)
    return client.call(
        device_name,
        method,
        require_occupation=require_occupation,
        **validated_params,
    )


@device_control_bp.route("/catalog", methods=["GET"])
def get_device_control_catalog():
    """Return the curated device list and current runtime state."""
    devices = []
    for entry in DEVICE_CATALOG:
        runtime = _get_device_runtime(entry["device_name"])
        commands = COMMAND_REGISTRY.get(entry["device_name"], {})
        devices.append(
            {
                **entry,
                **runtime,
                "allowlisted_commands": [
                    _serialize_command(entry["device_name"], name, command)
                    for name, command in commands.items()
                    if name not in BLOCKED_COMMANDS.get(entry["device_name"], set())
                ],
            }
        )
    return {"status": "success", "data": {"devices": devices}}


@device_control_bp.route("/claim", methods=["POST"])
def claim_device():
    """Claim a device for manual control."""
    data = request.get_json(force=True)  # type: ignore[arg-type]
    device_name = data.get("device_name")

    try:
        _require_implemented_device(device_name)
        runtime = _get_device_runtime(device_name)
        if runtime["dashboard_status"] != "IDLE":
            raise ValueError(
                f"Device '{device_name}' is not claimable because it is {runtime['dashboard_status']}."
            )
        manual_task_id = ObjectId()
        device_view.occupy_device(device_name, task_id=manual_task_id)
        _set_manual_claim_id(device_name, str(manual_task_id))
    except Exception as exception:
        return {"status": "error", "errors": str(exception)}, 400

    return {
        "status": "success",
        "data": {
            "device_name": device_name,
            "manual_task_id": str(manual_task_id),
        },
    }


@device_control_bp.route("/release", methods=["POST"])
def release_device():
    """Release a manual-control claim."""
    data = request.get_json(force=True)  # type: ignore[arg-type]
    device_name = data.get("device_name")
    manual_task_id = data.get("manual_task_id")

    try:
        _require_implemented_device(device_name)
        if not manual_task_id:
            raise ValueError("manual_task_id is required.")
        _require_manual_claim(device_name, str(manual_task_id))
        device_view.release_device(device_name=device_name)
        _set_manual_claim_id(device_name, None)
    except Exception as exception:
        return {"status": "error", "errors": str(exception)}, 400

    return {
        "status": "success",
        "data": {"device_name": device_name, "manual_task_id": manual_task_id},
    }


@device_control_bp.route("/command", methods=["POST"])
def execute_device_command():
    """Execute an allowlisted device command."""
    data = request.get_json(force=True)  # type: ignore[arg-type]
    device_name = data.get("device_name")
    command_name = data.get("command_name")
    manual_task_id = data.get("manual_task_id")
    params = data.get("params")

    try:
        _require_implemented_device(device_name)
        command_entry = COMMAND_REGISTRY[device_name].get(command_name)
        if command_entry is None or command_name in BLOCKED_COMMANDS.get(
            device_name, set()
        ):
            raise ValueError(
                f"Command '{command_name}' is not allowlisted for '{device_name}'."
            )
        validated_params = _validate_params(command_entry, params)
        if command_entry["mode"] == "actuate":
            if not manual_task_id:
                raise ValueError(
                    f"Command '{command_name}' requires a manual device claim."
                )
            try:
                ObjectId(str(manual_task_id))
            except (InvalidId, TypeError) as exc:
                raise ValueError("manual_task_id is not a valid ObjectId.") from exc
            _require_manual_claim(device_name, str(manual_task_id))
        result = _run_device_command(
            device_name=device_name,
            method=command_entry["target_method"],
            mode=command_entry["mode"],
            manual_task_id=str(manual_task_id) if manual_task_id else None,
            validated_params=validated_params,
        )
    except Exception as exception:
        return {"status": "error", "errors": str(exception)}, 400

    return {
        "status": "success",
        "data": {
            "device_name": device_name,
            "command_name": command_name,
            "mode": command_entry["mode"],
            "result": _normalize_result(result),
        },
    }
