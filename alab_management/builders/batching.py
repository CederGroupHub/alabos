import networkx as nx
from typing import List, Callable
import numpy as np
from alab_management.task_view.task import BaseTask
from bson import ObjectId


def merge_nodes(
    graph: nx.DiGraph,
    destination_node: str,
    nodes_to_merge: List[str],
) -> nx.DiGraph:
    """
    The merge_nodes function takes a graph, a destination node, and a list of nodes to merge.
    It then merges the samples from all the nodes in the list into one node (the destination).
    The function returns an updated graph with merged nodes.

    Args:
        graph: nx.DiGraph: Pass the graph we want to modify
        destination_node: str: Specify the node that will be kept
        nodes_to_merge: List[str]: Specify which nodes are to be merged

    Returns:
        A graph with the merged nodes

    """

    if len(nodes_to_merge) == 0:
        return graph

    if any([n not in graph.nodes for n in nodes_to_merge + [destination_node]]):
        raise ValueError(
            "One or more nodes to merge not in graph. Make sure you are passing node ids!"
        )

    final = graph.nodes[destination_node]
    final_contents = final["contents"]
    samples = final["samples"]
    BaseTask1 = graph.nodes[destination_node]["BaseTask"]

    for remove_id in nodes_to_merge:
        BaseTask2 = graph.nodes[remove_id]["BaseTask"]
        final_contents["parameters"] = BaseTask1.batch_merge_parameters(BaseTask2)
        final["samples"].extend(graph.nodes[remove_id]["samples"])
        for prev in graph.predecessors(remove_id):
            graph.add_edge(prev, destination_node)
        for next in graph.successors(remove_id):
            graph.add_edge(destination_node, next)
        graph.remove_node(remove_id)

    graph.nodes[destination_node]["contents"] = final_contents
    graph.nodes[destination_node]["samples"] = list(set(samples))


def iteratively_merge_nodes(
    graph: nx.DiGraph,
    node_type: str,
    parent_graph: nx.DiGraph = None,
) -> nx.DiGraph:
    """Iteratively merge nodes of a given type in a graph.

    Args:
        graph (nx.DiGraph): experimental graph (or subgraph) to merge nodes in

        node_type (str): type (ie Task type) of nodes to merge

        parent_graph (nx.DiGraph, optional): Parent graph to merge. This is required if merging subgraphs, as subgraphs cannot be edited (simply point to nodes within a parent graph). Edits based on subgraphs will be made to the parent graph. Defaults to None, which implies graph == parent_graph.

        merge_allowed_fn (Callable, optional): Function evaluated to decide whether two nodes can be merged. Should return a boolean. For example, merging nodes for heating in a furnace should check if the furnace profiles required of the two nodes are identical. Defaults to None, implies that any nodes with node_type can be merged if capacity allows.

        similarity_fn (Callable, optional): Function evaluated to decide how similar two nodes are (Higher value = more similar). We will sort nodes by similarity to prioritize merges between similar nodes. Defaults to None, implies that nodes are equally similar.

    Returns:
        nx.DiGraph: graph with nodes merged. Note that changes to parent_graph are made in place.
    """
    if parent_graph is None:
        parent_graph = graph

    # if len(nx.connected_components(graph) == 1):
    #     return graph

    node_ids = [
        node_id
        for node_id, node_contents in graph.nodes(data=True)
        if node_contents["name"] == node_type
    ]
    # if len(node_ids) < 1:
    #     return graph #nothing to merge here

    similarity_matrix = np.zeros((len(node_ids), len(node_ids)))
    for i, node_id in enumerate(node_ids):
        BaseTask1: BaseTask = parent_graph.nodes[node_id]["BaseTask"]
        for j, node_id2 in enumerate(node_ids[:i]):
            BaseTask2: BaseTask = parent_graph.nodes[node_id2]["BaseTask"]
            similarity_matrix[i, j] = BaseTask1.batch_merge_priority(BaseTask2)
            similarity_matrix[j, i] = similarity_matrix[i, j]
    sort_idx = np.argsort(np.sum(similarity_matrix, axis=0))[
        ::-1
    ]  # sort so that nodes with the most similar neighbors (largest similarity value) are checked first
    node_ids = [node_ids[i] for i in sort_idx]
    similarity_matrix = similarity_matrix[sort_idx, :][:, sort_idx]

    for reference_node_id in node_ids:
        # the reference node is the one we are trying to merge other nodes into
        if reference_node_id not in graph.nodes:
            continue  # we must have merged the reference node earlier, so this node no longer exists. No problem, skip it!

        ref = graph.nodes[reference_node_id]
        BaseTask1 = ref["BaseTask"]
        samples = set(ref["samples"])
        nodes_to_merge = []

        sort_idx = np.argsort(similarity_matrix[node_ids.index(reference_node_id)])[
            ::-1
        ]
        nodes_to_check = [node_ids[i] for i in sort_idx]
        nodes_to_check = [
            node_id
            for node_id in nodes_to_check
            if node_id != reference_node_id and node_id in graph.nodes
        ]

        for node_id in nodes_to_check:
            node = graph.nodes[node_id]
            BaseTask2: BaseTask = node["BaseTask"]

            if len(node["samples"]) + len(samples) > ref["contents"]["batch_capacity"]:
                # not enough space to merge
                continue
            if not BaseTask1.batch_merge_allowed(BaseTask2):
                continue

            samples.update(node["samples"])
            nodes_to_merge.append(node_id)

            if len(samples) == ref["contents"]["batch_capacity"]:
                # no more room to merge
                break

        if len(nodes_to_merge) == 0:
            continue
        merge_nodes(
            graph=parent_graph,
            destination_node=reference_node_id,
            nodes_to_merge=nodes_to_merge,
        )


def get_subgraphs(graph: nx.DiGraph) -> List[nx.DiGraph]:
    """Return subgraphs of a DiGraph. A subgraph is a set of connected nodes that are not connected to any other nodes in the graph.

    Args:
        graph (nx.DiGraph): directed graph of an experiment

    Returns:
        List[nx.Digraph]: list of subgraphs of the directed graph.
    """

    subgraphs = [
        graph.subgraph(c) for c in nx.connected_components(nx.to_undirected(graph))
    ]
    return subgraphs


def fix_labgraph_edges(graph: nx.DiGraph) -> nx.DiGraph:
    def get_node_type(node_id: ObjectId) -> str:
        return graph.nodes[node_id]["type"]

    for node in graph.nodes:
        graph.nodes[node]["upstream"] = [
            {"node_id": upstream_node_id, "node_type": get_node_type(upstream_node_id)}
            for upstream_node_id in graph.predecessors(node)
        ]
        graph.nodes[node]["downstream"] = [
            {
                "node_id": downstream_node_id,
                "node_type": get_node_type(downstream_node_id),
            }
            for downstream_node_id in graph.successors(node)
        ]


def batch_graphs(graphs: List[nx.DiGraph]) -> List[nx.DiGraph]:
    # First, compose our graphs into one big graph with disconnected components.
    if len(graphs) == 0:
        return []
    total_graph = graphs[0]
    for g in graphs[1:]:
        total_graph = nx.compose(total_graph, g)

    # Next, we need to determine the order in which to batch tasks. Priority goes to BaseTasks with the _lowest BATCH_SEQUENCE_. For matching BATCH_SEQUENCE, priority goes to the _lowest BATCH_CAPACITY_.
    task_dict = {
        node["name"]: node["BaseTask"]
        for node_id, node in total_graph.nodes(data=True)
        if node["type"] != "Material" and node["BaseTask"].BATCH_CAPACITY > 1
    }

    task_names = list(task_dict.items())
    task_names.sort(key=lambda x: x[1].BATCH_CAPACITY)
    task_names.sort(key=lambda x: x[1].BATCH_SEQUENCE)

    # Now we will try to condense graph nodes into shared tasks
    for task_name, _ in task_names:
        for subgraph in get_subgraphs(total_graph):
            # try to batch within existing connected tasks already.
            iteratively_merge_nodes(subgraph, task_name, parent_graph=total_graph)
        iteratively_merge_nodes(total_graph, task_name)

    fix_labgraph_edges(total_graph)
    return get_subgraphs(total_graph)
