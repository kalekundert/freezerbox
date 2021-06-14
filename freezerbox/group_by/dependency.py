#!/usr/bin/env python3

import networkx as nx
from math import inf
from copy import deepcopy
from more_itertools import pairwise
from ..utils import parse_tag

def group_by_synthesis(products):
    products = list(products)

    # Sort groups by order of appearance:

    group_from_arg0 = {}
    arg0_from_group = {}
    next_group = 0

    for product in products:
        arg0 = product.synthesis_args.by_index[0]
        if arg0 not in arg0_from_group:
            group_from_arg0[arg0] = next_group
            arg0_from_group[next_group] = arg0
            next_group += 1

    # Construct a dependency graph:

    deps = nx.DiGraph()

    for i, product in enumerate(products):
        arg0 = product.synthesis_args.by_index[0]
        deps.add_node(
                product.tag,
                group=group_from_arg0[arg0],
                order=i,
        )

    for product in products:
        for dep in product.dependencies:
            dep = parse_tag(dep)
            if dep in deps:
                deps.add_edge(dep, product.tag)

    # Split into groups and yield intermediates:

    intermediate_from_tag = {
            x.tag: x.make_intermediate(0)
            for x in products
    }

    for group, tags in grouped_topological_sort(deps):
        arg0 = arg0_from_group[group]
        intermediates = [intermediate_from_tag[tag] for tag in tags]
        yield arg0, intermediates

def group_by_cleanup(products):
    products = list(products)

    # Construct a dependency graph:

    deps = nx.DiGraph()

    for i, product in enumerate(products):
        for j, cleanup in enumerate(product.cleanup_args):
            deps.add_node((i, j), group=cleanup.by_index[0])

        for pair in pairwise(enumerate(product.cleanup_args)):
            (j, args_j), (k, args_k) = pair
            deps.add_edge((i, j), (i, k))

    # Split into groups:

    for key, nodes in grouped_topological_sort(deps):
        intermediates = [
                products[i].make_intermediate(j+1)
                for i, j in nodes
        ]
        yield key, intermediates

def grouped_topological_sort(deps):
    """
    Arguments:
        deps: networkx.DiGraph
            A graph of the dependencies to account for.  Each node should have 
            a "group" attribute identifying which group it is part of.  The 
            returned groups will be sorted by this attribute when possible.
    """

    by_order = lambda x: deps.nodes[x].get('order', x)

    def inner_sort(candidates, dep_counts):
        best_groups = []
        best_score = (inf, inf)

        for type in candidates:
            next_candidates = deepcopy(candidates)
            next_dep_counts = deepcopy(dep_counts)
            next_group = next_candidates.pop(type)

            for node in next_group:
                for _, child in deps.edges(node):
                    next_dep_counts[child] -= 1
                    if next_dep_counts[child] == 0:
                        child_type = deps.nodes[child]['group']
                        next_candidates.setdefault(child_type, []).append(child)
                        del next_dep_counts[child]

            remaining_groups = inner_sort(
                    next_candidates,
                    next_dep_counts,
            )
            score = len(remaining_groups), type

            if score < best_score:
                best_score = score
                best_groups = [
                        (type, sorted(next_group, key=by_order)),
                        *remaining_groups,
                ]

        if dep_counts and not candidates:
            raise nx.NetworkXUnfeasible("graph contains a cycle")

        return best_groups

    candidates = {}
    dep_counts = {}

    for v, d in deps.in_degree():
        if d > 0:
            dep_counts[v] = d
        else:
            type = deps.nodes[v]['group']
            candidates.setdefault(type, []).append(v)

    return inner_sort(candidates, dep_counts)

