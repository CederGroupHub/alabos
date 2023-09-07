from pathlib import Path
from typing import List, Dict, Any, Literal, Optional
from .samplebuilder import SampleBuilder
import matplotlib.pyplot as plt


from typing import Optional, List
from labgraph import Action, Measurement, Analysis, Material, Sample as LabgraphSample
from labgraph.utils.plot import plot_graph
from bson import ObjectId
import networkx as nx
import itertools as itt
from labgraph.data.nodes import BaseNode
from .batching import batch_graphs


class ExperimentBuilder:
    def __init__(
        self,
        name: str,
        description: str,
        tags: Optional[List[str]] = None,
        autobatching: bool = False,
        **contents,
    ):
        self.name = name
        self.tags = tags or []
        if not isinstance(self.tags, list):
            raise ValueError("tags must be a list of strings")
        if not all(isinstance(tag, str) for tag in self.tags):
            raise ValueError("tags must be a list of strings")

        self.contents = contents
        self.description = description
        self._samples = []
        self._id = ObjectId()

        self.autobatching = autobatching
        self.__graph_memo = {
            "graph": None,
            "tasks_during_last_build": [],
        }

    def add_sample(self, sample: SampleBuilder):
        self._samples.append(sample)

    def plot(self, ax=None):
        plot_graph(self.graph, ax=ax)

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

    @property
    def graph(self) -> nx.DiGraph:
        """Represent this batch + samples as a directed graph.

        Returns:
            nx.DiGraph: Graph representation of this batch and its samples
        """

        def is_prebatched(graphs) -> bool:
            """Check if any tasks are already batched to some extent. We do not support autobatching if tasks are already partially batched.

            Args:
                graphs (List[nx.DiGraph]): Labgraphs of each sample

            Returns:
                bool: True if some samples contain the same Task nodes already
            """
            task_nodes_per_graph = [
                set(
                    node_id
                    for node_id, contents in graph.nodes(data=True)
                    if contents["type"] != "Material"
                )
                for graph in graphs
            ]
            for taskset1, taskset2 in itt.combinations(task_nodes_per_graph, 2):
                if taskset1.intersection(taskset2):
                    return True
            return False

        def build_sample_graph_with_params(sample) -> nx.DiGraph:
            graph = sample.graph
            for node in sample.nodes:
                node: BaseNode
                graph.nodes[node.id]["samples"] = [sample.id]
                if "parameters" in node:
                    graph.nodes[node.id]["contents"]["parameters"] = node["parameters"]
                    graph.nodes[node.id]["BaseTask"] = node

            return graph

        graphs = [build_sample_graph_with_params(sample) for sample in self._samples]

        if self.autobatching:
            if is_prebatched(graphs):
                raise ValueError(
                    "Cannot autobatch if some samples are already prebatched (ie they share the same Task nodes as defined by the user)."
                )
            graphs = self.__build_graph(graphs)

        if len(graphs) == 0:
            return nx.DiGraph()
        total_graph = graphs[0]
        for g in graphs[1:]:
            total_graph = nx.compose(total_graph, g)
        return total_graph

    @property
    def samples(self) -> List[LabgraphSample]:
        if not self.autobatching:
            return self._samples
        nodes = []
        key = {
            "Action": Action,
            "Analysis": Analysis,
            "Material": Material,
            "Measurement": Measurement,
        }
        for node_id in self.graph.nodes:
            entry = self.graph.nodes[node_id]
            entry.pop("BaseTask", None)
            NodeClass = key[entry["type"]]
            nodes.append(NodeClass.from_dict(entry))

        batched_samples = [
            LabgraphSample(
                name=s.name,
                description=s.description,
                nodes=[n for n in nodes if s.id in n["samples"]],
                tags=s.tags,
                **s._contents,
            )
            for s in self._samples
        ]
        return batched_samples

    def __build_graph(self, graphs: List[nx.DiGraph]) -> nx.DiGraph:
        """A memoization wrapper around batch_graphs(). This function is called by the self.graph property, and will only recompute the graph if the tasks have changed."""
        hash_str = ""
        for graph in graphs:
            for node_id, data in graph.nodes(data=True):
                if data["type"] != "Material":
                    hash_str += str(node_id)

        task_hash = hash(hash_str)
        if (self.__graph_memo["graph"] is None) or (
            task_hash != self.__graph_memo["task_hash"]
        ):
            # first build or tasks changed
            self.__graph_memo["graph"] = batch_graphs(graphs)
            self.__graph_memo["task_hash"] = task_hash

        return self.__graph_memo["graph"]

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
                task_entry["labgraph_node_type"] = node.labgraph_node_type

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
