from pathlib import Path
from typing import List, Dict, Any, Literal, Optional
from .samplebuilder import SampleBuilder
import matplotlib.pyplot as plt


from typing import Optional, List
from labgraph import Material, Sample as LabgraphSample
from labgraph.utils.plot import plot_multiple_samples
from bson import ObjectId


class ExperimentBuilder:
    def __init__(
        self, name: str, description: str, tags: Optional[List[str]] = None, **contents
    ):
        self.name = name
        self.tags = tags or []
        if not isinstance(self.tags, list):
            raise ValueError("tags must be a list of strings")
        if not all(isinstance(tag, str) for tag in self.tags):
            raise ValueError("tags must be a list of strings")

        self.contents = contents
        self.description = description
        self.samples = []
        self._id = ObjectId()

    def add_sample(self, sample: SampleBuilder):
        self.samples.append(sample)

    def plot(self, ax=None):
        return plot_multiple_samples(self.samples, ax=ax)

    @property
    def umbrella_sample(self):
        umbrella_sample = LabgraphSample(
            name=self.name,
            description=self.description,
            nodes=[node for sample in self.samples for node in sample.nodes],
            tags=self.tags,
            **self.contents,
        )
        umbrella_sample._id = self._id

        return umbrella_sample

    def to_dict(self) -> dict:
        samples = []
        tasks = []
        task_ids = {}

        for sample in self.samples:
            # put into original ALabOS format
            samples.append(sample.to_dict())

            last_task_id = None
            for node in sample.nodes:
                if isinstance(node, Material):
                    continue  # only add task nodes (Action, Measurement, Analysis)

                # put into original ALabOS format
                task_entry = node.to_dict()
                task_entry["task_id"] = str(task_entry.pop("_id"))
                task_entry["name"] = task_entry.pop("name")
                task_entry["parameters"] = task_entry["contents"].get("parameters", {})
                task_entry = {
                    k: task_entry[k] for k in ["task_id", "name", "parameters"]
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

        d = self.umbrella_sample.to_dict(verbose=True)
        d.update({"tasks": tasks, "samples": samples})
        return d
        # return {
        #     "_id": str(self._id),
        #     "name": self.name,
        #     "description": self.description,
        #     "tags": self.tags,
        #     "contents": self.contents,
        #     "tasks": tasks,
        #     "samples": samples,
        #     "nodes": self.umbrella_sample.to_dict(verbose=True)["node_contents"],
        # }
