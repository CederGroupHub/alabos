"""Prometheus BFT → DASH segment control routes for the AlabOS dashboard."""

from __future__ import annotations

from flask import Blueprint, request

bft_control_bp = Blueprint(
    "/bft-control", __name__, url_prefix="/api/bft-control"
)


def _handle_request(handler, *, segment_id: str | None = None, parse_json: bool = False):
    try:
        body = request.get_json(silent=True) or {} if parse_json else {}
        if segment_id is None:
            data = handler()
        else:
            data = handler(segment_id, body)
        return {"status": "success", "data": data}
    except ValueError as error:
        return {"status": "error", "errors": str(error)}, 400
    except Exception as error:
        return {"status": "error", "errors": str(error)}, 400


@bft_control_bp.route("/catalog", methods=["GET"])
def get_bft_control_catalog():
    """List curated Prometheus BFT → DASH transfers."""
    from alab_one.bft_control.service import get_catalog

    return _handle_request(get_catalog)


@bft_control_bp.route("/preview/<segment_id>", methods=["POST"])
def preview_bft_segment(segment_id: str):
    """Build a batch for the segment without submitting it."""
    from alab_one.bft_control.service import preview_batch

    return _handle_request(preview_batch, segment_id=segment_id, parse_json=True)


@bft_control_bp.route("/run/<segment_id>", methods=["POST"])
def run_bft_segment(segment_id: str):
    """Build and submit a Prometheus BFT → DASH batch to AlabOS."""
    from alab_one.bft_control.service import run_batch

    return _handle_request(run_batch, segment_id=segment_id, parse_json=True)
