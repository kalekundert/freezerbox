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
            'grouper': eval_freezerbox,
            'items': eval,
            Optional('key', default='lambda x: x'): eval,
            'expected': empty_ok([{
                'value': eval_pytest,
                'items': eval_pytest,
            }]),
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
            'items': empty_ok([eval_with(DummyItem=DummyItem)]),
            'group_by': empty_ok({str: eval_freezerbox}),
            'merge_by': empty_ok({str: eval_freezerbox}),
            Optional('keys', default={}): empty_ok({str: eval_freezerbox}),
            'expected': empty_ok([{
                'attrs': empty_ok({str: eval_pytest}),
                'items': [eval_with(DummyItem=DummyItem)],
            }]),
        }),
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
