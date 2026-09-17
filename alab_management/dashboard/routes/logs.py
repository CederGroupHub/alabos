"""Dashboard API for per-launch service logs (Lab / alabos launch / worker / …)."""

from flask import Blueprint, request

from alab_management.utils.device_verbose_logging import (
    DEFAULT_VERBOSE_LOG_TAIL,
    MAX_VERBOSE_LOG_TAIL,
)
from alab_management.utils.data_objects import make_jsonable
from alab_management.utils.launch_logging import (
    list_launch_log_sources,
    read_launch_log_tail,
)

logs_bp = Blueprint("/logs", __name__, url_prefix="/api/logs")


@logs_bp.route("/sources", methods=["GET"])
def get_log_sources():
    """List the fixed Logs sidebar tabs and whether each file exists."""
    return make_jsonable(
        {
            "status": "success",
            "data": {"sources": list_launch_log_sources()},
        }
    )


@logs_bp.route("/tail/<source_id>", methods=["GET"])
def get_log_tail(source_id: str):
    """Trailing lines for one launch-log source (sandboxed filenames only)."""
    try:
        max_lines = int(request.args.get("lines", DEFAULT_VERBOSE_LOG_TAIL))
    except ValueError:
        return {"status": "error", "errors": "lines must be a number"}, 400
    max_lines = max(1, min(max_lines, MAX_VERBOSE_LOG_TAIL))

    try:
        payload = read_launch_log_tail(source_id, max_lines)
    except ValueError as exception:
        return {"status": "error", "errors": str(exception)}, 400

    return make_jsonable({"status": "success", "data": payload})
