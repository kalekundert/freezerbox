#!/usr/bin/env python3

from param_helpers import *

class DummyItem:

    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def __repr__(self):
        kwargs = ', '.join(f'{k}={v!r}' for k,v in self.kwargs.items())
        return f'DummyItem({kwargs})'

    def __eq__(self, other):
        return self.kwargs == other.kwargs

    def __getattr__(self, name):
        return self.kwargs[name]

with_dummy = Namespace(DummyItem=DummyItem)

@parametrize_from_file(
        schema=[
            cast(
                grouper=with_freeze.eval,
                items=with_py.eval,
                key=with_py.eval,
                expected=[empty(dict), with_pytest.eval],
            ),
            defaults(
                key=lambda x: x,
            ),
        ],
)
def test_group_by(grouper, items, key, expected):
    actual = [
            (k, list(it))
            for k, it in grouper(items, key=key)
    ]
    expected = [
            (x['value'], list(x['items']))
            for x in expected
    ]
    assert actual == expected

F = open('xxx', 'w')

@parametrize_from_file(
        schema=[
            cast(
                items=[empty(list), with_dummy.eval],
                group_by=[empty(dict), with_freeze.eval],
                merge_by=[empty(dict), with_freeze.eval],
                keys=[empty(dict), with_freeze.eval],
                expected=[
                    empty(list),
                    map_list(cast(
                        attrs=[empty(dict), with_pytest.eval],
                        items=with_dummy.eval,
                    )),
                ],
            ),
            defaults(
                keys={},
            ),
        ],
)
def test_iter_combos(items, group_by, merge_by, keys, expected):
    actual = [
            (attrs, list(items))
            for attrs, items in freezerbox.iter_combos(
                items,
                group_by=group_by,
                merge_by=merge_by,
                keys=keys,
            )
    ]
    expected = [
            (x['attrs'], list(x['items']))
            for x in expected
    ]
    assert actual == expected
