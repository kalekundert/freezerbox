#!/usr/bin/env python3

import pytest
import shlex
from po4 import Database, Tag, Protocol, Plasmid, Fragment, Oligo
from po4.stepwise import Make
from test_model import DummyConstruct
from utils import parametrize_via_toml

@parametrize_via_toml('test_make.toml')
def test_make(protocols, options, expected):
    db = Database()

    # Create some dummy sequences for the protocols to use.
    db['p1'] = Plasmid(seq='GATTACA')
    db['p2'] = Plasmid(seq='GATTACA')
    db['f1'] = Fragment(seq='GATTACA')
    db['f2'] = Fragment(seq='GATTACA', conc='100ng/µL')
    db['f3'] = Fragment(seq='GATTACA', conc='75nM')
    db['f4'] = Fragment(seq='GATTACA')
    db['f5'] = Fragment(seq='GATTACA', conc='100ng/µL')
    db['f6'] = Fragment(seq='GATTACA', conc='75nM')

    tags = []
    for i, protocol_str in enumerate(protocols, 1):
        tag = Tag('d', i); tags.append(tag)
        protocol = Protocol.from_text(db, protocol_str)
        db[tag] = DummyConstruct(protocol=protocol)

    make = Make(db, tags, options)
    make._make_commands()

    for a, b in zip(make.stepwise_commands, expected):
        assert shlex.join(a) == b

