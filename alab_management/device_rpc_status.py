"""Probe whether the Device Manager RPC queue has a consumer (lab hardware ready)."""

from __future__ import annotations

import threading
import time
from typing import Any

CACHE_TTL_S = 2.5

_lock = threading.Lock()
_cache: dict[str, Any] | None = None
_cache_at: float = 0.0


def device_rpc_queue_name() -> str:
    """Return ``{lab}.device_rpc`` (or ``{lab}_sim.device_rpc`` in sim)."""
    from alab_management.config import AlabOSConfig

    config = AlabOSConfig()
    name = config["general"]["name"]
    if config.is_sim_mode():
        name = f"{name}_sim"
    return f"{name}.device_rpc"


def _probe_uncached() -> dict[str, Any]:
    queue = device_rpc_queue_name()
    try:
        import pika
        from alab_management.config import AlabOSConfig

        rabbit = AlabOSConfig()["rabbitmq"]
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(
                host=rabbit.get("host", "localhost"),
                port=rabbit.get("port", 5672),
                connection_attempts=1,
                socket_timeout=5,
            )
        )
    except Exception as exc:
        return {
            "ready": False,
            "queue": queue,
            "exists": False,
            "consumers": 0,
            "messages": 0,
            "detail": f"rabbit unreachable: {exc}",
        }

    try:
        channel = connection.channel()
        try:
            result = channel.queue_declare(queue=queue, passive=True)
            consumers = int(result.method.consumer_count)
            messages = int(result.method.message_count)
            ready = consumers >= 1
            if ready:
                detail = f"{consumers} consumer(s)"
            else:
                detail = "no consumer"
            return {
                "ready": ready,
                "queue": queue,
                "exists": True,
                "consumers": consumers,
                "messages": messages,
                "detail": detail,
            }
        except Exception:
            return {
                "ready": False,
                "queue": queue,
                "exists": False,
                "consumers": 0,
                "messages": 0,
                "detail": "queue missing",
            }
        finally:
            try:
                channel.close()
            except Exception:
                pass
    finally:
        try:
            connection.close()
        except Exception:
            pass


def get_device_rpc_status(*, force: bool = False) -> dict[str, Any]:
    """Return cached device_rpc readiness (RabbitMQ passive declare)."""
    global _cache, _cache_at
    now = time.monotonic()
    with _lock:
        if (
            not force
            and _cache is not None
            and (now - _cache_at) < CACHE_TTL_S
        ):
            return dict(_cache)

    status = _probe_uncached()
    with _lock:
        _cache = dict(status)
        _cache_at = time.monotonic()
    return status


def lab_ready_label(device_rpc: dict[str, Any] | None = None) -> str:
    """Operator-facing short label for AppBar / banners."""
    status = device_rpc or get_device_rpc_status()
    if status.get("ready"):
        return "Lab ready"
    detail = str(status.get("detail") or "")
    if "unreachable" in detail or not status.get("exists", True):
        if "unreachable" in detail:
            return "Devices not ready"
        return "Lab starting…"
    if status.get("exists") and status.get("consumers", 0) == 0:
        return "Lab starting…"
    return "Devices not ready"


def get_lab_readiness(*, force: bool = False) -> dict[str, Any]:
    """Combined lab_ready payload for status API and gates."""
    device_rpc = get_device_rpc_status(force=force)
    ready = bool(device_rpc.get("ready"))
    return {
        "lab_ready": ready,
        "lab_ready_label": lab_ready_label(device_rpc),
        "device_rpc": device_rpc,
    }


LAB_NOT_READY_ERROR = "Lab devices are not ready yet. Wait until the lab shows ready."

LAB_READY_WAIT_CONTEXT_KEY = "lab_ready_wait"
LAB_READY_WAIT_PROMPT = (
    "Lab devices are still starting. Submitted experiments will begin when the lab is ready."
)


def ensure_lab_starting_user_input() -> None:
    """Create at most one pending maintenance notice while the lab is not ready."""
    from alab_management.user_input import UserInputView

    view = UserInputView()
    existing = view.get_pending_request_by_context(
        {LAB_READY_WAIT_CONTEXT_KEY: True}
    )
    if existing is not None:
        return
    view.insert_request(
        prompt=LAB_READY_WAIT_PROMPT,
        options=["OK"],
        task_id=None,
        maintenance=True,
        category="Lab readiness",
        request_context_extra={LAB_READY_WAIT_CONTEXT_KEY: True},
    )


def dismiss_lab_starting_user_input() -> None:
    """Fulfill the lab-starting notice once the lab is ready."""
    from datetime import datetime

    from alab_management.user_input import UserInputView, UserRequestStatus

    view = UserInputView()
    existing = view.get_pending_request_by_context(
        {LAB_READY_WAIT_CONTEXT_KEY: True}
    )
    if existing is None:
        return
    view._input_collection.update_one(
        {"_id": existing["_id"], "status": UserRequestStatus.PENDING.value},
        {
            "$set": {
                "status": UserRequestStatus.FULLFILLED.value,
                "response": "OK",
                "note": "Lab is ready.",
                "last_updated": datetime.now(),
            }
        },
    )


def require_lab_ready_or_503():
    """Return a Flask (body, status) tuple when not ready, else None."""
    readiness = get_lab_readiness()
    if readiness["lab_ready"]:
        return None
    return (
        {
            "status": "error",
            "errors": LAB_NOT_READY_ERROR,
            "lab_ready": False,
            "lab_ready_label": readiness["lab_ready_label"],
        },
        503,
    )
