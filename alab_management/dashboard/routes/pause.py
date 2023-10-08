"""
Routes for pausing and unpausing devices. Pause is a request to pause a device. Unpause is a request to release a
device from pause.
"""

from flask import Blueprint, request

from alab_management.dashboard.lab_views import device_view

pause_bp = Blueprint("/pause", __name__, url_prefix="/api/pause")


@pause_bp.route("/request", methods=["POST"])
def request_device_pause():
    """Request a device to pause. Pause will be fulfilled when the device goes idle (ie completes current task)."""
    data = request.get_json(force=True)  # type: ignore
    try:
        device_view.pause_device(device_name=data["device_name"])
    except Exception as exception:
        return {"status": "error", "errors": exception.args[0]}, 400

    return {"status": "success", "data": data}


@pause_bp.route("/release", methods=["POST"])
def release_device_pause():
    """Release a device from pause. If the pause had not yet been fulfilled, the request is cancelled. If the Device
    had been paused, it will now be available for new Tasks.
    """
    data = request.get_json(force=True)  # type: ignore
    try:
        device_view.unpause_device(device_name=data["device_name"])
    except Exception as exception:
        return {"status": "error", "errors": exception.args[0]}, 400
    return {"status": "success", "data": data}
