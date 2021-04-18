#!/usr/bin/env python3

import po4
import networkx as nx
from schema_helpers import *

@parametrize_from_file(
        schema=Schema({
            'nodes': empty_ok({eval: eval}),
            'edges': empty_ok([And(eval, tuple)]),
            **error_or(**{
                'expected': empty_ok([And(eval, tuple)]),
            }),
        }),
)
def test_grouped_topological_sort(nodes, edges, expected, error):
    g = nx.DiGraph()
    g.add_edges_from(edges)

    for node, group in nodes.items():
        g.add_node(node, group=group)

    with error:
        actual = freezerbox.grouped_topological_sort(g)
        assert actual == expected
