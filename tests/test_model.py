#!/usr/bin/env python3

import pytest
import datetime
import autoprop
from po4 import QueryError, DnaSeq, Protocol
from po4.model import *
from utils import *
from test_protocols import DummyProtocol

class DummyConstruct(Construct):
    tag_prefix = 'd'

    @property
    def is_double_stranded(self):
        return True

    @property
    def is_circular(self):
        return False

def test_database_getitem_setitem():
    db = Database()

    d0 = DummyConstruct()
    with pytest.raises(QueryError, match='not attached'): d0.db
    with pytest.raises(QueryError, match='not attached'): d0.tag
    with pytest.raises(QueryError, match="d0: not found in database"): db['d0']

    db['d1'] = d1 = DummyConstruct()
    db['d02'] = d2 = DummyConstruct()
    db['d', 3] = d3 = DummyConstruct()
    db[Tag('d', 4)] = d4 = DummyConstruct()

    with pytest.raises(LoadError, match="d1: already in database, cannot be replaced"):
        db['d1'] = DummyConstruct()
    with pytest.raises(LoadError, match="<.*DummyConstruct.*> cannot have tag 'p1': expected 'd' prefix"):
        db['p1'] = DummyConstruct()

    assert d1.db is db
    assert d2.db is db
    assert d3.db is db
    assert d4.db is db

    assert d1.tag == Tag('d', 1)
    assert d2.tag == Tag('d', 2)
    assert d3.tag == Tag('d', 3)
    assert d4.tag == Tag('d', 4)

    assert db['d1'] is d1
    assert db['d01'] is d1
    assert db['d', 1] is d1
    assert db[Tag('d', 1)] is d1

    assert db['d2'] is d2
    assert db['d02'] is d2
    assert db['d', 2] is d2
    assert db[Tag('d', 2)] is d2

    assert db['d3'] is d3
    assert db['d03'] is d3
    assert db['d', 3] is d3
    assert db[Tag('d', 3)] is d3

    assert db['d4'] is d4
    assert db['d04'] is d4
    assert db['d', 4] is d4
    assert db[Tag('d', 4)] is d4

def test_database_delitem():
    db = Database()
    db['d1'] = d1 = DummyConstruct()

    assert d1 in db
    assert d1.db is db
    assert d1.tag == Tag('d', 1)

    del db['d1']

    assert d1 not in db
    with pytest.raises(QueryError, match='not attached'): d1.db
    with pytest.raises(QueryError, match='not attached'): d1.tag

def test_database_contains():
    db = Database()
    d1 = DummyConstruct()
    assert d1 not in db

    db['d1'] = d1
    assert d1 in db

def test_database_iter():
    db = Database()
    db['d1'] = d1 = DummyConstruct()
    db['d2'] = d2 = DummyConstruct()

    values = {d1, d2}
    keys = {x.tag for x in values}
    items = {(x.tag, x) for x in values}

    assert set(db) == keys
    assert set(db.keys()) == keys
    assert set(db.values()) == values
    assert set(db.items()) == items

def test_database_len():
    db = Database()
    assert len(db) == 0

    db['d1'] = DummyConstruct()
    assert len(db) == 1

    db['d2'] = DummyConstruct()
    assert len(db) == 2


def test_tag():
    tag = Tag('p', 1)

    assert tag.type == 'p'
    assert tag.id == 1
    assert str(tag) == 'p1'


@parametrize_via_toml('test_model.toml')
def test_construct_seq(given_seq, protocol_seq, expected):
    kwargs = {}

    if given_seq != False:
        seq = given_seq['seq']
        kwargs['seq'] = (lambda: seq) if given_seq['defer'] else seq
    if protocol_seq != False:
        kwargs['protocol'] = DummyProtocol(protocol_seq)

    d1 = DummyConstruct(**kwargs)
    assert d1.seq == DnaSeq(expected)

def test_construct_seq_err():
    d1 = DummyConstruct()
    with pytest.raises(QueryError, match='no sequence specified'):
        d1.seq

@parametrize_via_toml('test_model.toml')
def test_construct_length(columns, expected):
    d1 = DummyConstruct(**columns)
    assert d1.length == expected

def test_construct_length_err():
    d1 = DummyConstruct()
    with pytest.raises(QueryError, match='no sequence specified'):
        d1.length

@parametrize_via_toml('test_model.toml')
def test_construct_name(columns, expected):
    d1 = DummyConstruct(**columns)
    assert d1.name == (expected or None)

@parametrize_via_toml('test_model.toml')
def test_construct_date(columns, expected):
    d1 = DummyConstruct(**columns)
    assert d1.date == (expected or None)

@parametrize_via_toml('test_model.toml')
def test_construct_desc(columns, expected):
    d1 = DummyConstruct(**columns)
    assert d1.desc == (expected or None)

def test_construct_protocol():
    d1 = DummyConstruct()

    with pytest.raises(QueryError, match="no protocol"):
        d1.protocol

    protocol = DummyProtocol('ATCG')
    d2 = DummyConstruct(protocol=protocol)
    d3 = DummyConstruct(protocol=lambda: protocol)

    assert d2.protocol is protocol
    assert d3.protocol is protocol

def test_construct_conc():
    d1 = DummyConstruct()

    with pytest.raises(QueryError, match="no concentration"):
        d1.conc_str

    d2 = DummyConstruct(seq='ATCG', conc='10 ng/µL')

    assert d2.conc_str == '10 ng/µL'
    assert d2.conc_ng_uL == pytest.approx(10)

    d3 = DummyConstruct(seq='ATCG', conc='10 nM')

    assert d3.conc_str == '10 nM'
    assert d3.conc_nM == pytest.approx(10)


def test_plasmid_mw():
    # http://molbiotools.com/dnacalculator.html
    p1 = Plasmid(seq='ATCG')

    assert p1.is_circular == (not p1.is_linear) == True
    assert p1.is_double_stranded == (not p1.is_single_stranded) == True
    assert p1.mw == pytest.approx(2471.58, rel=1e-3)

def test_fragment_mw():
    # 5'-phosphorylation assumed.
    # http://molbiotools.com/dnacalculator.html
    f1 = Fragment(protocol=DummyProtocol('ATCG'))

    assert f1.is_circular == (not f1.is_linear) == False
    assert f1.is_double_stranded == (not f1.is_single_stranded) == True
    assert f1.mw == pytest.approx(2507.61, rel=1e-3)

def test_oligo_mw():
    # 5'-OH assumed.
    # http://molbiotools.com/dnacalculator.html
    o1 = Oligo(seq='ATCG')

    assert o1.is_circular == (not o1.is_linear) == False
    assert o1.is_double_stranded == (not o1.is_single_stranded) == False
    assert o1.mw == pytest.approx(1173.82, rel=1e-3)

@parametrize_via_toml('test_model.toml')
def test_oligo_tm(seq, name, expected):
    o1 = Oligo(seq=seq, name=name)
    assert o1.tm == pytest.approx(expected)


