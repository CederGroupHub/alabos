"""Tests for launch service log helpers used by the Logs sidebar."""

from pathlib import Path

from alab_management.utils import launch_logging


def test_list_sources_without_env(monkeypatch) -> None:
    monkeypatch.delenv(launch_logging.ALABOS_LAUNCH_LOG_DIR_ENV, raising=False)
    sources = launch_logging.list_launch_log_sources()
    assert [s["id"] for s in sources] == [
        "lab",
        "alabos_launch",
        "alabos_worker",
        "alab_one_dashboard",
    ]
    assert all(s["available"] is False for s in sources)
    assert all(s["log_dir_configured"] is False for s in sources)


def test_list_and_tail_with_files(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv(launch_logging.ALABOS_LAUNCH_LOG_DIR_ENV, str(tmp_path))
    (tmp_path / "lab.log").write_text("one\ntwo\nthree\n", encoding="utf-8")
    sources = launch_logging.list_launch_log_sources()
    by_id = {s["id"]: s for s in sources}
    assert by_id["lab"]["available"] is True
    assert by_id["alabos_launch"]["available"] is False

    payload = launch_logging.read_launch_log_tail("lab", max_lines=2)
    assert payload["available"] is True
    assert payload["lines"] == ["two", "three"]


def test_unknown_source_raises() -> None:
    try:
        launch_logging.read_launch_log_tail("../etc/passwd")
        raise AssertionError("expected ValueError")
    except ValueError as exc:
        assert "Unknown log source" in str(exc)
