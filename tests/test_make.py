#!/usr/bin/env python3

import freezerbox
import parametrize_from_file

from stepwise.testing import disable_capture
from freezerbox import Database, parse_fields
from freezerbox.stepwise.make import Make
from schema_helpers import *
from mock_model import *
from os import getcwd

@parametrize_from_file(
        schema=Schema({
            'db': eval_db,
            Optional('tags', default=[]): [str],
            'expected': empty_ok([str]),
        }),
)
def test_make(db, tags, expected, disable_capture, mock_plugins):
    cwd = getcwd()

    tags = tags or list(db.keys())
    app = Make(db, tags)

    with disable_capture:
        assert app.protocol.steps == expected

    assert getcwd() == cwd

@parametrize_from_file(
        schema=Schema({
            'db': eval_db,
            'tags': [str],
            Optional('kwargs', default={}): {str: eval_pytest},
            'expected': [str],
        }),
)
def test_iter_targets(db, tags, kwargs, expected, mock_plugins):
    from freezerbox.stepwise.make import iter_targets
    targets = {str(x.tag) for x in iter_targets(db, tags, **kwargs)}
    assert targets == set(expected)

@parametrize_from_file(
        schema=Schema({
            'maker': str,
            'expected': {str: eval_freezerbox},
        }),
)
def test_builtin_maker_attrs(maker, expected, disable_capture):
    db = Database()
    db['x1'] = x1 = MockReagent(
            synthesis=parse_fields(maker),
    )

    with disable_capture:
        for attr, value in expected.items():
            assert getattr(x1.synthesis_maker, attr) == value

