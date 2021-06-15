#!/usr/bin/env python3

import pytest
from freezerbox import load_db, parse_tag, Fields
from freezerbox.model import *
from pathlib import Path
from schema_helpers import *
from mock_model import *
from datetime import datetime

MOCK_DB = Path(__file__).parent / 'mock_excel_db'

@pytest.fixture(autouse=True)
def db(mock_plugins):
    MOCK_CONFIG = {
            'use': 'mock',
            'database': {
                'mock': {
                    'type': 'excel',
                    'dir': str(MOCK_DB),
                }
            }
    }
    return load_db(config=MOCK_CONFIG)


@parametrize_from_file(
        schema=Schema({
            'path': str,
            'tag': str,
            'expected': eval,
        }),
)
def test_path_from_tag(tmp_path, path, tag, expected):
    from freezerbox.loaders.excel import _path_from_tag

    path = tmp_path / path
    path.touch()

    tag = parse_tag(tag)
    hit = _path_from_tag(tmp_path, tag)

    if expected:
        assert hit == path
    else:
        assert hit == None


def test_f2(db, tag='f2'):
    assert isinstance(db[tag], NucleicAcid)
    assert db[tag].alt_names == ['name 1', 'name 2']
    assert db[tag].date == datetime(2021, 4, 19)
    assert db[tag].desc == "description"
    assert db[tag].molecule == 'DNA'
    assert db[tag].is_double_stranded == True
    assert db[tag].is_circular == False
    assert db[tag].ready == True

def test_f3(db, tag='f3'):
    assert isinstance(db[tag], NucleicAcid)
    assert db[tag].desc == "sequence from db"
    assert db[tag].seq == 'GAATTC'

def test_f4(db, tag='f4'):
    assert isinstance(db[tag], NucleicAcid)
    assert db[tag].desc == "sequence from file"
    assert db[tag].seq == 'AAGCTT'

def test_f5(db, tag='f5'):
    assert isinstance(db[tag], NucleicAcid)
    assert db[tag].desc == "sequence from synthesis"
    assert db[tag].synthesis_args == Fields(['mock'], {'seq': 'GGTCTC'})
    assert db[tag].seq == 'GGTCTC'

def test_f6(db, tag='f6'):
    assert isinstance(db[tag], NucleicAcid)
    assert db[tag].desc == "mw from db"
    assert db[tag].mw == pytest.approx(5000, abs=0.1)

def test_f7(db, tag='f7'):
    assert isinstance(db[tag], NucleicAcid)
    assert db[tag].desc == "mw from sequence"
    # http://molbiotools.com/dnacalculator.html
    assert db[tag].mw == pytest.approx(3582.45, abs=0.1)

def test_f8(db, tag='f8'):
    assert isinstance(db[tag], NucleicAcid)
    assert db[tag].desc == "conc from db"
    assert db[tag].conc_nM == 60

def test_f9(db, tag='f9'):
    assert isinstance(db[tag], NucleicAcid)
    assert db[tag].desc == "conc from cleanup"
    assert db[tag].synthesis_args == Fields(['mock'], {})
    assert db[tag].cleanup_args == [Fields(['mock'], {'conc': '50nM'})]
    assert db[tag].conc_nM == 50

def test_f10(db, tag='f10'):
    assert isinstance(db[tag], NucleicAcid)
    assert db[tag].desc == "molecule from db"
    assert db[tag].molecule == 'RNA'
    assert db[tag].is_single_stranded == True

def test_f11(db, tag='f11'):
    assert isinstance(db[tag], NucleicAcid)
    assert db[tag].desc == "molecule from synthesis"
    assert db[tag].synthesis_args == Fields(['mock'], {'molecule': 'ssRNA'})
    assert db[tag].molecule == 'RNA'
    assert db[tag].is_single_stranded == True

def test_f12(db, tag='f12'):
    assert isinstance(db[tag], NucleicAcid)
    assert db[tag].desc == "length from db"
    assert db[tag].length == 10

def test_f13(db, tag='f13'):
    assert isinstance(db[tag], NucleicAcid)
    assert db[tag].desc == "length from sequence"
    assert db[tag].seq == "GAATTC"
    assert db[tag].length == 6

def test_f14(db, tag='f14'):
    assert isinstance(db[tag], NucleicAcid)
    assert db[tag].desc == "circular from db"
    assert db[tag].is_circular == True

def test_f15(db, tag='f15'):
    assert isinstance(db[tag], NucleicAcid)
    assert db[tag].desc == "circular from synthesis"
    assert db[tag].synthesis_args == Fields(['mock'], {'circular': 'y'})
    assert db[tag].is_circular == True

def test_f16(db, tag='f16'):
    assert isinstance(db[tag], NucleicAcid)
    assert db[tag].desc == "ready from db"
    assert db[tag].ready == False


def test_o2(db, tag='o2'):
    assert isinstance(db[tag], Oligo)
    assert db[tag].name == 'o2_tm61'
    assert db[tag].desc == 'tm from name'
    assert db[tag].tm == pytest.approx(61, abs=0.1)

def test_o3(db, tag='o3'):
    assert isinstance(db[tag], Oligo)
    assert db[tag].desc == 'tm from sequence'
    assert db[tag].seq == 'TCTCGCGGTATCATTG'
    assert db[tag].tm == pytest.approx(48, abs=0.1)

def test_o4(db, tag='o4'):
    assert isinstance(db[tag], Oligo)
    assert db[tag].desc == 'ignore scale purification'


def test_p2(db, tag='p2'):
    assert isinstance(db[tag], Plasmid)
    assert db[tag].is_double_stranded
    assert db[tag].is_circular


def test_r2(db, tag='r2'):
    assert isinstance(db[tag], Protein)


def test_b2(db, tag='b2'):
    assert isinstance(db[tag], Buffer)
