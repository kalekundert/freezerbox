#!/usr/bin/env python3

import freezerbox
import parametrize_from_file

from freezerbox import Database, parse_fields
from freezerbox.stepwise.make import Make
from schema_helpers import *
from mock_model import *
from os import getcwd

@parametrize_from_file(
        schema=Schema({
            'db': eval_db,
            'expected': empty_ok([str]),
        }),
)
def test_make(db, expected, disable_capture, mock_plugins):
    cwd = getcwd()

    tags = list(db.keys())
    app = Make(db, tags)

    with disable_capture:
        assert app.protocol.steps == expected

    assert getcwd() == cwd

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

