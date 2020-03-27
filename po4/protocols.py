#!/usr/bin/env python3

import math
import autoprop
import inform
from more_itertools import one
from Bio.Restriction import AllEnzymes
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
        Protocol.subclasses[cls.name] = cls

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
    # Currently only single-digests of plasmids are supported (n terms of 
    # getting the product sequence).  It shouldn't be too hard to add 
    # support for double-digests when I run into a need for that.
    name = "RE"

    def __init__(self, db, template, enzymes):
        super().__init__(db)
        self._template_tag = template
        self._enzymes = enzymes

    @classmethod
    def from_params(cls, db, params):
        p = get_tag_pattern(Plasmid)

        with inform.add_culprit(cls.name):
            return cls(
                    db,
                    parse_param(params, 'template', p),
                    parse_param(params, 'enzyme', r'[\w\d,-]+').split(','),
            )

    def get_template(self):
        return self.db[self._template_tag]

    def get_template_tag(self):
        return self._template_tag

    def get_template_seq(self):
        return self.template.seq

    def get_enzymes(self):
        return self._enzymes

    def get_product_seq(self):
        enzyme = one(
                self.enzymes,
                QueryError("no enzymes specified.", culprit=self.name),
                QueryError(f"double-digests not yet supported: {len(self.enzymes)} enzymes specified: {', '.join(repr(x) for x in self.enzymes)}", culprit=self.name),
        )
        enzyme = re.sub('-HF(v2)?$', '', enzyme)
        try:
            pattern = AllEnzymes.get(enzyme)
        except ValueError:
            raise QueryError(f"unknown enzyme '{enzyme}'", culprit=self.name) from None

        seq = self.template_seq
        sites = pattern.search(seq)
        site = -1 + one(
                sites,
                QueryError(f"{enzyme!r} does not cut {self.template_tag!r}", culprit=self.name),
                QueryError(f"{enzyme!r} cuts {self.template_tag!r} {len(sites)} times", culprit=self.name),
        )
        return seq[site:] + seq[:site]


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
class GoldenGateProtocol(Protocol):
    name = "GG"

    def __init__(self, db, backbone, inserts, enzyme=None):
        super().__init__(db)
        self._backbone_tag = backbone
        self._insert_tags = inserts
        self._enzyme = enzyme

    @classmethod
    def from_params(cls, db, params):
        pf = get_tag_pattern(Plasmid, Fragment)

        with inform.add_culprit(cls.name):
            gg = cls(
                    db,
                    parse_param(params, 'bb', pf),
                    parse_param(params, 'ins', fr'{pf}(?:,{pf})*').split(','),
            )
            if 'enzyme' in params:
                gg._enzyme = parse_param(params, 'enzyme', r'[\w\d-]+')

            return gg


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

    def get_enzyme(self):
        return self._enzyme or 'BsaI-HFv2'


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
