#!/usr/bin/env python3

import freezerbox
import pytest
import parametrize_from_file

from parametrize_from_file import Namespace, cast, defaults, star
from voluptuous import Schema, Invalid, Coerce, And, Or, Optional
from more_itertools import always_iterable
from pathlib import Path

TEST_DIR = Path(__file__).parent

def eval_db(reagents):
    reagents = with_freeze.eval(reagents)

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

def empty(factory):
    return lambda x: x or factory()

def map_list(*funcs):

    def inner_map(xs):
        out = []
        for x in xs:
            for f in always_iterable(funcs):
                x = f(x)
            out.append(x)
        return out

    return inner_map

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
