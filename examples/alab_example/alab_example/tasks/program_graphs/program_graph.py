"""This module provides functions for working with program graphs."""

from __future__ import annotations

import json
import os

import networkx as nx


def add_robot_name(graph: nx.DiGraph, robot_name: str) -> nx.DiGraph:
    """Adds a robot name to the graph. This is used to differentiate between the two robots in the graph."""
    for src, dest in graph.edges:
        graph[src][dest]["robot"] = robot_name
    return graph


def reduce_position_name(name: str, separator: str = "/") -> str:
    """Drops the index from a position name.

    Example:
        >>> reduce_position_name("sample_position/1") = "sample_position"
        >>> reduce_position_name("device/slot/1") = "device/slot"
        >>> reduce_position_name("device/slot") = "device/slot"

    Args:
        name (str): sample position
        separator (str, optional): delimiter between segments of the sample position name. Defaults to "/".

    Returns:
        (str): reduced sample position name
    """
    pieces = name.split(separator)
    if pieces[-1].isdigit():
        pieces = pieces[:-1]
    return separator.join(pieces)


def reduce_graph(graph: nx.DiGraph) -> nx.DiGraph:
    """Reduces a graph by removing the index from sample position names.
    This turns a graph of position->position into a graph of [Device/SamplePosition]->[Device/SamplePosition].
    """
    graph_dicts = nx.to_dict_of_dicts(graph)
    reduced_graph_dicts = {}
    for source in graph_dicts:
        reduced_source = reduce_position_name(source)
        if reduced_source in reduced_graph_dicts:
            continue  # no need to retrace the same device/sampleposition
        reduced_graph_dicts[reduced_source] = {}
        for dest in graph_dicts[source]:
            reduced_dest = reduce_position_name(dest)
            if reduced_dest in reduced_graph_dicts[reduced_source]:
                continue  # same idea as above
            reduced_graph_dicts[reduced_source][reduced_dest] = graph_dicts[source][
                dest
            ]
    return nx.DiGraph(reduced_graph_dicts)


path = os.path.split(os.path.abspath(__file__))[0]

with open(os.path.join(path, "char_program_graph.json")) as f:
    char_graph = nx.DiGraph(json.load(f))

with open(os.path.join(path, "furnace_program_graph.json")) as f:
    furnace_graph = nx.DiGraph(json.load(f))

char_graph = add_robot_name(char_graph, "arm_characterization")
furnace_graph = add_robot_name(furnace_graph, "arm_furnaces")
total_graph = nx.compose(char_graph, furnace_graph)

edges_missing_programs = []
for node0, node1, data in total_graph.edges(data=True):
    if "programs" not in data:
        edges_missing_programs.append((node0, node1))
if len(edges_missing_programs) > 0:
    raise ValueError(
        "Some edges are missing the 'programs' attribute! Affected edges: "
        + str(edges_missing_programs)
    )

reduced_char_graph = reduce_graph(char_graph)
reduced_furnace_graph = reduce_graph(furnace_graph)
total_reduced_graph = nx.compose(reduced_char_graph, reduced_furnace_graph)


def get_parent_path(source: str, destination: str) -> tuple[list[str], list[str]]:
    """Gets the parent path from source to destination. The parent path is the path through Devices/SamplePositions in
    the lab -- not through specific, indexed sample positions! This path is used to determine which resources
    (parents and robot arms) must be reserved to move a sample from source to destination.

    Args:
        source (str): source position
        destination (str): destination position

    Returns:
        Tuple[List[str], List[str]]: 1) path from source to destination. This is a list of parents
        (devices/sample positions) that the sample must pass through to get to the destination.
        2) robot arms that are involved/required to transfer a sample across the path
    """
    source = reduce_position_name(source)
    destination = reduce_position_name(destination)
    if source == destination:
        return [], []
    try:
        path = nx.shortest_path(total_reduced_graph, source=source, target=destination)
    except nx.NetworkXNoPath:
        raise ValueError(
            f"No path from {source} to {destination} in the robot planning graph!"
        )
    except nx.NodeNotFound:
        raise ValueError(
            f"One of the nodes ({source} or {destination}) were not found in the robot planning graph!"
        )

    robots_needed = set()
    for node0, node1 in zip(path, path[1:]):
        robots_needed.add(total_reduced_graph[node0][node1]["robot"])

    return path, robots_needed


def get_programs(source: str, destination: str) -> list[dict[str, list[str] | str]]:
    """Gets the programs that must be run to move a sample from source to destination.

    Args:
        source (str): source position
        destination (str): destination position

    Returns:
        Dict[str, Union[List[str], str]]: with format:
        [
            {
                "programs": ["program1.urp", "program2.urp"],
                "robot": "arm_characterization"
            },
            {
                "programs": ["program3.urp", "program4.urp"],
                "robot": "arm_furnaces"
            }...
        ]
    """
    steps = []
    path = nx.shortest_path(total_graph, source=source, target=destination)
    for node0, node1 in zip(path, path[1:]):
        steps.append(
            {
                "programs": total_graph[node0][node1]["programs"],
                "robot": total_graph[node0][node1]["robot"],
            }
        )

    return steps
