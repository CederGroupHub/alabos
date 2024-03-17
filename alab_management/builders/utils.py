"""This module contains utility functions for the builders module."""

from typing import TYPE_CHECKING

from bson import ObjectId  # type: ignore

from .experimentbuilder import ExperimentBuilder
from .samplebuilder import SampleBuilder

if TYPE_CHECKING:
    from alab_management import BaseTask


def append_task(
    task: "BaseTask",
    samples: SampleBuilder | list[SampleBuilder],
):
    """
    Used to add basetask to a SampleBuilder's tasklist during Experiment construction.

    Args:
        task (BaseTask): The task to be added to the SampleBuilder's tasklist.
        samples (Union[SampleBuilder, List[SampleBuilder]]): One or more SampleBuilder's which will
        have this task appended to their tasklists.
    """
    if not task.is_simulation:
        raise RuntimeError(
            "Cannot add a live BaseTask instance to a SampleBuilder. BaseTask must be instantiated with "
            "`simulation=True` to enable this method."
        )
    if isinstance(samples, SampleBuilder):
        samples = [samples]

    if len({sample.experiment for sample in samples}) != 1:
        raise ValueError("All samples must be from the same experiment to add a task.")
    experiment: ExperimentBuilder = samples[0].experiment

    task_id = str(ObjectId())
    experiment.add_task(
        task_id=task_id,
        task_name=task.__class__.__name__,
        task_kwargs=task.subclass_kwargs,
        samples=samples,
    )
    for sample in samples:
        sample.add_task(task_id=task_id)
