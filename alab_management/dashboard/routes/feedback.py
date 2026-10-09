"""Dashboard software-feedback API (Slack DM lane, not lab channel alerts)."""

from __future__ import annotations

from datetime import datetime, timezone

from flask import Blueprint, jsonify, request
from slack_sdk.errors import SlackApiError

from alab_management.alarm import Alarm
from alab_management.config import AlabOSConfig

feedback_bp = Blueprint("feedback", __name__, url_prefix="/api/feedback")

_MAX_MESSAGE_LEN = 4000


@feedback_bp.route("", methods=["POST"])
@feedback_bp.route("/", methods=["POST"])
def submit_feedback():
    """Send operator software/UI feedback as a Slack DM to ``feedback_slack_user_id``."""
    data = request.get_json(silent=True) or {}
    message = data.get("message", "")
    if not isinstance(message, str):
        return jsonify({"status": "error", "reason": "message must be a string."}), 400
    message = message.strip()
    if not message:
        return jsonify({"status": "error", "reason": "message is required."}), 400
    if len(message) > _MAX_MESSAGE_LEN:
        return (
            jsonify(
                {
                    "status": "error",
                    "reason": f"message must be at most {_MAX_MESSAGE_LEN} characters.",
                }
            ),
            400,
        )

    page = data.get("page", "")
    if not isinstance(page, str):
        page = ""
    page = page.strip()[:500]

    alarm_config = AlabOSConfig().get("alarm", {}) or {}
    alarm = Alarm(**alarm_config)

    if alarm.sim_mode_flag:
        return (
            jsonify(
                {
                    "status": "error",
                    "reason": "Feedback is disabled in simulation mode.",
                }
            ),
            503,
        )
    if not alarm.slack_bot_token:
        return (
            jsonify(
                {
                    "status": "error",
                    "reason": (
                        "Slack is not configured "
                        "(set ALABOS_ALARM_SLACK_BOT_TOKEN on the host)."
                    ),
                }
            ),
            503,
        )
    if not alarm.feedback_slack_user_id:
        return (
            jsonify(
                {
                    "status": "error",
                    "reason": (
                        "feedback_slack_user_id is not set in [alarm] config."
                    ),
                }
            ),
            503,
        )

    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    parts = [message, "", f"Time: {stamp}"]
    if page:
        parts.append(f"Page: {page}")
    body = "\n".join(parts)

    try:
        alarm.send_slack_dm(body, "Dashboard feedback")
    except SlackApiError as exc:
        return (
            jsonify(
                {
                    "status": "error",
                    "reason": f"Slack API error: {exc.response.get('error', exc)}",
                }
            ),
            502,
        )
    except Exception as exc:  # noqa: BLE001 — surface to dashboard
        return jsonify({"status": "error", "reason": str(exc)}), 500

    return jsonify({"status": "success"})
