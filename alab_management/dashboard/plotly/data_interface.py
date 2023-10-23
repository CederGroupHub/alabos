"""Plotly dashboard for ALAB management."""

import pandas as pd

from alab_management.sample_view import CompletedSampleView, SampleView
from alab_management.task_view import CompletedTaskView, TaskView


def get_samples() -> pd.DataFrame:
    sv = SampleView()
    svc = CompletedSampleView()
    all_samples = list(sv._sample_collection.find({}))

    sdf = pd.DataFrame(all_samples)
    csdf = pd.DataFrame(list(svc._completed_sample_collection.find({})))

    df = pd.concat([sdf, csdf]).reset_index()

    df["last_updated"] = df["last_updated"].astype("datetime64")
    df["created_at"] = df["created_at"].astype("datetime64")

    return df


def get_tasks() -> pd.DataFrame:
    tv = TaskView()
    tvc = CompletedTaskView()

    all_tasks = list(tv._task_collection.find({}))
    tdf = pd.DataFrame(all_tasks)
    ctdf = pd.DataFrame(list(tvc._completed_task_collection.find({})))
    tdf = pd.concat([tdf, ctdf]).reset_index()

    tdf["duration_minutes"] = (tdf["completed_at"] - tdf["started_at"]).apply(
        lambda x: x.total_seconds() / 60
    )

    return tdf
