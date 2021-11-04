import time
from typing import Dict, Any

from .experiment_view.experiment import Experiment
from .experiment_view.experiment_view import ExperimentStatus, ExperimentView
from .sample_view import SampleView
from .task_view import TaskView, TaskStatus
from .utils.graph_op import Graph


class ExperimentManager:
    def __init__(self):
        self.experiment_view = ExperimentView()
        self.task_view = TaskView()
        self.sample_view = SampleView()

    def run(self):
        while True:
            self._loop()
            time.sleep(2)

    def _loop(self):
        self.handle_pending_experiments()
        self.mark_completed_experiments()

    def handle_pending_experiments(self):
        """
        This method will scan the database to find out if there are
        any pending experiments and submit it to task database
        """
        pending_experiments = self.experiment_view.get_experiments_with_status(ExperimentStatus.PENDING)
        for experiment in pending_experiments:
            self._handle_pending_experiment(experiment=experiment)

    def _handle_pending_experiment(self, experiment: Dict[str, Any]):
        experiment = Experiment(**experiment).dict()  # first do data validation
        samples = experiment["samples"]
        tasks = experiment["tasks"]
        sample_ids = [self.sample_view.create_sample(sample["name"]) for sample in samples]
        task_ids = [self.task_view.create_task(task_type=task["type"], parameters=task["parameters"])
                    for task in tasks]

        task_graph = Graph(task_ids, {i: next_task for i, next_task in enumerate(tasks["next_tasks"])})
        if task_graph.has_cycle():
            raise ValueError("Detect cycle in task graph, which is supposed to be a DAG (directed acyclic graph).")

        for task_id in task_ids:
            self.task_view.update_task_dependency(task_id, next_tasks=task_graph.get_children(task_id),
                                                  prev_tasks=task_graph.get_parents(task_id))

        self.experiment_view.assign_sample_task_id(exp_id=experiment["_id"],
                                                   sample_ids=sample_ids, task_ids=task_ids)
        self.experiment_view.set_experiment_status(exp_id=experiment["_id"],
                                                   status=ExperimentStatus.RUNNING)

    def mark_completed_experiments(self):
        """
        This method will scan the database to mark completed experiments in time
        """
        running_experiments = self.experiment_view.get_experiments_with_status(ExperimentStatus.RUNNING)
        for experiment in running_experiments:
            task_ids = [task["task_id"] for task in experiment["tasks"]]
            if all(self.task_view.get_status(task_id=task_id) is TaskStatus.COMPLETED
                   for task_id in task_ids):
                self.experiment_view.set_experiment_status(exp_id=experiment["_id"],
                                                           status=ExperimentStatus.COMPLETED)
