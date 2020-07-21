#!/usr/bin/env python3

import pytest
import shlex
from po4 import Database, Tag, Protocol, Plasmid, Fragment, Oligo
from po4.stepwise import Make
from test_model import DummyConstruct
from utils import parametrize_via_toml

@parametrize_via_toml('test_make.toml')
def test_make(disable_capture, protocols, options, expected):
    db = Database()
    t7 = 'TAATACGACTCACTATA'

    # Create some dummy sequences for the protocols to use.
    db['p1'] = Plasmid(seq='GATTACA')
    db['p2'] = Plasmid(seq='GATTACA')
    db['f1'] = Fragment(seq='GATTACA')
    db['f2'] = Fragment(seq='GATTACA', conc='100ng/µL')
    db['f3'] = Fragment(seq='GATTACA', conc='75nM')
    db['f4'] = Fragment(seq='GATTACA')
    db['f5'] = Fragment(seq='GATTACA', conc='100ng/µL')
    db['f6'] = Fragment(seq='GATTACA', conc='75nM')
    db['f7'] = Fragment(seq=t7+300*'G')
    db['f8'] = Fragment(seq=t7+301*'G')
    db['o1'] = Oligo(seq='GATTACA')
    db['o2'] = Oligo(seq='GATTACA')
    db['o3'] = Oligo(seq='GATTACA')
    db['o4'] = Oligo(seq='GATTACA')

    tags = []
    for i, protocol_str in enumerate(protocols, 1):
        tag = Tag('d', i); tags.append(tag)
        protocol = Protocol.from_text(db, protocol_str)
        db[tag] = DummyConstruct(protocol=protocol)

    make = Make(db, tags, options)
    with disable_capture:
        p = make.protocol
    
    for cmd_i, expected_i in zip(p.commands, expected):
        assert cmd_i == expected_i

# Copied from stepwise
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
            pass

        def __exit__(self, _1, _2, _3):
            self.capmanager.resume_global_capture()

    yield suspend_guard()


