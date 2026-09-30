"""Tests for alab-data-reports MCP helpers (HTTP mocked)."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from alab_management import mcp_data_reports as mcp


def _ok(payload: dict) -> MagicMock:
    resp = MagicMock()
    resp.read.return_value = json.dumps(payload).encode("utf-8")
    resp.__enter__.return_value = resp
    resp.__exit__.return_value = False
    return resp


@patch("alab_management.mcp_data_reports.urllib.request.urlopen")
def test_list_data_reports(mock_urlopen: MagicMock) -> None:
    mock_urlopen.return_value = _ok(
        {"status": "success", "reports": [{"name": "sample_report"}]}
    )
    out = mcp.list_data_reports()
    assert out["reports"][0]["name"] == "sample_report"
    req = mock_urlopen.call_args[0][0]
    assert req.full_url.endswith("/api/data/reports")
    assert req.get_method() == "GET"


@patch("alab_management.mcp_data_reports.urllib.request.urlopen")
def test_register_and_refresh(mock_urlopen: MagicMock) -> None:
    mock_urlopen.side_effect = [
        _ok({"status": "success", "report": {"name": "demo_report"}}),
        _ok({"status": "success", "report": {"name": "demo_report", "rows": []}}),
    ]
    reg = mcp.register_data_report(name="demo_report", title="Demo")
    assert reg["report"]["name"] == "demo_report"
    ref = mcp.refresh_data_report("demo_report", start="2026-01-01", end="2026-01-31")
    assert ref["status"] == "success"
    assert mock_urlopen.call_count == 2


@patch("alab_management.mcp_data_reports.urllib.request.urlopen")
def test_update_and_delete(mock_urlopen: MagicMock) -> None:
    mock_urlopen.side_effect = [
        _ok({"status": "success", "report": {"name": "demo", "title": "New"}}),
        _ok({"status": "success", "name": "demo"}),
    ]
    upd = mcp.update_data_report("demo", title="New")
    assert upd["report"]["title"] == "New"
    deleted = mcp.delete_data_report("demo")
    assert deleted["name"] == "demo"


def test_handle_tools_list() -> None:
    resp = mcp.handle_message({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
    assert resp is not None
    names = {t["name"] for t in resp["result"]["tools"]}
    assert names == {
        "list_data_reports",
        "register_data_report",
        "update_data_report",
        "delete_data_report",
        "refresh_data_report",
        "get_data_report_rows",
    }


@patch("alab_management.mcp_data_reports.list_data_reports")
def test_handle_tools_call(mock_list: MagicMock) -> None:
    mock_list.return_value = {"status": "success", "reports": []}
    resp = mcp.handle_message(
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {"name": "list_data_reports", "arguments": {}},
        }
    )
    assert resp["result"]["isError"] is False
    assert "success" in resp["result"]["content"][0]["text"]


def test_call_tool_unknown() -> None:
    with pytest.raises(ValueError, match="Unknown tool"):
        mcp.call_tool("nope", {})
