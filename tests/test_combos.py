#!/usr/bin/env python3

from schema_helpers import *

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


@parametrize_from_file(
        schema=Schema({
            'grouper': eval_po4,
            'items': eval,
            Optional('key', default='lambda x: x'): eval,
            'expected': Or([{
                'value': eval_pytest,
                'items': eval_pytest,
            }], empty_list)
        }),
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

@parametrize_from_file(
        schema=Schema({
            'items': Or([eval_with(DummyItem=DummyItem)], empty_list),
            'group_by': Or({str: eval_po4}, empty_dict),
            'merge_by': Or({str: eval_po4}, empty_dict),
            'expected': Or([{
                'attrs': Or({str: eval_pytest}, empty_dict),
                'items': [eval_with(DummyItem=DummyItem)],
            }], empty_list),
        }),
)
def test_iter_combos(items, group_by, merge_by, expected):
    actual = [
            (attrs, list(items))
            for attrs, items in po4.iter_combos(
                items,
                group_by=group_by,
                merge_by=merge_by,
            )
    ]
    expected = [
            (x['attrs'], list(x['items']))
            for x in expected
    ]
    assert actual == expected
