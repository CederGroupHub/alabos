"""Per-device detail and device signal history.

``/api/status`` is a summary of the whole lab and is polled every second, so it stays deliberately
thin. These routes are for looking closely at one device: its full stored state, and the signals it
has been logging through ``@log_signal`` / ``DBLogger.log_device_signal``, which until now were
written to the database and never readable from the dashboard.
"""

from datetime import timedelta

from flask import Blueprint, request

from alab_management.dashboard.lab_views import device_view, sample_view
from alab_management.logger import DBLogger
from alab_management.utils.data_objects import make_jsonable

from .status import describe_sample, parse_device_status, published_attributes

device_bp = Blueprint("/device", __name__, url_prefix="/api/device")

#: Ceiling on how far back a signal query may reach, so a mistyped query cannot ask the database for
#: the entire history of a device that logs every few seconds.
MAX_SIGNAL_WINDOW = timedelta(days=30)

#: Ceiling on how many samples of one signal are returned, applied after the time window. The most
#: recent points are kept, since a chart of the last few hundred readings is what a plot needs.
MAX_SIGNAL_POINTS = 5000


@device_bp.route("/<device_name>", methods=["GET"])
def get_device(device_name: str):
    """Everything known about one device: definition, status, attributes and samples on it.

    Unlike ``/api/status`` this returns all stored attributes, not only the published subset, and
    names which of them the device asked to have shown so a client can highlight those first.
    """
    try:
        device = device_view.get_device(device_name=device_name)
    except ValueError as exception:
        return {"status": "error", "errors": str(exception)}, 404

    data = {
        "name": device["name"],
        "type": device["type"],
        "description": device.get("description", ""),
        "task_status": device["status"],
        "pause_status": device["pause_status"],
        "status": parse_device_status(device["status"], device["pause_status"]),
        "message": device.get("message", ""),
        "task": str(device["task_id"]) if device.get("task_id") is not None else None,
        "sample_positions": device.get("sample_positions", []),
        "dashboard_attributes": device.get("dashboard_attributes", []),
        "published_attributes": published_attributes(device),
        "attributes": device.get("attributes", {}),
        "samples": {
            position: [describe_sample(sample_id) for sample_id in samples]
            for position, samples in sample_view.get_samples_on_device(
                device_name
            ).items()
        },
        "last_updated": device.get("last_updated"),
        "created_at": device.get("created_at"),
    }
    return make_jsonable({"status": "success", "data": data})


@device_bp.route("/<device_name>/signals", methods=["GET"])
def get_device_signals(device_name: str):
    """Recorded signal history for a device.

    Query parameters:

    - ``signal``: repeatable. Which signals to return. Omit to get the latest value of every signal
      this device has ever logged, which is the cheap call a dashboard can poll.
    - ``hours``: how far back to look, default 1, capped at 30 days. Only applies when ``signal`` is
      given; without it only the latest value per signal is returned.
    """
    try:
        device_view.get_device(device_name=device_name)
    except ValueError as exception:
        return {"status": "error", "errors": str(exception)}, 404

    logger = DBLogger(task_id=None)
    requested = request.args.getlist("signal")

    if not requested:
        return make_jsonable(
            {
                "status": "success",
                "data": {
                    "device_name": device_name,
                    "latest": [
                        logger.get_latest_device_signal(
                            device_name=device_name, signal_name=signal_name
                        )
                        for signal_name in _known_signal_names(logger, device_name)
                    ],
                },
            }
        )

    try:
        hours = float(request.args.get("hours", 1))
    except ValueError:
        return {"status": "error", "errors": "hours must be a number"}, 400
    if hours <= 0:
        return {"status": "error", "errors": "hours must be positive"}, 400
    within = min(timedelta(hours=hours), MAX_SIGNAL_WINDOW)

    series = []
    for signal_name in requested:
        data = logger.filter_device_signal(
            device_name=device_name, signal_name=signal_name, within=within
        )
        # Keep the newest points when a signal has been logged more often than we will return.
        if len(data["timestamp"]) > MAX_SIGNAL_POINTS:
            data["timestamp"] = data["timestamp"][-MAX_SIGNAL_POINTS:]
            data["value"] = data["value"][-MAX_SIGNAL_POINTS:]
            data["truncated"] = True
        series.append(data)

    return make_jsonable(
        {
            "status": "success",
            "data": {
                "device_name": device_name,
                "within_hours": within.total_seconds() / 3600,
                "signals": series,
            },
        }
    )


def _known_signal_names(logger: DBLogger, device_name: str) -> list[str]:
    """Every signal name this device has ever logged, oldest name first."""
    names = logger._logging_collection.distinct(  # noqa: SLF001
        "log_data.signal_name",
        {"type": "DEVICE_SIGNAL", "log_data.device_name": device_name},
    )
    return sorted(name for name in names if name)
