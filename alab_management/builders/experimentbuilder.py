from pathlib import Path
from typing import Any, Literal

from bson import ObjectId

from alab_management.task_view.task import get_task_by_name

from .samplebuilder import SampleBuilder


def get_experiment_status(
    exp_id: ObjectId | str, address: str = "http://localhost:8895", **kwargs
):
    """
    Get the status of the experiment.

    Args:
        exp_id (ObjectId): The object id of the experiment.
        address (str): The address of the server. It is defaulted to `http://localhost:8895`,
            which is the default address of the alabos server.
        **kwargs: Additional keyword arguments to be passed to the `requests.get` function.

    Returns
    -------
        The status of the experiment.

    .. seealso::
        See the dashboard code for the response format. :func:`alab_management.dashboard.routes.experiment.query_experiment`
    """
    import requests

    # convert exp_id to string while validating the ObjectId format
    exp_id = str(ObjectId(exp_id))

    url = f"{address}/api/experiment/{exp_id}"
    response = requests.get(url, **kwargs)
    response.raise_for_status()
    return response.json()


def get_experiment_result(
    exp_id: ObjectId | str, address: str = "http://localhost:8895", **kwargs
):
    """
    Get the result of the experiment.

    Args:
        exp_id: The object id of the experiment.
        address: The address of the server. It is defaulted to `http://localhost:8895`,
            which is the default address of the alabos server.
        **kwargs: Additional keyword arguments to be passed to the `requests.get` function.

    Returns
    -------
        See the dashboard code for the response format.
        :func:`alab_management.dashboard.routes.experiment.query_experiment_results`
    """
    import requests

    # convert exp_id to string while validating the ObjectId format
    exp_id = str(ObjectId(exp_id))

    url = f"{address}/api/experiment/results/{exp_id}"
    response = requests.get(url, **kwargs)
    response.raise_for_status()
    return response.json()


class ExperimentBuilder:
    """
    It takes a list of samples and a list of tasks, and returns a dictionary
    that can be used to generate an input file for the `experiment` to run.

    Args:
      name (str): The name of the experiment.
    """

    def __init__(self, name: str, tags: list[str] | None = None, **metadata):
        """
        Args:
          name (str): The name of the experiment.
          tags (List[str]): A list of tags to attach to the experiment.
        """
        self.name = name
        self._samples: list[SampleBuilder] = []
        self._tasks: dict[str, dict[str, Any]] = {}
        self.tags = tags or []
        self.metadata = metadata

    def add_sample(
        self, name: str, tags: list[str] | None = None, **metadata
    ) -> SampleBuilder:
        """
        Add a sample to the batch. Each sample already has multiple tasks binded to it. Each
        batch is a directed graph of tasks.

        Args:
          name (str): The name of the sample. This must be unique within this ExperimentBuilder.
          tags (List[str]): A list of tags to attach to the sample.
          **metadata: Any additional keyword arguments will be attached to this sample as metadata.

        Returns
        -------
          A SampleBuilder object. This can be used to add tasks to the sample.
        """
        if any(name == sample.name for sample in self._samples):
            raise ValueError(f"Sample by name {name} already exists.")
        sample = SampleBuilder(name, experiment=self, tags=tags, **metadata)

        # TODO ensure that the metadata is json/bson serializable
        self._samples.append(sample)
        return sample

    def add_task(
        self,
        task_id: str,
        task_name: str,
        task_kwargs: dict[str, Any],
        samples: list[SampleBuilder],
    ) -> None:
        """
        This function adds a task to the sample. You should use this function only for special cases which
        are not handled by the `add_sample` function.

        Args:
            task_id (str): The object id of the task in mongodb
            task_name (str): The name of the task.
            task_kwargs (Dict[str, Any]): Any additional keyword arguments will be attached to this sample as metadata.
            samples (List[SampleBuilder]): A list of samples to which this task is binded to.

        Returns
        -------
            None
        """
        if task_id in self._tasks:
            return

        task_obj = get_task_by_name(task_name).from_kwargs(
            samples=[sample.name for sample in samples],
            task_id=ObjectId(task_id),
            **task_kwargs,
        )
        if not task_obj.validate():
            raise ValueError(
                "Task input validation failed!"
                + (
                    f"\nError message: {task_obj.get_message()}"
                    if task_obj.get_message()
                    else ""
                )
            )

        self._tasks[task_id] = {
            "type": task_name,
            "parameters": task_kwargs,
            "samples": [sample.name for sample in samples],
        }

    def to_dict(self) -> dict[str, Any]:
        """
        Return a dictionary that can be used to generate an input file for the `experiment`
        to run.

        Returns
        -------
            A dictionary that can be used to generate an input file for the `experiment` to run.

        """
        samples: list[dict[str, Any]] = []
        # tasks = []
        tasks: list[dict[str, str | set[int] | list]] = []
        task_ids = {}

        for sample in self._samples:
            samples.append(sample.to_dict())
            last_task_id = None
            for task_id in sample.tasks:
                task = self._tasks[task_id]
                task["_id"] = str(task_id)
                if task_id not in task_ids:
                    task_ids[task_id] = len(tasks)
                    # task["next_tasks"] = set()
                    task["prev_tasks"] = set()
                    tasks.append(task)
                if last_task_id is not None:
                    # tasks[task_ids[last_task_id]]["next_tasks"].add(task_ids[task_id])
                    task["prev_tasks"].add(task_ids[last_task_id])
                last_task_id = task_id

        for task in tasks:
            # task["next_tasks"] = list(task["next_tasks"])
            task["prev_tasks"] = list(task["prev_tasks"])

        return {
            "name": self.name,
            "tags": self.tags,
            "metadata": self.metadata,
            "samples": samples,
            "tasks": tasks,
        }

    def generate_input_file(
        self, filename: str, fmt: Literal["json", "yaml"] = "json"
    ) -> None:
        """
        Genreate an input file for the `experiment` command.

        Args:
            filename (str): The name of the file to be generated.
            fmt (Literal["json", "yaml"]): The format of the file to be generated.

        Returns
        -------
            None.
        """
        with Path(filename).open("w", encoding="utf-8") as f:
            if fmt == "json":
                import json

                json.dump(self.to_dict(), f, indent=2)
            elif fmt == "yaml":
                import yaml

                yaml.dump(self.to_dict(), f, default_flow_style=False, indent=2)

    def plot(self, ax=None) -> None:
        """
        Plot the directed graph of tasks.

        Args:
            ax (matplotlib.axes.Axes): The axes on which to plot the graph.

        Returns
        -------
            None.
        """
        import matplotlib.pyplot as plt  # type: ignore
        import networkx as nx  # type: ignore

        if ax is None:
            _, ax = plt.subplots(figsize=(8, 6))

        task_list = self.to_dict()["tasks"]

        unique_tasks = {task["type"] for task in task_list}
        color_key = {
            nodetype: plt.cm.tab10(i) for i, nodetype in enumerate(unique_tasks)
        }
        node_colors = []
        node_labels = {}
        for task in task_list:
            node_colors.append(color_key[task["type"]])
            node_labels[task["_id"]] = f"{task['type']} ({len(task['samples'])})"

        g = nx.DiGraph()
        for task in task_list:
            g.add_node(task["_id"], name=task["type"], samples=len(task["samples"]))
            for prev in task["prev_tasks"]:
                g.add_edge(task_list[prev]["_id"], task["_id"])

        try:
            pos = nx.nx_agraph.graphviz_layout(g, prog="dot")
        except:  # noqa: E722
            pos = nx.spring_layout(g)

        nx.draw(
            g,
            with_labels=True,
            node_color=node_colors,
            labels=node_labels,
            pos=pos,
            ax=ax,
        )

    def submit(self, address: str = "http://localhost:8895", **kwargs) -> ObjectId:
        """
        Submit the experiment to server.

        Args:
            address (str): The address of the server. It is defaulted to `http://localhost:8895`,
                which is the default address of the alabos server.
            **kwargs: Additional keyword arguments to be passed to the `requests.post` function.

        Returns
        -------
            The object id of the experiment.
        """
        import requests

        url = f"{address}/api/experiment/submit"

        data = self.to_dict()
        response = requests.post(url, json=data, **kwargs)

        if response.status_code != 200:
            raise ValueError(f"Error submitting experiment: {response.text}")

        return ObjectId(response.json()["data"]["exp_id"])

    def __repr__(self):
        """Return a string representation of the ExperimentBuilder."""
        return f"<ExperimentBuilder: {self.name}>"
