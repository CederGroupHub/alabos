"""Tests for Submissions free-form agent (no live SDK)."""

from __future__ import annotations

import time

import pytest

from alab_management.dashboard import submission_agent as agent
from alab_management.dashboard.submission_agent import SubmissionAgentError


@pytest.fixture(autouse=True)
def _clean_jobs():
    agent.reset_jobs_for_tests()
    yield
    agent.reset_jobs_for_tests()


def test_build_agent_prompt_mentions_single_device_limit() -> None:
    prompt = agent.build_agent_prompt(
        "heat 800 C for 3 h",
        device_name="BFT_box_d",
        sample_id="507f1f77bcf86cd799439011",
        sample_name="Andrea_1",
        physical_placement={"position": "BFT_box_d/slot/1"},
    )
    assert "ONE device" in prompt
    assert "Recipes" in prompt
    assert "BFT_box_d" in prompt
    assert "heat 800 C for 3 h" in prompt


def test_parse_draft_json() -> None:
    text = 'thinking...\nDRAFT_JSON={"heating_temperature_c": 900, "heating_duration_minutes": 120}\n'
    parsed = agent.parse_draft_json(text)
    assert parsed["heating_temperature_c"] == 900
    assert agent.parse_draft_json("no marker") is None


def test_start_freeform_job_requires_fields() -> None:
    with pytest.raises(SubmissionAgentError):
        agent.start_freeform_job({"prompt": "heat"})
    with pytest.raises(SubmissionAgentError, match="Recipes"):
        agent.start_freeform_job(
            {
                "prompt": "powder dosing then heat",
                "device_name": "BFT_box_d",
                "sample_id": "507f1f77bcf86cd799439011",
                "sample_name": "A_1",
            }
        )


def test_start_freeform_job_succeeds_with_local_parser() -> None:
    job = agent.start_freeform_job(
        {
            "prompt": "heat at 800 C for 3 hours",
            "device_name": "BFT_box_d",
            "sample_id": "507f1f77bcf86cd799439011",
            "sample_name": "Andrea_1",
            "reuse_existing": True,
            "physical_placement": {"position": "BFT_box_d/slot/3"},
        }
    )
    assert job["status"] in ("queued", "running", "succeeded")
    deadline = time.time() + 10
    current = job
    while time.time() < deadline:
        current = agent.get_job(job["id"])
        assert current is not None
        if current["status"] in ("succeeded", "failed"):
            break
        time.sleep(0.05)
    assert current["status"] == "succeeded"
    assert current["draft"]["experiment"]["tasks"][0]["type"] == "Heating"
    assert len(current["draft"]["experiment"]["tasks"]) == 1
