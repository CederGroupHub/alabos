"""
Experiment manager for the ALAB.

It is responsible for parsing the incoming experiment requests into many
tasks and samples and mark the finished tasks in the database when it is
done.
"""

import time
from typing import Dict, Any

from .experiment_view.experiment_view import ExperimentStatus, ExperimentView
from .logger import DBLogger
from .sample_view import SampleView
from .task_view import TaskView, TaskStatus
from .utils.graph_ops import Graph


class ExperimentManager:
    """
    Experiment manager read experiments from the experiment collection
    and submit the experiment to executor and flag the completed experiments
    """

    def __init__(self):
        self.experiment_view = ExperimentView()
        self.task_view = TaskView()
        self.sample_view = SampleView()
        self.logger = DBLogger(task_id=None)

    def run(self):
        """
        Start the event loop
        """
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
        pending_experiments = self.experiment_view. \
            get_experiments_with_status(ExperimentStatus.PENDING)
        for experiment in pending_experiments:
            self._handle_pending_experiment(experiment=experiment)
            self.logger.system_log(level="DEBUG", log_data={
                "logged_by": self.__class__.__name__,
                "type": "ExperimentStarted",
                "exp_id": experiment['_id'],
            })

    def _handle_pending_experiment(self, experiment: Dict[str, Any]):
        samples = experiment["samples"]
        tasks = experiment["tasks"]

        # check if there is any cycle in the graph
        reversed_edges = {i: task["prev_tasks"] for i, task in enumerate(tasks)}
        task_graph = Graph(
            list(range(len(tasks))),
            # reverse reserved edges to get right directions of edges
            {i: [j for j, children in reversed_edges.items() for child in children if child == i]
             for i in list(range(len(tasks)))}
        )
        if task_graph.has_cycle():
            raise ValueError("Detect cycle in task graph, which is supposed "
                             "to be a DAG (directed acyclic graph).")

        # create samples in the sample database
        sample_ids = {sample["name"]: self.sample_view.create_sample(sample["name"])
                      for sample in samples}

        # create tasks in the task database
        task_ids = []
        for task in tasks:
            samples = {k: sample_ids[v] for k, v in task["samples"].items()}
            task_ids.append(self.task_view.create_task(task_type=task["type"],
                                                       parameters=task["parameters"],
                                                       samples=samples))

        # change the content of graph's vertices
        task_graph.vertices = task_ids

        # add dependency to each task
        for task_id in task_ids:
            self.task_view.update_task_dependency(task_id, next_tasks=task_graph.get_children(task_id),
                                                  prev_tasks=task_graph.get_parents(task_id))
            self.task_view.try_to_mark_task_ready(task_id)

        # write back the assign task & sample ids
        self.experiment_view.update_sample_task_id(exp_id=experiment["_id"], sample_ids=list(sample_ids.values()),
                                                   task_ids=task_ids)

        # update the status of experiment to RUNNING (have handled by experiment manager)
        self.experiment_view.update_experiment_status(exp_id=experiment["_id"], status=ExperimentStatus.RUNNING)

    def mark_completed_experiments(self):
        """
        This method will scan the database to mark completed experiments in time
        """
        running_experiments = self.experiment_view.get_experiments_with_status(ExperimentStatus.RUNNING)
        for experiment in running_experiments:
            task_ids = [task["task_id"] for task in experiment["tasks"]]

            # if all the tasks of an experiment have been finished
            if all(self.task_view.get_status(task_id=task_id) is TaskStatus.COMPLETED
                   for task_id in task_ids):
                self.experiment_view.update_experiment_status(exp_id=experiment["_id"],
                                                              status=ExperimentStatus.COMPLETED)
                self.logger.system_log(level="DEBUG", log_data={
                    "logged_by": self.__class__.__name__,
                    "type": "ExperimentCompleted",
                    "exp_id": experiment['_id'],
                })
                print(f"Experiment ({experiment['_id']}) completed.")
