#!/usr/bin/env python3

import math
import autoprop
import inform
from inform import plural
from statistics import mean
from more_itertools import one
from .model import Plasmid, Fragment, Oligo
from .errors import ParseError, QueryError
from .utils import *

@autoprop
class Protocol:
    is_product_double_stranded = True
    is_product_phosphorylated = True
    subclasses = {}

    def __init__(self, db):
        self._db = db

    def __init_subclass__(cls):
        if x := getattr(cls, 'name', None):
            Protocol.subclasses[x] = cls

    @classmethod
    def from_text(cls, db, protocol_str):
        method, params_str = protocol_str.split(':', 1)
        params = parse_params(params_str)

        try:
            subcls = cls.subclasses[method]
        except KeyError:
            raise ParseError("unknown protocol type", culprit=method)

        return subcls.from_params(db, params)

    def get_db(self):
        # Allow `self._db` to be a callable that returns a database.  This 
        # allows `Construct.__init__()` to instantiate protocols before it has 
        # access to a database.
        return self._db() if callable(self._db) else self._db

    def get_product_seq(self):
        raise NotImplementedError(self.__class__)


@autoprop
class PcrProtocol(Protocol):
    name = "PCR"

    def __init__(self, db, template, primers, Ta=None, tx=None, volume=None):
        super().__init__(db)
        self._template_tag = template
        self._primer_tags = primers
        self._annealing_temp_C = Ta
        self._extension_time_s = tx
        self._volume_uL = volume

    @classmethod
    def from_params(cls, db, params):
        pf = get_tag_pattern(Plasmid, Fragment)
        o = get_tag_pattern(Oligo)

        with inform.add_culprit(cls.name):
            pcr = cls(
                    db,
                    parse_param(params, 'template', pf),
                    parse_param(params, 'primers', fr'({o}),\s*({o})'),
            )

            if 'Ta' in params:
                pcr._annealing_temp_C = parse_temp_C(params['Ta'])
            
            if 'tx' in params:
                pcr._extension_time_s = parse_time_s(params['tx'])

            if 'volume' in params:
                pcr._volume_uL = parse_volume_uL(params['volume'])

        return pcr
        
    def get_template(self):
        return self.db[self.template_tag]

    def get_template_tag(self):
        return self._template_tag

    def get_template_seq(self):
        return self.template.seq

    def get_primers(self):
        return [self.db[x] for x in self.primer_tags]

    def get_primer_tags(self):
        return self._primer_tags

    def get_primer_seqs(self):
        return [x.seq for x in self.primers]

    def get_product_seq(self):
        seq = self.template_seq
        primers = p = self.primer_seqs
        primer_pairs = [
                (p[0], p[1].reverse_complement()),
                (p[1], p[0].reverse_complement()),
        ]

        for fwd, rev in primer_pairs:
            # Assume perfect complementarity in the last 15 bases.  This is a 
            # bit of a hack...
            i = seq.find(fwd[-15:  ])
            j = seq.find(rev[   :15])

            if i > j and self.template.is_linear:
                continue
            if i >= 0 and j >= 0:
                break
        else:
            raise QueryError(f"{self.primer_tags[0]!r} and {self.primer_tags[1]!r} do not amplify {self.template_tag!r}")

        if i < j:
            return fwd[:-15] + seq[i:j] + rev
        else:
            return fwd[:-15] + seq[i:] + seq[:j] + rev

    def get_product_len(self):
        return len(self.product_seq)

    def get_annealing_temp_C(self):
        if self._annealing_temp_C:
            return self._annealing_temp_C

        tms = [x.tm for x in self.primers]
        return min(tms) + 1

    def get_extension_time_s(self):
        if self._extension_time_s:
            return self._extension_time_s

        time_sec = 30 * self.product_len / 1000
        if time_sec <= 10: return 10
        if time_sec <= 15: return 15
        return 30 * math.ceil(time_sec / 30)

    def get_volume_uL(self):
        return self._volume_uL


@autoprop
class InversePcrProtocol(PcrProtocol):
    name = "INV"

@autoprop
class DigestProtocol(Protocol):
    name = "RE"

    def __init__(self, db, template, enzymes, size=None):
        super().__init__(db)
        self._template_tag = template
        self._enzymes = enzymes
        self._product_size = size

    @classmethod
    def from_params(cls, db, params):
        p = get_tag_pattern(Plasmid)

        with inform.add_culprit(cls.name):
            self = cls(
                    db,
                    parse_param(params, 'template', p),
                    parse_param(params, 'enzymes', r'[\w\d,-]+').split(','),
            )
            if 'size' in params:
                self._product_size = parse_size_bp(params['size'])

            return self

    def get_template(self):
        return self.db[self._template_tag]

    def get_template_tag(self):
        return self._template_tag

    def get_template_seq(self):
        return self.template.seq

    def get_enzymes(self):
        return self._enzymes

    def get_product_seqs(self):
        from more_itertools import pairwise, flatten
        from Bio.Restriction import RestrictionBatch

        if not self.enzymes:
            raise QueryError("no enzymes specified.", culprit=self.name)

        enzymes_str = ','.join(repr(x) for x in self.enzymes)
        enzymes = [
                re.sub('-HF(v2)?$', '', x)
                for x in self.enzymes
        ]

        try:
            batch = RestrictionBatch(enzymes)
        except ValueError:
            raise QueryError(f"unknown enzyme(s): {enzymes_str}", culprit=self.name) from None

        seq = self.template_seq
        sites = [x-1 for x in flatten(batch.search(seq).values())]

        if not sites:
            raise QueryError(f"{enzymes_str} {plural(enzymes):/does/do} not cut {self.template_tag!r}", culprit=self.name)

        sites += [0, len(seq)] if self.template.is_linear else []
        sites = sorted(sites)

        if len(sites) == 1:
            site, = sites

        seqs = []
        for i,j in pairwise(sorted(sites)):
            seqs.append(seq[i:j])

        if self.template.is_circular:
            wrap_around = seq[sites[-1]:] + seq[:sites[0]]
            seqs.append(wrap_around)

        return seqs

    def get_product_seq(self):
        target_size = self._product_size or len(self.template_seq)
        return min(self.product_seqs, key=lambda x: abs(target_size - len(x)))


@autoprop
class AnnealProtocol(Protocol):
    name = "ANNEAL"

    def __init__(self, db, oligos, volume=None, conc=None, stock=None):
        super().__init__(db)
        self._oligo_tags = oligos
        self._volume_uL = volume
        self._conc_uM = conc
        self._stock_uM = stock

    @classmethod
    def from_params(cls, db, params):
        o = get_tag_pattern(Oligo)

        with inform.add_culprit(cls.name):
            anneal = cls(
                    db,
                    parse_param(params, 'oligos', fr'({o}),\s*({o})'),
            )
            mw = mean(x.mw for x in anneal.oligos)

            if 'volume' in params:
                anneal._volume_uL = parse_volume_uL(params['volume'])
            if 'conc' in params:
                anneal._conc_uM = parse_conc_uM(params['conc'], mw)
            if 'stock' in params:
                anneal._stock_uM = parse_conc_uM(params['stock'], mw)

        return anneal
        
    def get_product_seq(self):
        # This assumes that the two oligos are perfectly complementary, which 
        # may not be the case (e.g. there might be overhangs on either side).  
        # But there's no way to represent overhangs in PO₄ anyways, and this 
        # approximation should be close enough for most purposes.
        return self.oligo_seqs[0]

    def get_oligos(self):
        return [self.db[x] for x in self.oligo_tags]

    def get_oligo_tags(self):
        return self._oligo_tags

    def get_oligo_seqs(self):
        return [x.seq for x in self.oligos]

    def get_volume_uL(self):
        return self._volume_uL

    def get_conc_uM(self):
        return self._conc_uM

    def get_stock_uM(self):
        return self._stock_uM


@autoprop
class AssemblyProtocol(Protocol):
    allowed_tags = get_tag_pattern(Plasmid, Fragment)

    def __init__(self, db, backbone, inserts, volume=None):
        super().__init__(db)
        self._backbone_tag = backbone
        self._insert_tags = inserts
        self._volume_uL = volume

    @classmethod
    def from_params(cls, db, params):
        x = cls.allowed_tags

        with inform.add_culprit(cls.name):
            self = cls(
                    db,
                    parse_param(params, 'bb', x),
                    parse_param(params, 'ins', fr'{x}(?:,{x})*').split(','),
            )
            if 'volume' in params:
                self._volume_uL = parse_volume_uL(params['volume'])

            return self

    def get_backbone(self):
        return self.db[self.backbone_tag]

    def get_backbone_tag(self):
        return self._backbone_tag

    def get_backbone_seq(self):
        return self.backbone.seq

    def get_inserts(self):
        return [self.db[x] for x in self._insert_tags]

    def get_insert_tags(self):
        return self._insert_tags

    def get_insert_seqs(self):
        return [x.seq for x in self.inserts]

    def get_volume_uL(self):
        return self._volume_uL


@autoprop
class GoldenGateProtocol(AssemblyProtocol):
    name = "GG"

    def __init__(self, db, backbone, inserts, volume=None, enzyme=None):
        super().__init__(db, backbone, inserts, volume)
        self._enzyme = enzyme

    @classmethod
    def from_params(cls, db, params):
        gg = super().from_params(db, params)

        with inform.add_culprit(cls.name):
            if 'enzyme' in params:
                gg._enzyme = parse_param(params, 'enzyme', r'[\w\d-]+')

        return gg

    def get_enzyme(self):
        return self._enzyme or None

@autoprop
class GibsonProtocol(AssemblyProtocol):
    name = "GIB"


@autoprop
class LigateProtocol(AssemblyProtocol):
    name = "LIG"
    allowed_tags = get_tag_pattern(Fragment)

    def __init__(self, db, backbone, inserts, volume=None, use_kinase=False):
        super().__init__(db, backbone, inserts, volume)
        self._use_kinase = use_kinase

    @classmethod
    def from_params(cls, db, params):
        kld = super().from_params(db, params)

        with inform.add_culprit(cls.name):
            if 'kinase' in params:
                kld._use_kinase = parse_bool(params['kinase'])

        return kld
        
    def get_use_kinase(self):
        return self._use_kinase


@autoprop
class IvtProtocol(Protocol):
    name = "IVT"
    is_product_double_stranded = False

    # Caveats:
    # - Only recognizes the T7 promoter.
    # - Doesn't recognize any terminators; always reads to the end.
    # - Only works with fragments (see above).

    def __init__(self, db, template):
        super().__init__(db)
        self._template_tag = template

    @classmethod
    def from_params(cls, db, params):
        f = get_tag_pattern(Fragment)

        with inform.add_culprit(cls.name):
            return cls(
                    db,
                    parse_param(params, 'template', f),
            )

    def get_template(self):
        return self.db[self.template_tag]

    def get_template_tag(self):
        return self._template_tag

    def get_template_seq(self):
        return self.template.seq

    def get_product_seq(self):
        t7_promoter = 'TAATACGACTCACTATA'
        seq = str(self.template_seq)
        i = seq.find(t7_promoter)
        j = i + len(t7_promoter)

        if i < 0:
            raise QueryError(f"{self.template_tag!r} does not contain a T7 promoter ({t7_promoter!r}).", culprit=self.name)

        return DnaSeq(seq[j:]).transcribe()


@autoprop
class IdtProtocol(Protocol):
    name = "IDT"

    def __init__(self, db, seq):
        super().__init__(db)
        self._product_seq = seq

    @classmethod
    def from_params(cls, db, params):
        pfo = get_tag_pattern()

        with inform.add_culprit(cls.name):
            return cls(
                    db,
                    parse_param(params, 'seq', '[ATCGUatcgu]+', None),
            )

    def get_product_seq(self):
        return self._product_seq
