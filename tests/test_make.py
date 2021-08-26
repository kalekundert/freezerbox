#!/usr/bin/env python3

import freezerbox
import parametrize_from_file

from stepwise.testing import disable_capture
from freezerbox import Database, parse_fields
from freezerbox.stepwise.make import Make
from more_itertools import one
from schema_helpers import *
from mock_model import *
from os import getcwd

def _db_from_maker(x):
    if 'maker' in x:
        x['db'] = db = Database()
        x['tag'] = tag = 'x1'

        db[tag] = MockMolecule(
                synthesis=parse_fields(x['maker']),
        )
        del x['maker']

    return x

def _guess_tag(x):
    if 'tag' not in x:
        x['tag'] = one(x['db'], too_short=Invalid, too_long=Invalid)
    return x


@parametrize_from_file(
        schema=Schema({
            'db': eval_db,
            Optional('tags', default=[]): [str],
            'expected': empty_ok([str]),
        }),
)
def test_make(db, tags, expected, disable_capture, mock_plugins):
    cwd = getcwd()

    # Reverse to check that `Make()` puts the tags back in sorted order.
    tags = tags or list(reversed(db.keys()))
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
        schema=Schema(
            Or(
                And(
                    {
                        'db': eval_db,
                        'tag': str,
                        Optional('maker_attrs', default={}): {
                            str: eval_freezerbox,
                        },
                        Optional('reagent_attrs', default={}): {
                            str: eval_freezerbox,
                        },
                    },
                    _guess_tag,
                ),
                And(
                    {
                        'maker': str,
                        Optional('maker_attrs', default={}): {
                            str: eval_freezerbox,
                        },
                        Optional('reagent_attrs', default={}): {
                            str: eval_freezerbox,
                        },
                    },
                    _db_from_maker,
                ),
            ),
        ),
)
def test_builtin_maker_attrs(db, tag, maker_attrs, reagent_attrs, disable_capture):
    with disable_capture:
        reagent = db[tag]

        for key, value in maker_attrs.items():
            i, attr = key.split('.'); i = int(i)
            maker = reagent.make_intermediate(i).maker
            assert getattr(maker, attr) == value

        for attr, value in reagent_attrs.items():
            assert getattr(reagent, attr) == value
