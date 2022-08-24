#!/usr/bin/env python3

import freezerbox
import networkx as nx
from param_helpers import *
from mock_model import *

@parametrize_from_file(
        schema=[
            cast(
                nodes=[empty(dict), with_py.eval(keys=True)],
                edges=[empty(list), map_list(with_py.eval, tuple)],
                expected=[empty(list), map_list(with_py.eval, tuple)],
            ),
            with_nx.error_or('expected'),
        ],
)
def test_grouped_topological_sort(nodes, edges, expected, error):
    g = nx.DiGraph()
    g.add_edges_from(edges)

    for node, group in nodes.items():
        g.add_node(node, group=group)

    with error:
        actual = freezerbox.grouped_topological_sort(g)
        assert actual == expected

@parametrize_from_file
def test_group_by_synthesis(db, expected, mock_plugins):
    db = eval_db(db)

    actual = [
            (k, [str(v.tag) for v in vs])
            for k, vs in freezerbox.group_by_synthesis(db.values())
    ]
    expected = [
            (x['arg0'], x['tags'].split())
            for x in expected
    ]

    assert actual == expected

@parametrize_from_file
def test_group_by_cleanup(db, expected, mock_plugins):
    db = eval_db(db)

    actual = [
            (k, [v.maker_args['id'] for v in vs])
            for k, vs in freezerbox.group_by_cleanup(db.values())
    ]
    expected = [
            (x['arg0'], list(map(int, x['ids'].split())))
            for x in expected
    ]

    assert actual == expected
    





