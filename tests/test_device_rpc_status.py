"""Unit tests for lab readiness / device_rpc probe helpers."""

from alab_management.device_rpc_status import lab_ready_label


def test_lab_ready_label_when_ready() -> None:
    assert (
        lab_ready_label(
            {
                "ready": True,
                "exists": True,
                "consumers": 1,
                "detail": "1 consumer(s)",
            }
        )
        == "Lab ready"
    )


def test_lab_ready_label_when_starting() -> None:
    assert (
        lab_ready_label(
            {
                "ready": False,
                "exists": True,
                "consumers": 0,
                "detail": "no consumer",
            }
        )
        == "Lab starting..."
    )


def test_lab_ready_label_when_queue_missing() -> None:
    assert (
        lab_ready_label(
            {
                "ready": False,
                "exists": False,
                "consumers": 0,
                "detail": "queue missing",
            }
        )
        == "Lab starting..."
    )


def test_lab_ready_label_when_rabbit_down() -> None:
    assert (
        lab_ready_label(
            {
                "ready": False,
                "exists": False,
                "consumers": 0,
                "detail": "rabbit unreachable: boom",
            }
        )
        == "Devices not ready"
    )
