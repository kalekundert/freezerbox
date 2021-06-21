#!/usr/bin/env python3

import freezerbox
import pytest
import datetime
import autoprop
from freezerbox import Fields, QueryError
from freezerbox.model import *
from schema_helpers import *
from mock_model import *

kwargs_schema = lambda expected=eval_freezerbox: Schema({
    Optional('kwargs', {}): empty_ok({str: eval_freezerbox}),
    **error_or({
        'expected': expected,
    }),
})

def test_database_getitem_setitem():
    db = Database()

    x0 = MockReagent()
    with pytest.raises(QueryError, match='not attached'): x0.db
    with pytest.raises(QueryError, match='not attached'): x0.tag
    with pytest.raises(QueryError, match="x0: not found in database"): db['x0']

    db['x1'] = x1 = MockReagent()
    db['x02'] = x2 = MockReagent()
    db['x', 3] = x3 = MockReagent()
    db[Tag('x', 4)] = x4 = MockReagent()

    with pytest.raises(LoadError, match="x1: already in database, cannot be replaced"):
        db['x1'] = MockReagent()
    with pytest.raises(LoadError, match="MockReagent\\(\\) cannot have tag 'p1'\n. expected 'x' prefix"):
        db['p1'] = MockReagent()

    assert x1.db is db
    assert x2.db is db
    assert x3.db is db
    assert x4.db is db

    assert x1.tag == Tag('x', 1)
    assert x2.tag == Tag('x', 2)
    assert x3.tag == Tag('x', 3)
    assert x4.tag == Tag('x', 4)

    assert db['x1'] is x1
    assert db['x01'] is x1
    assert db['x', 1] is x1
    assert db[Tag('x', 1)] is x1

    assert db['x2'] is x2
    assert db['x02'] is x2
    assert db['x', 2] is x2
    assert db[Tag('x', 2)] is x2

    assert db['x3'] is x3
    assert db['x03'] is x3
    assert db['x', 3] is x3
    assert db[Tag('x', 3)] is x3

    assert db['x4'] is x4
    assert db['x04'] is x4
    assert db['x', 4] is x4
    assert db[Tag('x', 4)] is x4

def test_database_delitem():
    db = Database()
    db['x1'] = x1 = MockReagent()

    assert x1 in db
    assert x1.db is db
    assert x1.tag == Tag('x', 1)

    del db['x1']

    assert x1 not in db
    with pytest.raises(QueryError, match='not attached'): x1.db
    with pytest.raises(QueryError, match='not attached'): x1.tag

def test_database_contains():
    db = Database()
    x1 = MockReagent()
    assert x1 not in db

    db['x1'] = x1
    assert x1 in db

def test_database_iter():
    db = Database()
    db['x1'] = x1 = MockReagent()
    db['x2'] = x2 = MockReagent()

    values = {x1, x2}
    keys = {x.tag for x in values}
    items = {(x.tag, x) for x in values}

    assert set(db) == keys
    assert set(db.keys()) == keys
    assert set(db.values()) == values
    assert set(db.items()) == items

def test_database_len():
    db = Database()
    assert len(db) == 0

    db['x1'] = MockReagent()
    assert len(db) == 1

    db['x2'] = MockReagent()
    assert len(db) == 2


def test_tag():
    tag = Tag('p', 1)

    assert tag.type == 'p'
    assert tag.id == 1
    assert str(tag) == 'p1'


def test_reagent_repr():
    x1 = MockReagent()
    x2 = MockReagent(a='b')
    x3 = MockReagent(a='b', c='d')

    assert repr(x1) == "MockReagent()"
    assert repr(x2) == "MockReagent(a='b')"
    assert repr(x3) == "MockReagent(a='b', c='d')"

    db = Database()
    db['x1'] = x1
    db['x2'] = x2
    db['x3'] = x3

    assert repr(x1) == "MockReagent('x1')"
    assert repr(x2) == "MockReagent('x2', a='b')"
    assert repr(x3) == "MockReagent('x3', a='b', c='d')"

def test_reagent_intermediate_repr():
    x1 = MockReagent(
            synthesis=Fields(['m'], {}),
    )
    i1 = x1.make_intermediate(0)

    assert repr(x1) == "MockReagent(synthesis=Fields(['m'], {}))"
    assert repr(i1) == "MockReagentIntermediate(step=0, synthesis=Fields(['m'], {}))"

@parametrize_from_file(schema=kwargs_schema())
def test_reagent_name(kwargs, expected, error):
    db = Database()
    db['x1'] = x1 = MockReagent(**kwargs)
    with error:
        assert x1.name == expected

@parametrize_from_file(schema=kwargs_schema())
def test_reagent_alt_names(kwargs, expected, error):
    db = Database()
    db['x1'] = x1 = MockReagent(**kwargs)
    with error:
        assert x1.alt_names == expected

@parametrize_from_file(schema=kwargs_schema())
def test_reagent_date(kwargs, expected, error):
    db = Database()
    db['x1'] = x1 = MockReagent(**kwargs)
    with error:
        assert x1.date == expected

@parametrize_from_file(schema=kwargs_schema())
def test_reagent_desc(kwargs, expected, error):
    db = Database()
    db['x1'] = x1 = MockReagent(**kwargs)
    with error:
        assert x1.desc == expected

@parametrize_from_file(schema=kwargs_schema())
def test_reagent_ready(kwargs, expected, error):
    db = Database()
    db['x1'] = x1 = MockReagent(**kwargs)
    with error:
        assert x1.ready == expected

def test_reagent_maker_args_1():
    db = Database()
    db['x1'] = x1 = MockReagent(
            synthesis=Fields(['m'], {'conc': '1 nM'}),
            cleanups=[
                Fields(['m'], {'conc': '2 nM'}),
                Fields(['m'], {'conc': '3 nM'}),
            ],
    )
    assert x1.synthesis_args[0] == 'm'
    assert x1.synthesis_args['conc'] == '1 nM'

    assert x1.cleanup_args[0][0] == 'm'
    assert x1.cleanup_args[0]['conc'] == '2 nM'

    assert x1.cleanup_args[1][0] == 'm'
    assert x1.cleanup_args[1]['conc'] == '3 nM'

def test_reagent_maker_args_2():
    db = Database()
    db['x1'] = x1 = MockReagent(
            synthesis=lambda: Fields(['m'], {'conc': '1 nM'}),
            cleanups=lambda: [
                Fields(['m'], {'conc': '2 nM'}),
                Fields(['m'], {'conc': '3 nM'}),
            ],
    )
    assert x1.synthesis_args[0] == 'm'
    assert x1.synthesis_args['conc'] == '1 nM'

    assert x1.cleanup_args[0][0] == 'm'
    assert x1.cleanup_args[0]['conc'] == '2 nM'

    assert x1.cleanup_args[1][0] == 'm'
    assert x1.cleanup_args[1]['conc'] == '3 nM'

def test_reagent_makers(mock_plugins):
    db = Database()
    db['x1'] = x1 = MockReagent(
            synthesis=Fields(['m'], {'conc': '1 nM'}),
            cleanups=[
                Fields(['m'], {'conc': '2 nM'}),
                Fields(['m'], {'conc': '3 nM'}),
            ],
    )
    m1 = x1.synthesis_maker
    m2 = x1.cleanup_makers[0]
    m3 = x1.cleanup_makers[1]

    assert isinstance(m1, MockMaker)
    assert m1.product_conc == Quantity(1, 'nM')

    assert isinstance(m2, MockMaker)
    assert m2.product_conc == Quantity(2, 'nM')

    assert isinstance(m3, MockMaker)
    assert m3.product_conc == Quantity(3, 'nM')

def test_reagent_maker_err_1():
    db = Database()
    db['x1'] = x1 = MockReagent()
    with pytest.raises(QueryError, match="no synthesis specified"):
        x1.synthesis_args
    with pytest.raises(QueryError, match="no synthesis specified"):
        x1.synthesis_maker
    with pytest.raises(QueryError, match="no synthesis specified"):
        x1.cleanup_args
    with pytest.raises(QueryError, match="no synthesis specified"):
        x1.cleanup_makers

def test_reagent_maker_err_2(mock_plugins):
    db = Database()
    db['x1'] = x1 = MockReagent(
            # no synthesis
            cleanups=[
                Fields(['m'], {'conc': '2 nM'}),
                Fields(['m'], {'conc': '3 nM'}),
            ],
    )
    with pytest.raises(QueryError, match="no synthesis specified"):
        x1.cleanup_args
    with pytest.raises(QueryError, match="no synthesis specified"):
        x1.cleanup_makers

def test_reagent_get_maker_attr_1(mock_plugins):
    db = Database()
    db['x1'] = x1 = MockReagent(
            synthesis=Fields(['m'], {'conc': '1 nM'}),
            cleanups=[
                Fields(['m'], {'conc': '2 nM'}),
                Fields(['m'], {'conc': '3 nM'}),
            ],
    )
    assert x1.get_maker_attr('product_conc') == Quantity(3, 'nM')
    assert x1.get_maker_attr('product_conc', None) == Quantity(3, 'nM')

def test_reagent_get_maker_attr_2(mock_plugins):
    db = Database()
    db['x1'] = x1 = MockReagent(
            synthesis=Fields(['m'], {'conc': '1 nM'}),
            cleanups=[
                Fields(['m'], {'conc': '2 nM'}),
                Fields(['m'], {}),
            ],
    )
    assert x1.get_maker_attr('product_conc') == Quantity(2, 'nM')
    assert x1.get_maker_attr('product_conc', None) == Quantity(2, 'nM')

def test_reagent_get_maker_attr_3(mock_plugins):
    db = Database()
    db['x1'] = x1 = MockReagent(
            synthesis=Fields(['m'], {'conc': '1 nM'}),
            cleanups=[
                Fields(['m'], {}),
                Fields(['m'], {}),
            ],
    )
    assert x1.get_maker_attr('product_conc') == Quantity(1, 'nM')
    assert x1.get_maker_attr('product_conc', None) == Quantity(1, 'nM')

def test_reagent_get_maker_attr_4(mock_plugins):
    db = Database()
    db['x1'] = x1 = MockReagent(
            synthesis=Fields(['m'], {}),
            cleanups=[
                Fields(['m'], {}),
                Fields(['m'], {}),
            ],
    )
    with pytest.raises(QueryError, match='product_conc'):
        x1.get_maker_attr('product_conc')
    assert x1.get_maker_attr('product_conc', None) == None

def test_reagent_get_maker_attr_5():
    db = Database()
    db['x1'] = x1 = MockReagent()
    with pytest.raises(QueryError, match='product_conc'):
        x1.get_maker_attr('product_conc')
    assert x1.get_maker_attr('product_conc', None) == None


@parametrize_from_file(schema=kwargs_schema())
def test_molecule_seq(kwargs, expected, error, mock_plugins):
    db = Database()
    db['x1'] = x1 = MockMolecule(**kwargs)
    with error:
        assert x1.seq == expected

        # Make sure the sequence is cached:
        x1._attrs['seq'] = '!!!'
        assert x1.seq == expected

@parametrize_from_file(schema=kwargs_schema())
def test_molecule_length(kwargs, expected, error):
    db = Database()
    db['x1'] = x1 = MockMolecule(**kwargs)
    with error:
        assert x1.length == expected

@parametrize_from_file(
        schema=kwargs_schema([eval_freezerbox]),
)
def test_molecule_conc(kwargs, expected, error, mock_plugins):
    db = Database()
    db['x1'] = x1 = MockMolecule(**kwargs)

    get_by_unit = {
            'nM': lambda: x1.conc_nM,
            'uM': lambda: x1.conc_uM,
            'µM': lambda: x1.conc_uM,
            'ng/uL': lambda: x1.conc_ng_uL,
            'ng/µL': lambda: x1.conc_ng_uL,
            'mg/mL': lambda: x1.conc_mg_mL,
    }

    # The first expected value should have the same units as the specified 
    # concentration.
    with error:
        assert x1.conc == expected[0]

    for q in expected:
        with error:
            assert x1.get_conc(q.unit).value == pytest.approx(q.value)
            assert x1.get_conc(q.unit).unit == q.unit
        with error:
            assert get_by_unit[q.unit]() == pytest.approx(q.value)

@parametrize_from_file(
        schema=kwargs_schema({str: eval_freezerbox}),
)
def test_molecule_volume(kwargs, expected, error, mock_plugins):
    db = Database()
    db['x1'] = x1 = MockMolecule(**kwargs)

    with error:
        assert x1.volume == expected['quantity']
    with error:
        assert x1.volume_uL == expected['uL']


def test_protein_mw():
    db = Database()
    db['r1'] = r1 = Protein(seq='DYKDDDDK')
    assert r1.mw == pytest.approx(1012.98, abs=0.1)

def test_protein_mw_err():
    db = Database()
    db['r1'] = r1 = Protein(seq='X')
    with pytest.raises(QueryError, match="'X' is not a valid unambiguous letter for protein"):
        r1.mw

@parametrize_from_file(
        schema=kwargs_schema({
            'molecule': eval,
            'strandedness': eval,
        }),
)
def test_nucleic_acid_molecule(kwargs, expected, error, mock_plugins):
    db = Database()
    db['f1'] = f1 = NucleicAcid(**kwargs)
    with error:
        assert f1.molecule == expected['molecule']
        assert f1.is_double_stranded == (expected['strandedness'] == 2)
        assert f1.is_single_stranded == (expected['strandedness'] == 1)

@parametrize_from_file(schema=kwargs_schema())
def test_nucleic_acid_circular(kwargs, expected, error, mock_plugins):
    db = Database()
    db['f1'] = f1 = NucleicAcid(**kwargs)
    with error:
        assert f1.is_circular == expected
        assert f1.is_linear == (not expected)

@parametrize_from_file(
        schema=kwargs_schema(),
)
def test_nucleic_acid_mw(kwargs, expected, error):
    # 5'-phosphorylation assumed.
    # http://molbiotools.com/dnacalculator.html
    db = Database()
    db['f1'] = f1 = NucleicAcid(**kwargs)
    with error:
        assert f1.mw == pytest.approx(expected, abs=0.1)

def test_plasmid_mw():
    # http://molbiotools.com/dnacalculator.html
    db = Database()
    db['p1'] = p1 = Plasmid(seq='ATCG')

    assert p1.is_circular == (not p1.is_linear) == True
    assert p1.is_double_stranded == (not p1.is_single_stranded) == True
    assert p1.mw == pytest.approx(2471.58, abs=0.1)

def test_oligo_mw():
    # 5'-OH assumed.
    # http://molbiotools.com/dnacalculator.html
    db = Database()
    db['o1'] = o1 = Oligo(seq='ATCG')

    assert o1.is_circular == (not o1.is_linear) == False
    assert o1.is_double_stranded == (not o1.is_single_stranded) == False
    assert o1.mw == pytest.approx(1173.82, abs=0.1)

@parametrize_from_file(schema=kwargs_schema())
def test_oligo_tm(kwargs, expected, error):
    db = Database()
    db['o1'] = o1 = Oligo(**kwargs)
    with error:
        assert o1.tm == pytest.approx(expected)


def test_intermediate(mock_plugins):
    db = Database()
    db['x1'] = x1 = MockMolecule(
            synthesis=Fields('m', {'conc': '1 nM'}),
            cleanups=[
                Fields('m', {'conc': '2 nM'}),
                Fields('m', {'conc': '3 nM'}),
            ],
    )

    # Access the concentration before creating the intermediates so that a 
    # concentration value is cached.  The intermediates will need to forget 
    # this value:
    assert x1.conc == Quantity(3, 'nM')

    i1 = x1.make_intermediate(0)
    i2 = x1.make_intermediate(1)
    i3 = x1.make_intermediate(2)

    with pytest.raises(QueryError) as err:
        x1.make_intermediate(3)

    assert err.match("x1: intermediate 3 doesn't exist")
    assert err.match("intermediates:")
    assert err.match("0: m conc='1 nM'")
    assert err.match("1: m conc='2 nM'")
    assert err.match("2: m conc='3 nM'")

    # Access the concentration again after creating the intermediates, to make 
    # sure that doing so does not somehow re-establish the cache:
    assert x1.conc == Quantity(3, 'nM')

    # Test that precursors are correct:
    assert i2.precursor is i1
    assert i3.precursor is i2

    # Test that fields are correct:
    assert i1.maker_args[0] == 'm'
    assert i1.maker_args['conc'] == '1 nM'
    assert i2.maker_args[0] == 'm'
    assert i2.maker_args['conc'] == '2 nM'
    assert i3.maker_args[0] == 'm'
    assert i3.maker_args['conc'] == '3 nM'

    # Test that makers are correct:
    assert i1.maker.product_conc == Quantity(1, 'nM')
    assert i2.maker.product_conc == Quantity(2, 'nM')
    assert i3.maker.product_conc == Quantity(3, 'nM')

    # Test that properties depending on fields are re-evaluated correctly.
    assert i1.conc == Quantity(1, 'nM')
    assert i2.conc == Quantity(2, 'nM')
    assert i3.conc == Quantity(3, 'nM')

