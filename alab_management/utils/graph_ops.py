"""
This file contains a custom graph class and functions for checking if there are cycles in a graph.
"""

from typing import List, Any, Dict


class Graph:
    """
    Use adjacent table to store a graph
    """

    def __init__(self, vertices: List[Any], edges: Dict[int, List[int]]):
        """
        Note that the all the keys and values are the index of vertices
        """
        if len(vertices) != len(edges):
            raise ValueError(
                "The edges (adjacent table) should be the same length as the vertices."
            )
        if len(vertices) != len(set(vertices)):
            raise ValueError("Duplicated value in vertices.")
        self.vertices = vertices
        self.edges = edges

    def has_cycle(self) -> bool:
        """
        Use DFS algorithm to detect cycle in a graph
        """
        visited = [False] * len(self.vertices)
        rec_stack = [False] * len(self.vertices)

        def _is_cyclic(v):
            visited[v] = True
            rec_stack[v] = True

            # Recur for all neighbours
            # if any neighbour is visited and in
            # recStack then graph is cyclic
            for child in self.edges[v]:
                if not visited[child] and _is_cyclic(child):
                    return True
                if rec_stack[child]:
                    return True

            # The vertex needs to be popped from
            # recursion stack before function ends
            rec_stack[v] = False
            return False

        for vertex in range(len(self.vertices)):
            if not visited[vertex] and _is_cyclic(vertex):
                return True
        return False

    def get_parents(self, v: Any) -> List[Any]:
        """
        Provide the value of vertex, return the value of its parents vertices
        """
        index = self.vertices.index(v)
        return [
            self.vertices[i]
            for i, children in self.edges.items()
            for child in children
            if child == index
        ]

    def get_children(self, v: Any) -> List[Any]:
        """
        Provide the index of vertex, return the value of its children vertices
        """
        index = self.vertices.index(v)
        return [self.vertices[i] for i in self.edges[index]]
