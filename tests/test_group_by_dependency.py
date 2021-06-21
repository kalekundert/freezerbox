#!/usr/bin/env python3

import freezerbox
import networkx as nx
from schema_helpers import *
from mock_model import *

@parametrize_from_file(
        schema=Schema({
            'nodes': empty_ok({eval: eval}),
            'edges': empty_ok([And(eval, tuple)]),
            **error_or({
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

@parametrize_from_file(
        schema=Schema({
            'db': eval_db,
            'expected': empty_ok([{'arg0': str, 'tags': str}]),
        }),
)
def test_group_by_synthesis(db, expected, mock_plugins):
    actual = [
            (k, [str(v.tag) for v in vs])
            for k, vs in freezerbox.group_by_synthesis(db.values())
    ]
    expected = [
            (x['arg0'], x['tags'].split())
            for x in expected
    ]

    assert actual == expected

@parametrize_from_file(
        schema=Schema({
            'db': eval_db,
            'expected': empty_ok([{'arg0': str, 'ids': str}]),
        }),
)
def test_group_by_cleanup(db, expected, mock_plugins):
    actual = [
            (k, [v.maker_args['id'] for v in vs])
            for k, vs in freezerbox.group_by_cleanup(db.values())
    ]
    expected = [
            (x['arg0'], list(map(int, x['ids'].split())))
            for x in expected
    ]

    assert actual == expected
    





