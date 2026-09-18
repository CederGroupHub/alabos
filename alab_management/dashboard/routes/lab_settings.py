"""Lab settings dashboard APIs: idle gate, clear occupancy, and related actions."""

from __future__ import annotations

from flask import Blueprint, jsonify

from alab_management.lab_reset import (
    LabNotIdleError,
    clear_lab_occupancy,
    get_lab_idle_status,
    reset_lab_software_state,
)

lab_settings_bp = Blueprint(
    "lab_settings", __name__, url_prefix="/api/lab-settings"
)


@lab_settings_bp.route("/idle", methods=["GET"])
def lab_idle():
    """Return whether the lab is idle enough for destructive settings actions."""
    return jsonify({"status": "success", "data": get_lab_idle_status()})


@lab_settings_bp.route("/clear_occupancy", methods=["POST"])
def clear_occupancy():
    """Null every sample position; keep identity, last_position, and history."""
    try:
        summary = clear_lab_occupancy()
    except LabNotIdleError as exc:
        return (
            jsonify(
                {
                    "status": "error",
                    "reason": str(exc),
                    "data": {"idle": False, "reasons": exc.reasons},
                }
            ),
            409,
        )
    except Exception as exc:  # noqa: BLE001 — surface to dashboard
        return jsonify({"status": "error", "reason": str(exc)}), 500
    return jsonify({"status": "success", "data": summary})


@lab_settings_bp.route("/reset_lab", methods=["POST"])
def reset_lab():
    """Same as ``/api/experiment/reset_lab`` — kept here for Lab settings UI."""
    try:
        summary = reset_lab_software_state()
    except Exception as exc:  # noqa: BLE001
        return jsonify({"status": "error", "reason": str(exc)}), 500
    return jsonify({"status": "success", "data": summary})
