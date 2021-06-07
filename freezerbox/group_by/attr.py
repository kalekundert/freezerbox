#!/usr/bin/env python3

from itertools import groupby, count
from more_itertools import unzip
from statistics import mean
from operator import attrgetter
from ..utils import join_lists

# group_by_...(items, key):
#   Functions that yield (value, subitems) tuples.  Each item in `subitems` 
#   will be associated with the given value.

# Items will be maker instances

def iter_combo_makers(
        factory,
        solo_makers, *,
        group_by={},
        merge_by={},
        keys={},
    ):
    combos = iter_combos(
            solo_makers,
            group_by=group_by,
            merge_by={
                'products': join_lists,
                **merge_by,
            },
            keys=keys,
    )
    for attrs, items in combos:
        combo_maker = factory()
        for k, v in attrs.items():
            setattr(combo_maker, k, v)
        yield combo_maker

def iter_combos(items, *, group_by={}, merge_by={}, keys={}):

    def get_key(attr):
        return keys.get(attr, lambda x: getattr(x, attr))

    def do_iter_combos(items, group_by, attrs):
        if not items:
            return

        if not group_by:
            items = list(items)

            for attr, merge in merge_by.items():
                key = get_key(attr)
                values = map(key, items)
                attrs[attr] = merge(values)

            yield attrs, items
            return

        x = list(group_by.items())
        head, tail = x[0], x[1:]

        attr, grouper = head
        group_by_tail = dict(tail)
        key = get_key(attr)

        for group_value, group_items in grouper(items, key=key):
            yield from do_iter_combos(
                    group_items,
                    group_by_tail,
                    {**attrs, attr: group_value},
            )

    yield from do_iter_combos(items, group_by, {})

class group_by_cluster:

    def __init__(self, *, max_diff, aggregate=mean):
        self.max_diff = max_diff
        self.aggregate = aggregate

    def __call__(self, items, key=lambda x: x):
        import numpy as np
        from sklearn.cluster import AgglomerativeClustering

        if len(items) == 0:
            return
        if len(items) == 1:
            value = self.aggregate(map(key, items))
            yield value, items
            return

        clustering = AgglomerativeClustering(
                linkage='complete',
                n_clusters=None,
                distance_threshold=self.max_diff,
        )

        # Specify `dtype=object` to prevent numpy from casting the keys, which 
        # in some cases can lead to confusing results (e.g. `np.int64` doesn't 
        # undergo true division with `statistics.mean()`).
        keys = map(key, items)
        keys = np.array(list(keys), dtype=object).reshape(-1, 1)

        labels = clustering.fit_predict(keys)

        by_label = lambda x: x[0]
        item_infos = sorted(
                zip(labels, items, keys.flat, count()),
                key=by_label,
        )

        # Note that we take care to yield the clustered items in roughly the 
        # same order as they were given to us.

        clusters = []

        for label, group in groupby(item_infos, key=by_label):
            _, group_items, group_keys, group_indices = unzip(group)
            clusters.append((
                    mean(group_indices),
                    self.aggregate(group_keys),
                    list(group_items),
            ))

        for order, value, items in sorted(clusters):
            yield value, items

def group_by_identity(items, key=lambda x: x):
    # The advantage of this algorithm is that it only requires the items to 
    # support the equality operator.  More efficient algorithms would require 
    # additional functionality, and therefore would not support all inputs:
    # 
    # - itertools.groupby(): inputs must be sorted, therefore items must 
    #   support comparison operators.
    # - dict of lists: items must be hashable.

    groups = []

    for item in items:
        item_key = key(item)

        for group in groups:
            if item_key == group[0]:
                group[1].append(item)
                break
        else:
            groups.append((item_key, [item]))

    yield from groups

