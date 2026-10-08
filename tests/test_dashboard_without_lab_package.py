"""Core AlabOS dashboard must import and serve without the lab-specific ``alab_one`` package."""

from __future__ import annotations

import importlib
import sys
from contextlib import contextmanager

import pytest

BLOCKED = "alab_one"
RELOADED = (
    "alab_management.dashboard",
    "alab_management.dashboard.routes",
)


class _BlockAlabOne:
    """Meta-path finder that makes ``alab_one`` unimportable even when it is installed."""

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
        assert routes.device_bp is not None
        assert not hasattr(routes, "submissions_bp")


def test_create_app_without_alab_one_omits_submissions_routes() -> None:
    with alab_one_unavailable():
        dashboard = importlib.import_module("alab_management.dashboard")
        app = dashboard.create_app()
        rules = {rule.rule for rule in app.url_map.iter_rules()}
        assert "/api/device" in "".join(rules) or any(
            r.startswith("/api/device") for r in rules
        )
        assert not any(r.startswith("/api/submissions") for r in rules)
