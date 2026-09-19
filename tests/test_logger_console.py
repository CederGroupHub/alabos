"""Tests for Rich console color behavior in launch logs."""

from __future__ import annotations

from alab_management.utils import logger as logger_mod


def test_rich_console_no_color_when_forced_off(monkeypatch) -> None:
    monkeypatch.setenv("ALABOS_FORCE_COLOR", "0")
    monkeypatch.delenv("NO_COLOR", raising=False)
    console = logger_mod._rich_console()
    assert console.no_color is True


def test_rich_console_force_color(monkeypatch) -> None:
    monkeypatch.setenv("ALABOS_FORCE_COLOR", "1")
    monkeypatch.delenv("NO_COLOR", raising=False)
    console = logger_mod._rich_console()
    assert console.is_terminal is True
    assert console.no_color is False


def test_rich_console_respects_no_color(monkeypatch) -> None:
    monkeypatch.setenv("NO_COLOR", "1")
    monkeypatch.setenv("ALABOS_FORCE_COLOR", "1")
    console = logger_mod._rich_console()
    assert console.no_color is True


def test_rich_console_follows_stdout_isatty(monkeypatch) -> None:
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.delenv("ALABOS_FORCE_COLOR", raising=False)

    class _FakeStdout:
        def isatty(self) -> bool:
            return False

    monkeypatch.setattr(logger_mod.sys, "stdout", _FakeStdout())
    console = logger_mod._rich_console()
    assert console.is_terminal is False
