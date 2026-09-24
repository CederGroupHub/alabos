"""Tests for Data page Cursor report agent jobs (no live SDK)."""

from __future__ import annotations

import threading
from unittest.mock import MagicMock

import pytest

from alab_management.dashboard import report_agent as agent
from alab_management.dashboard.report_agent import ReportAgentError


@pytest.fixture(autouse=True)
def _clean_jobs():
    agent.reset_jobs_for_tests()
    yield
    agent.reset_jobs_for_tests()


def test_build_agent_prompt_includes_pipeline_and_user_text() -> None:
    prompt = agent.build_agent_prompt(
        "list samples with name",
        dashboard_base="http://127.0.0.1:8895",
    )
    assert "user_reports/<slug>.py" in prompt
    assert "REPORT_NAME=<slug>" in prompt
    assert "http://127.0.0.1:8895/api/data/reports" in prompt
    assert "list samples with name" in prompt


def test_parse_report_name_takes_last_match() -> None:
    text = "working…\nREPORT_NAME=first_one\nmore\nREPORT_NAME=final_slug\n"
    assert agent.parse_report_name(text) == "final_slug"
    assert agent.parse_report_name("no marker") is None
    assert agent.parse_report_name("REPORT_NAME=Bad") is None


def test_start_report_job_requires_prompt(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CURSOR_API_KEY", "cursor_test")
    monkeypatch.setitem(__import__("sys").modules, "cursor_sdk", MagicMock())
    with pytest.raises(ReportAgentError) as exc:
        agent.start_report_job("   ")
    assert exc.value.status_code == 400


def test_start_report_job_requires_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CURSOR_API_KEY", raising=False)
    with pytest.raises(ReportAgentError) as exc:
        agent.start_report_job("make a sample table")
    assert exc.value.status_code == 503
    assert "CURSOR_API_KEY" in str(exc.value)


def test_start_report_job_requires_sdk(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CURSOR_API_KEY", "cursor_test")

    import builtins

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "cursor_sdk" or name.startswith("cursor_sdk."):
            raise ImportError("no sdk")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    with pytest.raises(ReportAgentError) as exc:
        agent.start_report_job("make a sample table")
    assert exc.value.status_code == 503
    assert "cursor-sdk" in str(exc.value)


def test_start_report_job_rejects_when_busy(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CURSOR_API_KEY", "cursor_test")
    monkeypatch.setitem(__import__("sys").modules, "cursor_sdk", MagicMock())

    started = threading.Event()
    release = threading.Event()

    def fake_run(job_id, user_prompt, names_before):
        agent._set_job_fields(job_id, status="running")
        started.set()
        release.wait(timeout=5)
        agent._set_job_fields(job_id, status="succeeded", report_name="demo")

    monkeypatch.setattr(agent, "_run_sdk_job", fake_run)
    monkeypatch.setattr(agent, "_catalog_names", lambda: set())

    first = agent.start_report_job("first request")
    assert first["status"] == "queued"
    assert started.wait(timeout=2)

    with pytest.raises(ReportAgentError) as exc:
        agent.start_report_job("second request")
    assert exc.value.status_code == 409

    release.set()
    # Allow background thread to finish and clear _active_thread.
    thread = agent._active_thread
    if thread is not None:
        thread.join(timeout=2)
