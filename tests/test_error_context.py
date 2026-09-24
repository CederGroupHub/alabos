from alab_management.utils.error_context import TRACEBACK_HEADER, format_error_report


def test_format_error_report_splits_what_and_cause() -> None:
    try:
        try:
            raise RuntimeError("delivery request was cancelled")
        except RuntimeError as inner:
            raise RuntimeError("Error in thread for sample 'S1'") from inner
    except RuntimeError as exc:
        report = format_error_report(
            exc=exc,
            task_type="Moving",
            task_id="abc123",
            samples=["S1"],
            header="Task failed",
        )

    assert report.startswith("ERROR: Task failed in Moving")
    assert "- What: RuntimeError" in report
    assert "Error in thread for sample 'S1'" in report
    assert "- Cause: RuntimeError" in report
    assert "delivery request was cancelled" in report
    assert "- Task: Moving (id: abc123)" in report
    assert "- Samples: S1" in report
    assert TRACEBACK_HEADER in report
    # Summary comes before the traceback and is not one mashed line.
    summary = report.split(TRACEBACK_HEADER, 1)[0]
    assert summary.count("\n") >= 5


def test_format_error_report_without_cause_keeps_what() -> None:
    try:
        raise ValueError("bad vial")
    except ValueError as exc:
        report = format_error_report(exc=exc, header="An error occurred")

    assert "- What: ValueError" in report
    assert "bad vial" in report
    assert "- Cause:" not in report
