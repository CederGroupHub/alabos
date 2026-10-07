"""This file contains a helper object to manage resources and update sample positions."""

from alab_management.device_view import DeviceView
from alab_management.experiment_view import ExperimentView
from alab_management.sample_view import SampleView
from alab_management.sample_view.analysis_view import AnalysisView
from alab_management.task_view import TaskView
from alab_management.user_input import UserInputView

task_view = TaskView()
sample_view = SampleView()
# The analysis Data API routes and any in-process caller share this one implementation (data-architecture D9).
analysis_view = AnalysisView(sample_view)
device_view = DeviceView()
experiment_view = ExperimentView()
user_input_view = UserInputView()
