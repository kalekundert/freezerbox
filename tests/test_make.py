#!/usr/bin/env python3

import freezerbox
import parametrize_from_file

from freezerbox import Database, parse_fields
from freezerbox.stepwise.make import Make
from schema_helpers import *
from mock_model import *

@parametrize_from_file(
        schema=Schema({
            'reagents': empty_ok({str: eval_freezerbox}),
            'expected': empty_ok([str]),
        }),
)
def test_make(reagents, expected, disable_capture):
    db = freezerbox.Database()
    tags = list(reagents.keys())

    for tag, reagent in reagents.items():
        db[tag] = reagent

    app = Make(db, tags)
    with disable_capture:
        assert app.protocol.steps == expected

@parametrize_from_file(
        schema=Schema({
            'maker': str,
            'expected': {str: eval_freezerbox},
        }),
)
def test_builtin_maker_attrs(maker, expected):
    db = Database()
    db['x1'] = x1 = MockReagent(
            synthesis=parse_fields(maker),
    )

    for attr, value in expected.items():
        assert getattr(x1.synthesis_maker, attr) == value

@pytest.fixture
def disable_capture(pytestconfig):
    # Equivalent to `pytest -s`, but temporary.
    # This is necessary because even `capfd.disabled()` leaves stdin in a state 
    # that somehow interferes with the redirection we're trying to do.

    class suspend_guard:

        def __init__(self):
            self.capmanager = pytestconfig.pluginmanager.getplugin('capturemanager')

        def __enter__(self):
            self.capmanager.suspend_global_capture(in_=True)

        def __exit__(self, _1, _2, _3):
            self.capmanager.resume_global_capture()

    yield suspend_guard()

