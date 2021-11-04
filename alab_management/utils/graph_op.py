from typing import List, Any, Dict


class Graph:
    """
    Use adjacent table to store a graph
    """
    def __init__(self, vertices: List[Any], edges: Dict[int, List[int]]):
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
                elif rec_stack[child]:
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
        index = self.vertices.index(v)
        return [self.vertices[i] for i, children in self.edges for child in children if child == index]

    def get_children(self, v: Any) -> List[Any]:
        index = self.vertices.index(v)
        return [self.vertices[i] for i in self.edges[index]]
