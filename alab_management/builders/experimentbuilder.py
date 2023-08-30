from pathlib import Path
from typing import List, Dict, Any, Literal, Optional
from .samplebuilder import SampleBuilder
import matplotlib.pyplot as plt


from typing import Optional, List
from labgraph import Material
from labgraph.utils.plot import plot_multiple_samples
from bson import ObjectId


class ExperimentBuilder:
    def __init__(self, name: str, tags: Optional[List[str]] = None, **contents):
        self.name = name
        self.tags = tags or []
        self.contents = contents
        self.samples = []
        self._id = ObjectId()

    def add_sample(self, sample: SampleBuilder):
        self.samples.append(sample)

    def plot(self, ax=None):
        return plot_multiple_samples(self.samples, ax=ax)

    def to_dict(self) -> dict:
        samples = []
        tasks = []
        task_ids = {}

        for sample in self.samples:
            # put into original ALabOS format
            sdict = sample.to_dict()
            sdict.pop("nodes")
            sdict["metadata"] = sdict.pop("contents", {})
            sdict["metadata"]["description"] = sdict.pop("description", "")
            sdict["sample_id"] = str(sdict.pop("_id"))
            samples.append(sdict)

            last_task_id = None
            for node in sample.nodes:
                if isinstance(node, Material):
                    continue  # only add task nodes (Action, Measurement, Analysis)

                # put into original ALabOS format
                task_entry = node.to_dict()
                task_entry["task_id"] = str(task_entry.pop("_id"))
                task_entry["type"] = task_entry.pop("name")
                task_entry["parameters"] = task_entry["contents"].get("parameters", {})
                task_entry = {
                    k: task_entry[k] for k in ["task_id", "type", "parameters"]
                }
                task_entry["samples"] = []
                task_entry["labgraph_node_type"] = node.labgraph_type

                task_entry["prev_tasks"] = set()
                if node.id not in task_ids:
                    task_ids[node.id] = len(tasks)

                    for upstream in node.upstream:
                        if upstream["node_type"] == "Material":
                            continue
                        task_entry["prev_tasks"].add(task_ids[upstream["node_id"]])

                    tasks.append(task_entry)

                tasks[task_ids[node.id]]["samples"].append(sample.name)
                if last_task_id is not None:
                    # tasks[task_ids[last_task_id]]["next_tasks"].add(task_ids[task_id])
                    task_entry["prev_tasks"].add(task_ids[last_task_id])
                last_task_id = node.id

        for task in tasks:
            task["prev_tasks"] = list(task["prev_tasks"])

        return {
            "name": self.name,
            "tags": self.tags,
            "metadata": self.contents,
            "samples": samples,
            "tasks": tasks,
            "_id": str(self._id),
        }


# class ExperimentBuilder:
#     """
#     It takes a list of samples and a list of tasks, and returns a dictionary
#     that can be used to generate an input file for the `experiment` command

#     Args:
#       name (str): The name of the experiment.
#     """

#     def __init__(self, name: str, tags: Optional[List[str]] = None, **metadata):
#         """
#         Args:
#           name (str): The name of the experiment.
#         """
#         self.name = name
#         self._samples: List[SampleBuilder] = []
#         self._tasks: Dict[str, Dict[str, Any]] = {}
#         self.tags = tags or []
#         self.metadata = metadata

#     def add_sample(
#         self, name: str, tags: Optional[List[str]] = None, **metadata
#     ) -> SampleBuilder:
#         """
#         This function adds a sample to the experiment

#         Args:
#           name (str): The name of the sample. This must be unique within this ExperimentBuilder.
#           **metadata: Any additional keyword arguments will be attached to this sample as metadata.
#         Returns:
#           A SampleBuilder object. This can be used to add tasks to the sample.
#         """
#         if any(name == sample.name for sample in self._samples):
#             raise ValueError(f"Sample by name {name} already exists.")
#         sample = SampleBuilder(name, experiment=self, tags=tags, **metadata)

#         # TODO ensure that the metadata is json/bson serializable
#         self._samples.append(sample)
#         return sample

#     def add_task(
#         self,
#         task_id: str,
#         task_name: str,
#         task_kwargs: Dict[str, Any],
#         samples: List[SampleBuilder],
#     ) -> None:
#         if task_id in self._tasks:
#             return
#         self._tasks[task_id] = {
#             "type": task_name,
#             "parameters": task_kwargs,
#             "samples": [sample.name for sample in samples],
#         }

#     def to_dict(self):
#         samples = []
#         tasks = []
#         task_ids = {}

#         for sample in self._samples:
#             samples.append(sample.to_dict())
#             last_task_id = None
#             for task_id in sample.tasks:
#                 task = self._tasks[task_id]
#                 task["_id"] = str(task_id)
#                 if task_id not in task_ids:
#                     task_ids[task_id] = len(tasks)
#                     # task["next_tasks"] = set()
#                     task["prev_tasks"] = set()
#                     tasks.append(task)
#                 if last_task_id is not None:
#                     # tasks[task_ids[last_task_id]]["next_tasks"].add(task_ids[task_id])
#                     task["prev_tasks"].add(task_ids[last_task_id])
#                 last_task_id = task_id

#         for task in tasks:
#             # task["next_tasks"] = list(task["next_tasks"])
#             task["prev_tasks"] = list(task["prev_tasks"])

#         return {
#             "name": self.name,
#             "tags": self.tags,
#             "metadata": self.metadata,
#             "samples": samples,
#             "tasks": tasks,
#         }

#     def generate_input_file(
#         self, filename: str, fmt: Literal["json", "yaml"] = "json"
#     ) -> None:
#         with Path(filename).open("w", encoding="utf-8") as f:
#             if fmt == "json":
#                 import json

#                 json.dump(self.to_dict(), f, indent=2)
#             elif fmt == "yaml":
#                 import yaml

#                 yaml.dump(self.to_dict(), f, default_flow_style=False, indent=2)

#     def plot(self, ax=None):
#         import networkx as nx
#         import matplotlib.pyplot as plt

#         if ax is None:
#             _, ax = plt.subplots(figsize=(8, 6))

#         task_list = self.to_dict()["tasks"]

#         unique_tasks = set([task["type"] for task in task_list])
#         color_key = {
#             nodetype: plt.cm.tab10(i) for i, nodetype in enumerate(unique_tasks)
#         }
#         node_colors = []
#         node_labels = {}
#         for task in task_list:
#             node_colors.append(color_key[task["type"]])
#             node_labels[task["_id"]] = f"{task['type']} ({len(task['samples'])})"

#         g = nx.DiGraph()
#         for task in task_list:
#             g.add_node(task["_id"], name=task["type"], samples=len(task["samples"]))
#             for prev in task["prev_tasks"]:
#                 g.add_edge(task_list[prev]["_id"], task["_id"])

#         try:
#             pos = nx.nx_agraph.graphviz_layout(g, prog="dot")
#         except:
#             pos = nx.spring_layout(g)

#         nx.draw(
#             g,
#             with_labels=True,
#             node_color=node_colors,
#             labels=node_labels,
#             pos=pos,
#             ax=ax,
#         )

#     def __repr__(self):
#         return f"<ExperimentBuilder: {self.name}>"
