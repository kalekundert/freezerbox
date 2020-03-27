#!/usr/bin/env python3

import autoprop
from more_itertools import one
from dataclasses import dataclass
from collections import namedtuple
from configurator import Config
from voluptuous import Schema, Invalid
from pkg_resources import iter_entry_points
from Bio.SeqUtils import molecular_weight, MeltingTemp
from .config import load_config
from .errors import LoadError, QueryError, CheckError, only_raise
from .utils import *

class Database:

    def __init__(self, name=None):
        self.name = name
        self._constructs = {}

    def __iter__(self):
        yield from self._constructs

    def __len__(self):
        return len(self._constructs)

    def __getitem__(self, tag):
        tag = parse_tag(tag)
        try:
            return self._constructs[tag]
        except KeyError:
            raise QueryError(f"not found in database", culprit=tag) from None

    def __setitem__(self, tag, construct):
        tag = parse_tag(tag)
        if tag in self._constructs:
            raise LoadError(f"already in database, cannot be replaced", culprit=tag)
        if tag.type != construct.tag_prefix:
            raise LoadError(f"{construct} cannot have tag '{tag}': expected {construct.tag_prefix!r} prefix")

        self._constructs[tag] = construct
        construct._db = self
        construct._tag = tag

    def __delitem__(self, tag):
        construct = self._constructs.pop(parse_tag(tag))
        construct._db = None
        construct._tag = None

    def __contains__(self, construct):
        return construct._tag in self._constructs

    def keys(self):
        return self._constructs.keys()

    def values(self):
        return self._constructs.values()

    def items(self):
        return self._constructs.items()


@dataclass(frozen=True)
class Tag:
    type: str
    id: int

    def __str__(self):
        return f'{self.type}{self.id}'

@autoprop
class Construct:
    tag_prefix = None

    def __init__(self, **kwargs):
        self._db = None
        self._tag = None

        self._seq = kwargs.get('seq')
        self._name = kwargs.get('name')
        self._alt_names = kwargs.get('alt_names', [])
        self._date = kwargs.get('date')
        self._desc = kwargs.get('desc')
        self._length = kwargs.get('length')
        self._conc_str = kwargs.get('conc')
        self._protocol = kwargs.get('protocol')

    def check(self):
        self._check_seq()

    def _check_seq(self):
        from Bio import pairwise2
        from Bio.pairwise2 import format_alignment

        try:
            primary_seq = self.seq
            protocol_seq = self.protocol.product_seq
        except (QueryError, NotImplementedError):
            pass
        else:
            if primary_seq != protocol_seq:
                alignments = pairwise2.align.globalxx(primary_seq, protocol_seq)
                message = f"sequence doesn't match protocol\n" + format_alignment(*alignments[0])
                raise CheckError(message, culprit=self._tag)

    def get_db(self):
        if not self._db:
            raise QueryError("not attached to a database", culprit=self._tag)
        return self._db

    def get_tag(self):
        if not self._tag:
            raise QueryError("not attached to a database", culprit=self._tag)
        return self._tag

    def get_seq(self):
        # Allow the retrieval of the sequence to be deferred, e.g. so unused 
        # sequences never have to be read from disc.
        if callable(self._seq):
            self._seq = self._seq()

        # If we have instructions for how to make the construct, try getting
        # the sequence from that.
        if not self._seq and self._protocol:
            self._seq = self.protocol.product_seq

        if not self._seq:
            raise QueryError("no sequence specified", culprit=self._tag)

        # Always return a `Bio.Seq` object.
        if isinstance(self._seq, str):
            self._seq = DnaSeq(self._seq)

        return self._seq

    def get_length(self):
        if self._length:
            return self._length
        else:
            return len(self.seq)

    def get_name(self):
        return self._name

    def get_alt_names(self):
        return self._alt_names

    def get_date(self):
        return self._date

    def get_desc(self):
        return self._desc

    def get_protocol(self):
        if not self._protocol:
            raise QueryError("no protocol specified", culprit=self._tag)

        # Allow `self._protocol` to be a callable that returns a protocol, so 
        # that the protocol doesn't have to be loaded until it is actually 
        # needed.  This means lets the database load faster, and avoids 
        # generating errors relating to protocols that the user doesn't 
        # actively care about.
        if callable(self._protocol):
            self._protocol = self._protocol()

        return self._protocol

    def get_mw(self):
        from Bio.SeqUtils import molecular_weight
        mw = molecular_weight(
                seq=self.seq,
                double_stranded=self.is_double_stranded,
                circular=self.is_circular,
        )

        # For some reason Biopython just assumes 5' phosphorylation, so we need 
        # to correct for that here.
        hpo3 = 1.008 + 30.974 + 3*15.999
        if not self.is_phosphorylated:
            strands = 2 if self.is_double_stranded else 1
            ends = 0 if self.is_circular else strands
            mw -= hpo3 * ends

        return mw

    def get_conc_str(self):
        if not self._conc_str:
            raise QueryError("no concentration specified", culprit=self._tag)
        return self._conc_str

    def get_conc_nM(self):
        return parse_conc_nM(self.conc_str, self.mw)

    def get_conc_ng_uL(self):
        return parse_conc_ng_uL(self.conc_str, self.mw)

    @property
    def is_double_stranded(self):
        raise NotImplementedError

    @property
    def is_single_stranded(self):
        return not self.is_double_stranded

    @property
    def is_circular(self):
        raise NotImplementedError

    @property
    def is_linear(self):
        return not self.is_circular

    def is_phosphorylated(self):
        raise NotImplementedError


@autoprop
class Plasmid(Construct):
    tag_prefix = 'p'

    @property
    def is_double_stranded(self):
        return True

    @property
    def is_circular(self):
        return True

@autoprop
class Fragment(Construct):
    tag_prefix = 'f'

    @property
    def is_double_stranded(self):
        return self.protocol.is_product_double_stranded

    @property
    def is_circular(self):
        return False

    @property
    def is_phosphorylated(self):
        return self.protocol.is_product_phosphorylated


@autoprop
class Oligo(Construct):
    tag_prefix = 'o'

    def get_melting_temp(self):
        from Bio.SeqUtils import MeltingTemp

        # If the TM is encoded in the oligo name, use that.
        if m := re.search(r'[-_ ](TM|Tm|tm)=?(\d+)', self.name):
            return float(m.group(2))

        # Otherwise, calculate a Tm using the Wallace rule.  This isn't a 
        # particularly accurate method, but I chose it because it agrees most 
        # closely with NEB's Tm calculator, which is what I've been using for 
        # everything.
        else:
            return MeltingTemp.Tm_Wallace(self.seq)

    def get_tm(self):
        return self.melting_temp

    @property
    def is_double_stranded(self):
        return False

    @property
    def is_circular(self):
        return False

    @property
    def is_phosphorylated(self):
        # Right now, PO4 has no support for modified oligos at all.  
        return False

@only_raise(LoadError)
def load_db(use=None, config=None):
    if not config:
        # Can't test this line, because it reads the real configuration files 
        # on the tester's machine, and so cannot be made to produce consistent 
        # results.
        config = load_config()  # pragma: no cover

    if not use:
        try:
            use = config['use']
        except KeyError as err:
            raise LoadError("no database specified.") from None

    try:
        config_use = config['database'][use]
    except KeyError as err:
        raise LoadError(f"unknown database {use!r}") from None

    try:
        type_use = config_use['type']
    except KeyError as err:
        raise LoadError(f"no 'type' specified for database {use!r}") from None

    plugin = one(
            iter_entry_points('po4.databases', type_use),
            too_short=LoadError(f"no {type_use!r} database plugin found."),
            too_long=LoadError(f"multiple {type_use!r} database plugins found."),
    )
    plugin = plugin.load()

    if defaults := getattr(plugin, 'default_config'):
        config_use = (Config(defaults) + config_use).data

    if hasattr(plugin, 'schema'):
        schema = Schema(plugin.schema)
        config_use = schema(config_use)

    return plugin.load(config_use)

