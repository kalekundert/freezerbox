#!/usr/bin/env python3

import freezerbox
import parametrize_from_file

from stepwise.testing import disable_capture
from freezerbox import Database, parse_fields
from freezerbox.stepwise.make import Make
from more_itertools import one
from param_helpers import *
from mock_model import *
from os import getcwd

def _db_from_maker(x):
    if 'maker' in x:
        x['db'] = db = Database({})
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
        schema=[
            cast(db=eval_db),
            defaults(tags=[]),
        ],
)
def test_make(db, tags, expected, disable_capture, mock_plugins):
    cwd = getcwd()

    tags = tags or list(db.keys())
    app = Make(db, tags)

    with disable_capture:
        assert app.protocol.steps == expected

    assert getcwd() == cwd

@parametrize_from_file(
        schema=[
            cast(db=eval_db, kwargs=with_py.eval),
            defaults(kwargs={}),
        ],
)
def test_collect_targets(db, tags, kwargs, expected, mock_plugins):
    from freezerbox.stepwise.make import collect_targets
    targets = {str(x.tag) for x in collect_targets(db, tags, **kwargs)}
    assert targets == set(expected)

@parametrize_from_file(
        schema=[
            cast(
                db=eval_db,
                maker_attrs=with_freeze.eval,
                reagent_attrs=with_freeze.eval,
            ),
            defaults(
                maker_attrs={},
                reagent_attrs={},
            ),

            # If the test includes a "maker" field, use that information to 
            # instantiate fill in the "db" and "tag" fields.  The "maker" field 
            # is removed.
            _db_from_maker,

            _guess_tag,
        ],
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
