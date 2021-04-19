#!/usr/bin/env python3

import freezerbox
import parametrize_from_file

from freezerbox.stepwise.make import Make
from schema_helpers import *
from mock_model import *

@parametrize_from_file(
        schema=Schema({
            'reagents': empty_ok({str: eval_freezerbox}),
            'expected': empty_ok([str]),
        }),
)
def test_make(reagents, expected):
    db = freezerbox.Database()
    tags = list(reagents.keys())

    for tag, reagent in reagents.items():
        db[tag] = reagent

    app = Make(db, tags)
    assert app.protocol.steps == expected

