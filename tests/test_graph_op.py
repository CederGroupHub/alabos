import os
from pathlib import Path
from unittest import TestCase

os.environ["ALAB_CONFIG"] = (Path(__file__).parent.parent /
                             "examples" / "fake_lab" / "config.toml").as_posix()

from alab_management.utils.graph_op import Graph


class TestGraph(TestCase):
    def test_has_cycle(self):
        vertices = list(range(5))
        edges = {0: [1, 2], 1: [2, 3], 2: [3, 4], 3: [4, 5]}
        with self.assertRaises(ValueError):
            Graph(vertices, edges)

        vertices = list(range(5))
        edges = {0: [1, 2], 1: [2, 3], 2: [3, 4], 3: [4], 4: []}
        self.assertFalse(Graph(vertices, edges).has_cycle())

        vertices = list(range(5))
        edges = {0: [1, 2], 1: [2, 3], 2: [3, 4], 3: [4, 0], 4: []}
        self.assertTrue(Graph(vertices, edges).has_cycle())

        vertices = list(range(5))
        edges = {0: [0, 1, 2], 1: [2, 3], 2: [3, 4], 3: [4], 4: []}
        self.assertTrue(Graph(vertices, edges).has_cycle())

        vertices = list(range(1))
        edges = {0: []}
        self.assertFalse(Graph(vertices, edges).has_cycle())

    def test_get_parents(self):
        vertices = list(range(5))
        edges = {0: [1, 2], 1: [2, 3], 2: [3, 4], 3: [4], 4: []}
        graph = Graph(vertices, edges)
        self.assertListEqual([1, 2], graph.get_parents(3))
        self.assertListEqual([], graph.get_parents(0))

    def test_get_children(self):
        vertices = list(range(5))
        edges = {0: [1, 2], 1: [2, 3], 2: [3, 4], 3: [4], 4: []}
        graph = Graph(vertices, edges)
        self.assertListEqual([], graph.get_children(3))
        self.assertListEqual([1, 2], graph.get_children(0))
