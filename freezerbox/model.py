#!/usr/bin/env python3

import autoprop
import entrypoints
from more_itertools import one, only
from dataclasses import dataclass
from collections import namedtuple
from configurator import Config
from voluptuous import Schema
from inform import plural
from Bio.SeqUtils import molecular_weight, MeltingTemp
from .config import load_config
from .errors import LoadError, QueryError, CheckError, only_raise
from .utils import *

DB_PLUGINS = entrypoints.get_group_named('freezerbox.databases')
MAKER_PLUGINS = entrypoints.get_group_named('freezerbox.make')
INTERMEDIATE_SUBCLASSES = {}

class Database:

    def __init__(self, name='*unnamed database*'):
        self.name = name
        self._reagents = {}

    def __iter__(self):
        yield from self._reagents

    def __len__(self):
        return len(self._reagents)

    def __getitem__(self, tag):
        tag = parse_tag(tag)
        try:
            return self._reagents[tag]
        except KeyError:
            raise QueryError(f"not found in database", culprit=tag) from None

    def __setitem__(self, tag, reagent):
        tag = parse_tag(tag)
        if tag in self._reagents:
            raise LoadError("already in database, cannot be replaced", culprit=tag)
        if tag.type != reagent.tag_prefix:
            err = LoadError(
                    tag=tag,
                    reagent=reagent,
            )
            err.brief = "{reagent} cannot have tag '{tag}'"
            err.blame += "expected {reagent.tag_prefix!r} prefix"
            raise err

        self._reagents[tag] = reagent
        reagent._db = self
        reagent._tag = tag

    def __delitem__(self, tag):
        reagent = self._reagents.pop(parse_tag(tag))
        reagent._db = None
        reagent._tag = None
        autoprop.clear_cache(reagent)

    def __contains__(self, reagent):
        return reagent._tag in self._reagents

    def keys(self):
        return self._reagents.keys()

    def values(self):
        return self._reagents.values()

    def items(self):
        return self._reagents.items()


@dataclass(frozen=True)
class Tag:
    type: str
    id: int

    def __str__(self):
        return f'{self.type}{self.id}'


@autoprop.immutable
class Reagent:
    tag_prefix = None

    def __init__(self, **kwargs):
        self._db = None
        self._tag = None
        self._attrs = kwargs
        self._intermediates = {}

    def __repr__(self):
        attrs = list(self._attrs.items())
        if isinstance(self, IntermediateMixin):
            attrs.insert(0, ('step', self.step))

        attr_strs = [f'{k}={v!r}' for k, v in attrs]
        if self._tag:
            attr_strs.insert(0, repr(str(self._tag)))

        return f'{self.__class__.__qualname__}({", ".join(attr_strs)})'

    def check(self):
        pass

    def make_intermediate(self, step):
        if step in self._intermediates:
            return self._intermediates[step]

        if step > len(self.cleanup_args):
            err = QueryError(
                    culprit=self,
                    step=step,
                    synthesis_args=self.synthesis_args,
                    cleanup_args=self.cleanup_args,
            )
            err.brief = "intermediate {step} doesn't exist"
            err.info += lambda e: '\n'.join([
                "intermediates:", *([
                    f'{i}: {x}' 
                    for i, x in enumerate([e.synthesis_args] + e.cleanup_args)
                ]),
            ])
            raise err

        parent = self.parent
        bases = IntermediateMixin, parent.__class__

        try:
            cls = INTERMEDIATE_SUBCLASSES[bases]
        except KeyError:
            name = self.__class__.__name__ + 'Intermediate'
            cls = INTERMEDIATE_SUBCLASSES[bases] = type(name, bases, {})

        intermediate = cls()

        # Note that this is a shallow copy, so changes to any mutable 
        # attributes will be reflected in the intermediate.  That said, 
        # reagents are supposed to be fully immutable, so this should never 
        # matter in practice.

        intermediate.__dict__ = self.__dict__.copy()

        # Set new attributes after overriding `__dict__`:

        intermediate._step = step
        intermediate._parent = parent

        # Any property of the reagent (e.g. concentration, volume, etc.) could 
        # be affected by cleanup steps that come after this intermediate, so 
        # any cached property values need to be discarded.  Properties that 
        # aren't affected by cleanup steps (e.g. seq) can manually implement 
        # caching if desired.

        autoprop.clear_cache(intermediate)

        self._intermediates[step] = intermediate
        return intermediate

    def get_db(self):
        if not self._db:
            raise QueryError("not attached to a database", culprit=self)
        return self._db

    def get_tag(self):
        if not self._tag:
            raise QueryError("not attached to a database", culprit=self)
        return self._tag

    def get_parent(self):
        return self

    def get_name(self):
        return self._attrs.get('name', '')

    def get_alt_names(self):
        return self._attrs.get('alt_names', [])

    def get_date(self):
        return self._attrs.get('date')

    def get_desc(self):
        return self._attrs.get('desc', '')

    def get_dependencies(self):
        try:
            return frozenset(self.synthesis_maker.dependencies)
        except QueryError:
            return frozenset()

    def get_ready(self):
        ready = self._attrs.get('ready', True)

        if callable(ready):
            ready = ready()

        return ready

    def get_maker_attr(self, attr, default=NO_DEFAULT):
        try:
            makers = [self.synthesis_maker, *self.cleanup_makers]
        except QueryError:
            pass
        else:
            for maker in reversed(makers):
                try:
                    return getattr(maker, attr)
                except AttributeError:
                    continue

        if default is not NO_DEFAULT:
            return default
        else:
            raise QueryError(attr)

    def get_synthesis_attr(self, attr, default=NO_DEFAULT):
        try:
            maker = self.synthesis_maker
        except QueryError:
            pass
        else:
            try:
                return getattr(maker, attr)
            except AttributeError:
                pass

        if default is not NO_DEFAULT:
            return default
        else:
            raise QueryError(attr)

    def get_synthesis_maker(self):
        return self.make_intermediate(0).maker

    def get_synthesis_args(self):
        try:
            synthesis = self._attrs['synthesis']
        except KeyError:
            raise QueryError("no synthesis specified", culprit=self) from None

        # Allow `self._synthesis` to be a callable, so that the synthesis 
        # arguments don't have to be loaded until they are actually needed.  
        # This lets the database load faster, and avoids generating errors 
        # relating to synthesis steps that the user doesn't actively care 
        # about.
        if callable(synthesis):
            return synthesis()

        return synthesis

    def get_cleanup_makers(self):
        return [
                self.make_intermediate(i + 1).maker
                for i in range(len(self.cleanup_args))
        ]

    def get_cleanup_args(self):
        # Require that 
        try:
            self._attrs['synthesis']
        except KeyError:
            raise QueryError("no synthesis specified", culprit=self) from None

        cleanups = self._attrs.get('cleanups', [])

        # Allow `self._cleanups` to be a callable, so that the cleanup 
        # arguments don't have to be loaded until they are actually needed.  
        # See `get_synthesis()` for more info.

        if callable(cleanups):
            return cleanups()

        return cleanups

@autoprop.immutable
class Buffer(Reagent):
    tag_prefix = 'b'


@autoprop.immutable
class Molecule(Reagent):
    default_molecule = None

    def __init__(self, **attrs):
        super().__init__(**attrs)
        self._seq = None

    def check(self):
        self._check_seq()

    def get_seq(self):
        # Explicitly cache this property, rather than relying on the caching 
        # provided by autoprop.  We go out of our way to do this because (i) 
        # the sequence is especially expensive to look up and (ii) we know that 
        # it won't be affected by the cleanup steps.

        if self._seq:
            return self._seq

        seq = self._attrs.get('seq')

        # Allow the retrieval of the sequence to be deferred, e.g. so unused 
        # sequences never have to be read from disc.
        if callable(seq):
            seq = seq()

        # If we have instructions for how to make this molecule, try getting
        # the sequence from that.
        if not seq:
            seq = only(
                    self.get_synthesis_attr('product_seqs', []),
                    too_long=QueryError("protocol has multiple sequences", culprit=self),
            )

        if not seq:
            raise QueryError("no sequence specified", culprit=self)

        self._seq = seq
        return seq

    def get_length(self):
        try:
            return self._attrs.get('length') or len(self.seq)
        except QueryError:
            raise QueryError("no length specified", culprit=self)

    def get_mw(self):
        mw = self._attrs.get('mw')

        if not mw:
            mw = self._calc_mw()

        return mw

    def get_conc(self, unit=None):
        conc = self._attrs.get('conc')

        if conc is None:
            conc = self.get_maker_attr('product_conc', None)

        if conc is None:
            raise QueryError("no concentration specified", culprit=self)

        # Allow parsing to be deferred until the concentration is accessed, so 
        # errors don't prevent the rest of the database from loading.
        if callable(conc):
            conc = conc()

        if not unit or unit == conc.unit:
            return conc
        else:
            try:
                mw = self.mw
            except QueryError:
                mw = None

            return convert_conc_unit(conc, mw, unit)

    def get_conc_nM(self):
        return self.get_conc('nM').value

    def get_conc_uM(self):
        return self.get_conc('uM').value

    def get_conc_ng_uL(self):
        return self.get_conc('ng/uL').value

    def get_conc_mg_mL(self):
        return self.get_conc('mg/mL').value

    def get_volume(self):
        volume = self._attrs.get('volume')

        if volume is None:
            volume = self.get_maker_attr('product_volume', None)

        if volume is None:
            raise QueryError("no volume specified", culprit=self)

        # Allow parsing to be deferred until the volume is accessed, so errors 
        # don't prevent the rest of the database from loading.
        if callable(volume):
            volume = volume()

        return volume

    def get_volume_uL(self):
        return self.volume.convert_unit('µL', VOLUME_CONVERSION_FACTORS).value

    def _check_seq(self):
        from Bio import pairwise2
        from Bio.pairwise2 import format_alignment

        try:
            primary_seq = self.seq
            protocol_seq = one(self.get_synthesis_attr('product_seqs'))
        except (QueryError, ValueError):
            pass
        else:
            if primary_seq != protocol_seq:
                alignments = pairwise2.align.globalxx(primary_seq, protocol_seq)
                err = CheckError(culprit=self, alignments=alignments)
                err.brief = "sequence doesn't match construction"
                err.info = lambda e: format_alignment(e.alignments[0])
                raise err

    def _calc_mw(self):
        raise NotImplementedError


@autoprop.immutable
class Protein(Molecule):
    tag_prefix = 'r'

    def get_isoelectric_point(self):
        from Bio.SeqUtils.ProtParam import ProteinAnalysis
        analysis = ProteinAnalysis(self.seq)
        return analysis.isoelectric_point()

    @only_raise(QueryError)
    def _calc_mw(self):
        from Bio.SeqUtils import molecular_weight
        return molecular_weight(
                seq=self.seq,
                seq_type='protein',
        )


@autoprop.immutable
class NucleicAcid(Molecule):
    # "f" for "fragment", i.e. non-plasmid/non-oligo DNA constructs.
    tag_prefix = 'f'
    default_molecule = 'DNA'
    default_strandedness = None

    def __init__(self, **attrs):
        super().__init__(**attrs)
        self._molecule = None
        self._strandedness = None

    def get_molecule(self):
        self._cache_stranded_molecule()
        assert self._molecule
        return self._molecule

    @property
    def is_double_stranded(self):
        self._cache_stranded_molecule()
        assert self._strandedness
        return self._strandedness == 2

    @property
    def is_single_stranded(self):
        return not self.is_double_stranded

    @property
    def is_circular(self):
        circular = self._attrs.get('circular')

        if circular is None:
            circular = self.get_synthesis_attr('is_product_circular', False)

        if circular is None:
            circular = False

        if callable(circular):
            circular = circular()

        return circular

    @property
    def is_linear(self):
        return not self.is_circular

    @property
    def is_phosphorylated_5(self):
        # This attribute is only used when calculating molecular weight.  In 
        # the future, I want to support IDT-style sequence strings, so I could 
        # figure this out by looking for "/5Phos/" or "/3Phos/".  In the 
        # meantime, I'll just assume nothing is phosphorylated.
        return self.get_synthesis_attr('is_product_phosphorylated_5', False)

    @property
    def is_phosphorylated_3(self):
        return self.get_synthesis_attr('is_product_phosphorylated_3', False)

    def _cache_stranded_molecule(self):
        if not self._molecule or not self._strandedness:
            self._parse_stranded_molecule()

    def _parse_stranded_molecule(self):
        molecule = self._attrs.get('molecule')

        if not molecule:
            molecule = self.get_synthesis_attr('product_molecule', None)

        if not molecule:
            molecule = self.default_molecule

        if not molecule:
            raise QueryError("no molecule specified")

        with QueryError.add_info(culprit=self):
            self._molecule, self._strandedness = parse_stranded_molecule(
                    molecule, self.default_strandedness)

    @only_raise(QueryError)
    def _calc_mw(self):
        from Bio.SeqUtils import molecular_weight

        try:
            mw = molecular_weight(
                    seq=self.seq,
                    seq_type=self.molecule,
                    double_stranded=self.is_double_stranded,
                    circular=self.is_circular,
            )
            # For some reason Biopython just assumes 5' phosphorylation, so we 
            # need to correct for that here.
            if not self.is_phosphorylated_5:
                num_strands = 2 if self.is_double_stranded else 1
                num_ends = 0 if self.is_circular else num_strands
                hpo3 = 1.008 + 30.974 + 3*15.999
                mw -= hpo3 * num_ends

            return mw

        except QueryError:
            pass

        try:
            self._cache_stranded_molecule()
            molecule = self._molecule, self._strandedness
            return mw_from_length(self.length, molecule)

        except QueryError:
            pass

        raise QueryError("need sequence or length to calculate molecular weight")


@autoprop.immutable
class Plasmid(NucleicAcid):
    tag_prefix = 'p'

    def get_molecule(self):
        return 'DNA'

    @property
    def is_double_stranded(self):
        return True

    @property
    def is_circular(self):
        return True

@autoprop.immutable
class Oligo(NucleicAcid):
    tag_prefix = 'o'
    default_strandedness = 1

    def get_melting_temp(self):
        from Bio.SeqUtils import MeltingTemp

        # If the Tm is encoded in the oligo name, use that.
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



class MakerInterface:
    # Maker classes are not required to actually inherit from this class, but 
    # they are expected to implement this interface.

    # Note that I don't use autoprop on this class, because I don't want 
    # getters to be part of the interface.  Subclasses are free to use 
    # autoprop, though.

    @classmethod
    def make(self, db, products):
        raise NotImplementedError

    @property
    def protocol(self):
        raise AttributeError

    @property
    def protocol_duration(self):
        raise AttributeError

    @property
    def dependencies(self):
        raise AttributeError

    @property
    def products(self):
        # Required by make for "Label the product..." step.
        raise AttributeError

    @property
    def product_tags(self):
        raise AttributeError

    @property
    def product_seqs(self):
        raise AttributeError

    @property
    def product_molecule(self):
        raise AttributeError

    @property
    def product_conc(self):
        """
        Return a `Quantity` with one of the following units:
        - "nM"
        - "uM"
        - "µM"
        - "ng/uL"
        - "ng/µL"
        """
        raise AttributeError

    @property
    def product_volume(self):
        """
        Return a `Quantity` with units of "uL" or "µL".
        """
        raise AttributeError

    @property
    def is_product_circular(self):
        raise AttributeError

    @property
    def is_product_phosphorylated_5(self):
        raise AttributeError

    @property
    def is_product_phosphorylated_3(self):
        raise AttributeError

    @property
    def label_products(self):
        raise AttributeError


@autoprop.immutable
class IntermediateMixin:
    # Mixin class; must appear before Reagent in MRO, e.g.:
    #
    # class IntermediatePlasmid(IntermediateMixin, Plasmid):
    #     pass

    def get_step(self):
        # `self._step` is set by `Reagent.make_intermediate()`.
        return self._step

    def get_parent(self):
        return self._parent

    def get_precursor(self):
        if self.step == 0:
            raise QueryError(f"can't get precursor of first intermediate", culprit=self)

        return self.make_intermediate(self.step - 1)

    def get_maker(self):
        try:
            key = self.maker_args[0]
        except IndexError:
            raise QueryError("no protocol specified", culprit=self)

        factory = load_maker_factory(key)
        makers = list(factory(self.db, [self]))
        return one(makers)

    def get_maker_args(self):
        if self.step == 0:
            return self.synthesis_args
        else:
            return self.cleanup_args[-1]

    def get_cleanup_args(self):
        return super().cleanup_args[:self.step]

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

    try:
        plugin = DB_PLUGINS[type_use].load()
    except KeyError as err:
        raise LoadError(f"no {err} database plugin found") from None

    if defaults := getattr(plugin, 'default_config'):
        config_use = (Config(defaults) + config_use).data

    if hasattr(plugin, 'schema'):
        schema = Schema(plugin.schema)
        config_use = schema(config_use)

    return plugin.load(config_use)

def load_maker_factory(key):
    try:
        plugin = MAKER_PLUGINS[key].load()
    except KeyError as err:
        raise QueryError(f"no {err.args[0]!r} maker plugins found")

    return plugin.make

