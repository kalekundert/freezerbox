#!/usr/bin/env python3

import pytest, rtoml
from freezerbox import load_db, Fields
from freezerbox.model import *
from freezerbox.config import BUILTIN_CONF
from pathlib import Path
from mock_model import *
from datetime import datetime

MOCK_DB = Path(__file__).parent / 'mock_excel_db'

@pytest.fixture(autouse=True)
def db(mock_plugins):
    # Load the real defaults, so we can test them.
    defaults = rtoml.load(BUILTIN_CONF)

    MOCK_CONFIG = {
            'use': 'mock',
            'tag_pattern': r'([pforsb])(\d+)',
            'database': {
                'mock': [
                    {
                        'format': 'excel',
                        'reagent': 'plasmid',
                        'path': str(MOCK_DB / 'plasmids.xlsx'),
                        'sequence': str(MOCK_DB / 'plasmids/{tag_match[1]}{tag_match[2]:0>3}.dna'),
                        'tag_template': 'p${i+2}',
                    }, {
                        'format': 'excel',
                        'reagent': 'nucleic_acid',
                        'path': str(MOCK_DB / 'fragments.xlsx'),
                        'sequence': str(MOCK_DB / 'fragments/{tag}.dna'),
                    }, {
                        'format': 'excel',
                        'reagent': 'oligo',
                        'path': str(MOCK_DB / 'oligos.xlsx'),
                        'worksheet': 'Oligos',
                    }, {
                        'format': 'excel',
                        'reagent': 'protein',
                        'path': str(MOCK_DB / 'proteins.xlsx'),
                        'sequence': str(MOCK_DB / 'proteins/{tag}.prot'),
                    }, {
                        'format': 'excel',
                        'reagent': 'strain',
                        'path': str(MOCK_DB / 'strains.xlsx'),
                    }, {
                        'format': 'excel',
                        'reagent': 'buffer',
                        'path': str(MOCK_DB / 'buffers.xlsx'),
                    },
                ],
            },
            'features': defaults['features'],
    }
    return load_db(config=MOCK_CONFIG)


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
    assert db[tag].seq == 'TCGCGCGTTTCGGTGATGACGGTGAAAACCTCTGACACATGCAGCTCCCGGAGACGGTCACAGCTTGTCTGTAAGCGGATGCCGGGAGCAGACAAGCCCGTCAGGGCGCGTCAGCGGGTGTTGGCGGGTGTCGGGGCTGGCTTAACTATGCGGCATCAGAGCAGATTGTACTGAGAGTGCACCATATGCGGTGTGAAATACCGCACAGATGCGTAAGGAGAAAATACCGCATCAGGCGCCATTCGCCATTCAGGCTGCGCAACTGTTGGGAAGGGCGATCGGTGCGGGCCTCTTCGCTATTACGCCAGCTGGCGAAAGGGGGATGTGCTGCAAGGCGATTAAGTTGGGTAACGCCAGGGTTTTCCCAGTCACGACGTTGTAAAACGACGGCCAGTGAATTCGAGCTCGGTACCCGGGGATCCTCTAGAGTCGACCTGCAGGCATGCAAGCTTGGCGTAATCATGGTCATAGCTGTTTCCTGTGTGAAATTGTTATCCGCTCACAATTCCACACAACATACGAGCCGGAAGCATAAAGTGTAAAGCCTGGGGTGCCTAATGAGTGAGCTAACTCACATTAATTGCGTTGCGCTCACTGCCCGCTTTCCAGTCGGGAAACCTGTCGTGCCAGCTGCATTAATGAATCGGCCAACGCGCGGGGAGAGGCGGTTTGCGTATTGGGCGCTCTTCCGCTTCCTCGCTCACTGACTCGCTGCGCTCGGTCGTTCGGCTGCGGCGAGCGGTATCAGCTCACTCAAAGGCGGTAATACGGTTATCCACAGAATCAGGGGATAACGCAGGAAAGAACATGTGAGCAAAAGGCCAGCAAAAGGCCAGGAACCGTAAAAAGGCCGCGTTGCTGGCGTTTTTCCATAGGCTCCGCCCCCCTGACGAGCATCACAAAAATCGACGCTCAAGTCAGAGGTGGCGAAACCCGACAGGACTATAAAGATACCAGGCGTTTCCCCCTGGAAGCTCCCTCGTGCGCTCTCCTGTTCCGACCCTGCCGCTTACCGGATACCTGTCCGCCTTTCTCCCTTCGGGAAGCGTGGCGCTTTCTCATAGCTCACGCTGTAGGTATCTCAGTTCGGTGTAGGTCGTTCGCTCCAAGCTGGGCTGTGTGCACGAACCCCCCGTTCAGCCCGACCGCTGCGCCTTATCCGGTAACTATCGTCTTGAGTCCAACCCGGTAAGACACGACTTATCGCCACTGGCAGCAGCCACTGGTAACAGGATTAGCAGAGCGAGGTATGTAGGCGGTGCTACAGAGTTCTTGAAGTGGTGGCCTAACTACGGCTACACTAGAAGAACAGTATTTGGTATCTGCGCTCTGCTGAAGCCAGTTACCTTCGGAAAAAGAGTTGGTAGCTCTTGATCCGGCAAACAAACCACCGCTGGTAGCGGTGGTTTTTTTGTTTGCAAGCAGCAGATTACGCGCAGAAAAAAAGGATCTCAAGAAGATCCTTTGATCTTTTCTACGGGGTCTGACGCTCAGTGGAACGAAAACTCACGTTAAGGGATTTTGGTCATGAGATTATCAAAAAGGATCTTCACCTAGATCCTTTTAAATTAAAAATGAAGTTTTAAATCAATCTAAAGTATATATGAGTAAACTTGGTCTGACAGTTACCAATGCTTAATCAGTGAGGCACCTATCTCAGCGATCTGTCTATTTCGTTCATCCATAGTTGCCTGACTCCCCGTCGTGTAGATAACTACGATACGGGAGGGCTTACCATCTGGCCCCAGTGCTGCAATGATACCGCGAGACCCACGCTCACCGGCTCCAGATTTATCAGCAATAAACCAGCCAGCCGGAAGGGCCGAGCGCAGAAGTGGTCCTGCAACTTTATCCGCCTCCATCCAGTCTATTAATTGTTGCCGGGAAGCTAGAGTAAGTAGTTCGCCAGTTAATAGTTTGCGCAACGTTGTTGCCATTGCTACAGGCATCGTGGTGTCACGCTCGTCGTTTGGTATGGCTTCATTCAGCTCCGGTTCCCAACGATCAAGGCGAGTTACATGATCCCCCATGTTGTGCAAAAAAGCGGTTAGCTCCTTCGGTCCTCCGATCGTTGTCAGAAGTAAGTTGGCCGCAGTGTTATCACTCATGGTTATGGCAGCACTGCATAATTCTCTTACTGTCATGCCATCCGTAAGATGCTTTTCTGTGACTGGTGAGTACTCAACCAAGTCATTCTGAGAATAGTGTATGCGGCGACCGAGTTGCTCTTGCCCGGCGTCAATACGGGATAATACCGCGCCACATAGCAGAACTTTAAAAGTGCTCATCATTGGAAAACGTTCTTCGGGGCGAAAACTCTCAAGGATCTTACCGCTGTTGAGATCCAGTTCGATGTAACCCACTCGTGCACCCAACTGATCTTCAGCATCTTTTACTTTCACCAGCGTTTCTGGGTGAGCAAAAACAGGAAGGCAAAATGCCGCAAAAAAGGGAATAAGGGCGACACGGAAATGTTGAATACTCATACTCTTCCTTTTTCAATATTATTGAAGCATTTATCAGGGTTATTGTCTCATGAGCGGATACATATTTGAATGTATTTAGAAAAATAAACAAATAGGGGTTCCGCGCACATTTCCCCGAAAAGTGCCACCTGACGTCTAAGAAACCATTATTATCATGACATTAACCTATAAAAATAGGCGTATCACGAGGCCCTTTCGTC'
    assert db[tag].origin == 'pUC'          # inferred from sequence
    assert db[tag].resistance == ['AmpR']   # inferred from sequence

def test_p3(db, tag='p3'):
    assert isinstance(db[tag], Plasmid)
    assert db[tag].is_double_stranded
    assert db[tag].is_circular
    assert db[tag].origin == 'p15A'
    assert db[tag].resistance == ['AmpR', 'TetR']
    assert db[tag].antibiotics == ['Amp', 'Tet']

def test_p4(db, tag='p4'):
    assert isinstance(db[tag], Plasmid)
    assert db[tag].antibiotics == ['Amp', 'Kan']


def test_r2(db, tag='r2'):
    assert isinstance(db[tag], Protein)
    assert db[tag].seq == 'DYKDDDDK'


def test_s2(db, tag='s2'):
    assert isinstance(db[tag], Strain)
    assert db[tag].parent_strain == 's0'

def test_s3(db, tag='s3'):
    assert isinstance(db[tag], Strain)
    assert db[tag].plasmids == [db['p2'], db['p3']]

def test_s4(db, tag='s4'):
    assert isinstance(db[tag], Strain)
    assert db[tag].antibiotics == ['Amp', 'Kan']


def test_b2(db, tag='b2'):
    assert isinstance(db[tag], Buffer)
