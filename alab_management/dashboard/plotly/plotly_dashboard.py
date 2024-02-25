"""This is a dashboard that displays data from the ALab database."""

from datetime import datetime, timedelta

import dash_mantine_components as dmc  # type: ignore
import pandas as pd
import plotly.express as px  # type: ignore
from dash import Dash, Input, Output, callback, dcc, html  # type: ignore

from .data_interface import get_samples, get_tasks

app = Dash(__name__)


sample_df = get_samples()
task_df = get_tasks()

earliest_date = min(sample_df.created_at.min(), task_df.started_at.min())


def build_task_row(task_type: str, task_df: pd.DataFrame = task_df):
    fig = px.scatter(
        data_frame=task_df[
            (task_df.status == "COMPLETED") & (task_df.type == task_type)
        ],
        x="completed_at",
        y="duration_minutes",
        height=100,
    )
    fig.update_layout(
        margin={"l": 0, "r": 0, "t": 0, "b": 0},
        xaxis_title="",
        yaxis_title="",
    )

    pie = px.pie(
        data_frame=task_df[(task_df.type == task_type)],
        names="status",
        height=100,
        hole=0.5,
        color="status",
        color_discrete_map={
            "COMPLETED": "#636EFA",
            "ERROR": "#EF553B",
            "RUNNING": "#00CC96",
            "WAITING": "#AB63FA",
            "CANCELLED": "#BAB0AC",
        },
    )
    pie.update_layout(
        margin={"l": 0, "r": 0, "t": 0, "b": 0},
        showlegend=False,
    )

    return dmc.Grid(
        [
            dmc.Col(
                [dmc.Text(task_type, align="left", size="md")],
                span=2,
            ),
            dmc.Col(
                [dcc.Graph(id=f"{task_type}-pie", figure=pie)],
                span=2,
            ),
            dmc.Col(
                [
                    dcc.Graph(id=f"{task_type}-graph", figure=fig),
                ],
                span=8,
            ),
        ]
    )


CONTROLS_LAYOUT = [
    dmc.Text("Controls", align="center", size="lg"),
    dmc.DateRangePicker(
        id="date-range-picker",
        label="Date Range",
        description="This will filter all data displayed in the graphs below.",
        minDate=earliest_date.date(),
        maxDate=datetime.now().date(),
        value=[datetime.now().date() - timedelta(days=30), datetime.now().date()],
    ),
]

SAMPLE_LAYOUT = [
    dmc.Text("Samples", align="center", size="lg"),
    dcc.Graph(
        id="completed-samples-graph",
        figure=px.histogram(
            sample_df,
            x="last_updated",
            labels={"last_updated": "Completed At"},
        ),
    ),
]

# TASK_LAYOUT = [
#     dmc.Text("Tasks", align="center", size="lg"),
# ] + [build_task_row(task_type) for task_type in task_df.type.unique()]

TASK_LAYOUT = [
    html.Div(id="task-table"),  # This is the callback output
]


app.layout = html.Div(CONTROLS_LAYOUT + SAMPLE_LAYOUT + TASK_LAYOUT)


@callback(
    Output("task-table", "children"),
    Input("date-range-picker", "value"),
)
def update_task_table(date_range):
    # print(date_range)
    filtered_task_df = task_df[
        (task_df.started_at >= date_range[0]) & (task_df.started_at <= date_range[1])
    ]
    return [
        dmc.Text("Tasks", align="center", size="lg"),
    ] + [
        build_task_row(task_type, filtered_task_df)
        for task_type in filtered_task_df.type.unique()
    ]


if __name__ == "__main__":
    app.run(debug=True)
