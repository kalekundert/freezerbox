#!/usr/bin/env python3

import pytest
from po4 import Database, Plasmid, Fragment, Oligo
from po4.protocols import *
from utils import *

@autoprop
class DummyProtocol(Protocol):
    name = 'DUMMY'

    def __init__(self, seq, db=None):
        super().__init__(db)
        self._seq = seq

    @classmethod
    def from_params(cls, db, params):
        return cls(params['seq'], db)

    def get_product_seq(self):
        return self._seq

class DummyProtocolSubclass(DummyProtocol):
    name = 'DUMMY_SUBCLS'

def test_protocol_from_text():
    db = Database()
    dummy1 = Protocol.from_text(db, 'DUMMY: seq=GATTACA')

    assert isinstance(dummy1, DummyProtocol)
    assert dummy1.db is db
    assert dummy1.product_seq == 'GATTACA'

    dummy2 = Protocol.from_text(db, 'DUMMY_SUBCLS: seq=TGTAATC')
    assert isinstance(dummy2, DummyProtocolSubclass)
    assert dummy2.db is db
    assert dummy2.product_seq == 'TGTAATC'

    with pytest.raises(ParseError, match="UNDEFINED: unknown protocol type"):
        Protocol.from_text(db, 'UNDEFINED: seq=TGTAATC')


def test_pcr_from_params():
    db = Database()
    pcr = PcrProtocol.from_params(db, dict(
            template='f1',
            primers='o1,o2',
            Ta='60°C',
            tx='30s',
            volume='50 µL',
    ))
    assert pcr.template_tag == 'f1'
    assert pcr.primer_tags == ('o1', 'o2')
    assert pcr.annealing_temp_C == 60
    assert pcr.extension_time_s == 30
    assert pcr.volume_uL == 50

@parametrize_via_toml('test_protocols.toml')
def test_pcr_from_params_err(params, error):
    with pytest.raises(ParseError, match=error):
        PcrProtocol.from_params(None, params)

def test_pcr_template():
    db = Database()
    db['p1'] = Plasmid(seq='AAAA')
    db['f1'] = Fragment(seq='CCCC')

    pcr1 = PcrProtocol(db, 'p1', ('o1', 'o2'))
    assert pcr1.template_tag == 'p1'
    assert pcr1.template_seq == 'AAAA'

    pcr2 = PcrProtocol(db, 'f1', ('o1', 'o2'))
    assert pcr2.template_tag == 'f1'
    assert pcr2.template_seq == 'CCCC'

def test_pcr_primers():
    db = Database()
    db['o1'] = Oligo(seq='AAAA')
    db['o2'] = Oligo(seq='CCCC')

    pcr = PcrProtocol(db, 'f1', ('o1', 'o2'))
    assert pcr.primer_seqs == ['AAAA', 'CCCC']

@parametrize_via_toml('test_protocols.toml')
def test_pcr_product(primer_fwd, primer_rev, template, product):
    db = Database()
    db['p1'] = Plasmid(seq=template)
    db['o1'] = Oligo(seq=primer_fwd)
    db['o2'] = Oligo(seq=primer_rev)

    pcr = PcrProtocol(db, 'p1', ('o1', 'o2'))
    assert pcr.product_seq == product.upper()
    assert pcr.product_len == len(product)

@parametrize_via_toml('test_protocols.toml')
def test_pcr_product_err(primer_fwd, primer_rev, template, error):
    db = Database()
    db['f1'] = Fragment(seq=template)
    db['o1'] = Oligo(seq=primer_fwd)
    db['o2'] = Oligo(seq=primer_rev)

    pcr = PcrProtocol(db, 'f1', ('o1', 'o2'))

    with pytest.raises(QueryError, match=error):
        pcr.product_seq

def test_pcr_annealing_temp():
    db = Database()
    db['o1'] = Oligo(name='O1_TM60')
    db['o2'] = Oligo(name='O2_TM62')

    pcr1 = PcrProtocol(db, 'f1', ('o1', 'o2'))
    assert pcr1.annealing_temp_C == 61  # Lowest primer Tm +1°C

    pcr2 = PcrProtocol(db, 'f1', ('o1', 'o2'), Ta=60)
    assert pcr2.annealing_temp_C == 60

@parametrize_via_toml('test_protocols.toml')
def test_pcr_extension_time(product_len, extension_time_s):
    db = Database()
    db['o1'] = o1 = Oligo(seq='tataacaggctgctgagacc')  # SR001
    db['o2'] = o2 = Oligo(seq='tctaggactatcaccggagg')  # SR002

    n = product_len - len(o1.seq) - len(o2.seq)
    db['f1'] = Fragment(seq=f'{o1.seq}{n * "A"}{o2.seq.reverse_complement()}')

    pcr = PcrProtocol(db, 'f1', ('o1', 'o2'))
    assert pcr.product_len == product_len
    assert pcr.extension_time_s == pytest.approx(extension_time_s)

def test_pcr_volume():
    pcr1 = PcrProtocol(None, None, None)
    assert pcr1.volume_uL == None

    pcr2 = PcrProtocol(None, None, None, volume=10)
    assert pcr2.volume_uL == 10


def test_digest_from_params():
    db = Database()
    digest = DigestProtocol.from_params(db, dict(
            template='p1',
            enzymes='BsaI',
            size='1kb',
    ))
    assert digest.template_tag == 'p1'
    assert digest.enzymes == ['BsaI']
    assert digest._product_size == 1000

@parametrize_via_toml('test_protocols.toml')
def test_digest_from_params_err(params, error):
    with pytest.raises(ParseError, match=error):
        DigestProtocol.from_params(None, params)

@parametrize_via_toml('test_protocols.toml')
def test_digest_product(seq, enzymes, circular, size, products, product):
    Construct = Plasmid if circular else Fragment
    tag = f'{Construct.tag_prefix}1'

    db = Database()
    db[tag] = Construct(seq=seq)

    digest = DigestProtocol(db, tag, enzymes, size or None)
    assert digest.product_seqs == [DnaSeq(x) for x in products]
    assert digest.product_seq == DnaSeq(product)

@parametrize_via_toml('test_protocols.toml')
def test_digest_product_err(seq, enzymes, error):
    db = Database()
    db['p1'] = Plasmid(seq=seq)

    digest = DigestProtocol(db, 'p1', enzymes)

    with pytest.raises(QueryError, match=error):
        digest.product_seq


def test_anneal_from_params():
    db = Database()
    db['o1'] = Oligo(seq='GATTACA')
    db['o2'] = Oligo(seq='TGTAATC')

    anneal = AnnealProtocol.from_params(db, dict(
            oligos='o1,o2',
            volume='10µL',
            conc='50µM',
            stock='200µM',
    ))
    assert anneal.oligo_tags == ('o1', 'o2')
    assert anneal.volume_uL == 10
    assert anneal.conc_uM == 50
    assert anneal.stock_uM == 200

@parametrize_via_toml('test_protocols.toml')
def test_anneal_from_params_err(params, error):
    db = Database()
    db['o1'] = Oligo(seq='GATTACA')
    db['o2'] = Oligo(seq='TGTAATC')

    with pytest.raises(ParseError, match=error):
        AnnealProtocol.from_params(db, params)


def test_gg_from_params():
    db = Database()
    gg = GoldenGateProtocol.from_params(db, dict(
            bb='p1',
            ins='f1,f2',
            enzyme='BbsI',
            volume='10µL',
    ))
    assert gg.backbone_tag == 'p1'
    assert gg.insert_tags == ['f1', 'f2']
    assert gg.enzyme == 'BbsI'
    assert gg.volume_uL == 10

@parametrize_via_toml('test_protocols.toml')
def test_gg_from_params_err(params, error):
    with pytest.raises(ParseError, match=error):
        GoldenGateProtocol.from_params(None, params)

def test_gg_bb_ins():
    db = Database()
    db['p1'] = Plasmid(seq='AAAA')
    db['f1'] = Fragment(seq='CCCC')
    db['f2'] = Fragment(seq='GGGG')

    gg = GoldenGateProtocol(db, 'p1', ['f1', 'f2'])
    assert gg.backbone_seq == 'AAAA'
    assert gg.insert_seqs == ['CCCC', 'GGGG']


def test_gib_from_params():
    db = Database()
    gib = GibsonProtocol.from_params(db, dict(
            bb='p1',
            ins='f1,f2',
            volume='10µL',
    ))
    assert gib.backbone_tag == 'p1'
    assert gib.insert_tags == ['f1', 'f2']
    assert gib.volume_uL == 10


def test_ligate_from_params():
    db = Database()
    lig = LigateProtocol.from_params(db, dict(
            bb='f1',
            ins='f2,f3',
            volume='10µL',
            kinase='y',
    ))
    assert lig.backbone_tag == 'f1'
    assert lig.insert_tags == ['f2', 'f3']
    assert lig.volume_uL == 10
    assert lig.use_kinase == True

@parametrize_via_toml('test_protocols.toml')
def test_ligate_from_params_err(params, error):
    with pytest.raises(ParseError, match=error):
        LigateProtocol.from_params(None, params)


def test_ivt_from_params():
    db = Database()
    ivt = IvtProtocol.from_params(db, dict(
            template='f1',
    ))
    assert ivt.template_tag == 'f1'
    assert ivt.is_product_double_stranded == False

@parametrize_via_toml('test_protocols.toml')
def test_ivt_from_params_err(params, error):
    with pytest.raises(ParseError, match=error):
        IvtProtocol.from_params(None, params)

@parametrize_via_toml('test_protocols.toml')
def test_ivt_product(template, expected):
    from Bio.Seq import Seq
    from Bio.Alphabet import RNAAlphabet

    db = Database()
    db['f1'] = Fragment(seq=template)

    ivt = IvtProtocol(db, 'f1')
    assert ivt.product_seq == Seq(expected, RNAAlphabet())

@parametrize_via_toml('test_protocols.toml')
def test_ivt_product_err(template, error):
    db = Database()
    db['f1'] = Fragment(seq=template)

    ivt = IvtProtocol(db, 'f1')

    with pytest.raises(QueryError, match=error):
        ivt.product_seq


def test_idt_from_params():
    db = Database()
    idt = IdtProtocol.from_params(db, dict(
            seq='GATTACA',
    ))
    assert idt.product_seq == 'GATTACA'

@parametrize_via_toml('test_protocols.toml')
def test_idt_from_params_err(params, error):
    with pytest.raises(ParseError, match=error):
        IdtProtocol.from_params(None, params)

