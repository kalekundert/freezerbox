#!/usr/bin/env python3

import freezerbox
import pytest
import parametrize_from_file

from parametrize_from_file import star
from parametrize_from_file.voluptuous import Namespace
from voluptuous import Schema, Invalid, Coerce, And, Or, Optional
from pathlib import Path

TEST_DIR = Path(__file__).parent

def eval_db(reagents):
    schema = Schema({
            str: with_freeze.eval,
    })
    reagents = schema(reagents)

    meta = reagents.pop('meta', {})
    config = meta.get('config', {})
    paths = meta.get('paths', {})

    config = freezerbox.Config(config, paths)
    db = freezerbox.Database(config)

    for tag, reagent in reagents.items():
        db[tag] = reagent

    if not db.name:
        db.name = 'mock'

    return db

def empty_ok(x):
    return Or(x, And('', lambda y: type(x)()))

def approx_Q(x):
    from stepwise import Quantity
    q = Quantity.from_anything(x)
    return pytest.approx(q, abs=Quantity(1e-6, q.unit))

with_py = Namespace(
        'from operator import attrgetter',
)
with_nx = Namespace(
        'import networkx as nx',
)
with_pytest = Namespace(
        'from pytest import *',
)
with_sw = Namespace(
        with_py,
        with_pytest,
        'from stepwise import Quantity, Q, pl, ul, ol, table',
        approx_Q=approx_Q,
)
with_freeze = Namespace(
        with_sw,
        'import freezerbox; from freezerbox import *',
        'from mock_model import *',
        TEST_DIR=TEST_DIR,
)

@pytest.fixture
def files(request, tmp_path):
    for name, contents in request.param.items():
        p = tmp_path / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(contents)

    return tmp_path

