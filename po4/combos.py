#!/usr/bin/env python3

from itertools import groupby, count
from more_itertools import unzip
from statistics import mean
from operator import attrgetter

# group_by_...(items, key):
#   Functions that yield (value, subitems) tuples.  Each item in `subitems` 
#   will be associated with the given value.

# Items will be maker instances

def iter_combo_makers(cls, solo_makers, groupers):
    # This function assumes that makers are `appcli.App` instances.  That's not 
    # great, but I think the effort to generalize this would not be worth it 
    # for now.
    for attrs in iter_combos(solo_makers, groupers):
        obj = cls.from_params()
        for k, v in attrs.items():
            setattr(obj, k, v)
        yield obj

def iter_combos(items, groupers):
    yield from _iter_combos(items, groupers, {})

def _iter_combos(items, groupers, attrs):
    if not items:
        return
    if not groupers:
        yield attrs, items
        return

    x = list(groupers.items())
    head, tail = x[0], x[1:]

    attr, grouper = head
    remaining_groupers = dict(tail)
    key = attrgetter(attr)

    for group_value, group_items in grouper(items, key=key):
        yield from _iter_combos(
                group_items,
                remaining_groupers,
                {**attrs, attr: group_value},
        )

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
    yield from groupby(sorted(items, key=key), key=key)
    
class merge:

    def __init__(self, aggregate):
        self.aggregate = aggregate

    def __call__(self, items, key=lambda x: x):
        if items:
            value = self.aggregate(map(key, items))
            yield value, items



