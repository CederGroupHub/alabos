"""The dashboard must import, and `create_app()` must work, without the lab-specific `alab_one`."""

from __future__ import annotations

import importlib
import sys
from contextlib import contextmanager

import pytest

BLOCKED = "alab_one"
# Re-imported under the block; `lab_views` is left cached so no new Mongo connection is opened.
RELOADED = (
    "alab_management.dashboard",
    "alab_management.dashboard.routes",
    "alab_management.dashboard.submission_agent",
)


class _BlockAlabOne:
    """Meta-path finder that makes `alab_one` unimportable even when it is installed."""

    def find_spec(self, fullname, path=None, target=None):
        if fullname == BLOCKED or fullname.startswith(BLOCKED + "."):
            raise ModuleNotFoundError(f"No module named {fullname!r}", name=fullname)
        return None


def _purged_names() -> list[str]:
    return [
        name
        for name in list(sys.modules)
        if name == BLOCKED
        or name.startswith(BLOCKED + ".")
        or name in RELOADED
        or name.startswith("alab_management.dashboard.routes.")
    ]


@contextmanager
def alab_one_unavailable():
    saved = {name: sys.modules.pop(name) for name in _purged_names()}
    blocker = _BlockAlabOne()
    sys.meta_path.insert(0, blocker)
    try:
        yield
    finally:
        sys.meta_path.remove(blocker)
        for name in _purged_names():
            del sys.modules[name]
        sys.modules.update(saved)


def test_alab_one_is_really_blocked() -> None:
    with alab_one_unavailable(), pytest.raises(ModuleNotFoundError):
        importlib.import_module("alab_one.submissions.freeform")


def test_routes_package_imports_without_alab_one() -> None:
    with alab_one_unavailable():
        routes = importlib.import_module("alab_management.dashboard.routes")
        assert routes.submissions_bp is not None


def test_create_app_without_alab_one_keeps_submission_routes() -> None:
    with alab_one_unavailable():
        dashboard = importlib.import_module("alab_management.dashboard")
        app = dashboard.create_app()
        rules = {rule.rule for rule in app.url_map.iter_rules()}
        assert "/api/submissions/freeform/jobs" in rules


def test_freeform_job_fails_at_call_time_with_a_clear_message() -> None:
    with alab_one_unavailable():
        agent = importlib.import_module("alab_management.dashboard.submission_agent")
        with pytest.raises(agent.SubmissionAgentError) as excinfo:
            agent.start_freeform_job(
                {
                    "prompt": "heat at 800 C for 3 hours",
                    "device_name": "BFT_box_d",
                    "sample_id": "507f1f77bcf86cd799439011",
                    "sample_name": "Andrea_1",
                }
            )
        assert BLOCKED in str(excinfo.value)
        assert excinfo.value.status_code == 503
