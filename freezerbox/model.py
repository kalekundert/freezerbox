#!/usr/bin/env python3

import autoprop
import entrypoints
from more_itertools import one, only
from dataclasses import dataclass
from collections import namedtuple
from voluptuous import Schema
from inform import plural
from more_itertools import flatten
from stringcase import snakecase, sentencecase
from mergedeep import merge
from Bio.SeqUtils import MeltingTemp, molecular_weight
from .config import Config, load_config
from .errors import LoadError, QueryError, CheckError
from .utils import *

DB_PLUGINS = entrypoints.get_group_named('freezerbox.databases')
MAKER_PLUGINS = entrypoints.get_group_named('freezerbox.make')
REAGENT_CLASSES = {}
INTERMEDIATE_SUBCLASSES = {}

class Database:

    def __init__(self, config):
        if isinstance(config, dict):
            config = Config(config)

        self.name = config.get('use')
        self.config = config
        self._reagents = {}

    def __iter__(self):
        yield from self._reagents

    def __len__(self):
        return len(self._reagents)

    def __getitem__(self, tag):
        try:
            return self._reagents[tag]
        except KeyError:
            raise QueryError(f"not found in database", culprit=tag) from None

    def __setitem__(self, tag, reagent):
        check_tag(self, tag)

        if tag in self._reagents:
            raise LoadError("already in database, cannot be replaced", culprit=tag)

        self._reagents[tag] = reagent
        reagent._db = self
        reagent._tag = tag

    def __delitem__(self, tag):
        reagent = self._reagents.pop(tag)
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


@autoprop.immutable
class Reagent:
    config_name = 'reagent'
    pretty_name = 'reagent'

    def __init__(self, **kwargs):
        # `self._db` and `self._tag` are set by `Database.__setitem__()`.
        self._db = None
        self._tag = None
        self._attrs = kwargs
        self._intermediates = {}

    def __init_subclass__(cls):
        super().__init_subclass__()

        if 'config_name' not in cls.__dict__:
            cls.config_name = snakecase(cls.__name__)
        if 'pretty_name' not in cls.__dict__:
            cls.pretty_name = sentencecase(cls.__name__).lower()

        # It is possible for one reagent class to overwrite another.  This 
        # might be useful, e.g. if a user wants to replace a standard reagent 
        # class with a personal variant.
        REAGENT_CLASSES[cls.config_name] = cls

    def __repr__(self):
        attrs = list(self._attrs.items())
        if isinstance(self, IntermediateMixin):
            attrs.insert(0, ('step', self.step))

        attr_strs = [f'{k}={v!r}' for k, v in attrs]
        if self._tag:
            attr_strs.insert(0, repr(self._tag))

        return f'{self.__class__.__qualname__}({", ".join(attr_strs)})'

    def __eq__(self, other):
        return self.db is other.db and self.tag == other.tag

    def __hash__(self):
        return hash((id(self.db), self.tag))

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
class Strain(Reagent):

    def get_parent_strain(self):
        # Right now this is just a string.  But maybe it should be an object...
        return self._attrs.get('parent_strain')

    def get_plasmids(self):
        plasmids = self._attrs.get('plasmids', [])

        if callable(plasmids):
            plasmids = plasmids()

        return plasmids

    def get_antibiotics(self):
        antibiotics = self._attrs.get('antibiotics', [])

        if callable(antibiotics):
            antibiotics = antibiotics()

        if not antibiotics:
            antibiotics = list(flatten(
                x.antibiotics
                for x in self.plasmids
            ))

        return antibiotics


@autoprop.immutable
class Buffer(Reagent):
    pass


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
            seq = self.get_synthesis_attr('product_seq', None)

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
            protocol_seq = self.get_synthesis_attr('product_seq')
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

    def get_isoelectric_point(self):
        from Bio.SeqUtils.ProtParam import ProteinAnalysis
        analysis = ProteinAnalysis(self.seq)
        return analysis.isoelectric_point()

    def _calc_mw(self):
        from Bio.SeqUtils import molecular_weight
        seq = self.seq
        try:
            return molecular_weight(seq, seq_type='protein')
        except ValueError as err:
            raise QueryError(str(err)) from err


@autoprop.immutable
class NucleicAcid(Molecule):
    # "f" for "fragment", i.e. non-plasmid/non-oligo DNA constructs.
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

        except ValueError as err:
            raise QueryError(str(err)) from err

        try:
            self._cache_stranded_molecule()
            molecule = self._molecule, self._strandedness
            return mw_from_length(self.length, molecule)

        except QueryError as err:
            pass

        raise QueryError("need sequence or length to calculate molecular weight")


@autoprop.immutable
class Plasmid(NucleicAcid):

    def get_molecule(self):
        return 'DNA'

    def get_origin(self):
        """
        Return the origin of replication for this plasmid.

        The return value is the name of the origin as a string, e.g. ``"pUC"``.  
        The origin can either be manually specified via the constructor, or 
        inferred by comparing the list of features in the config file to the 
        sequence of the plasmid.
        """
        try:
            return self._attrs['origin']
        except KeyError:
            pass

        return one(
                self._find_features('ori'),
                too_short=QueryError("no origin of replication found", culprit=self),
                too_long=QueryError("multiple origins of replication found", culprit=self),
        )

    def get_resistance(self):
        """
        Return the resistance genes encoded by this plasmid.

        The return value is a list of strings, where the strings are the names 
        of the resistance genes, e.g. ``["AmpR"]``.  No distinction is 
        currently made between bacterial and mammalian resistance genes.  Most 
        plasmids only have one resistance gene, but the API always returns a 
        list because it's possible (and not unheard of) for a plasmid to have 
        multiple resistance genes.

        The resistance genes can either be manually specified by passing a 
        *resistance* argument to the constructor, or inferred by comparing the 
        list of features in the config file to the sequence of the plasmid.
        """
        resistance = self._attrs.get('resistance')

        if not resistance:
            resistance = self._find_features('resistance')

        if not resistance:
            raise QueryError("no resistance genes found", culprit=self)

        return resistance

    def get_antibiotics(self):

        def strip_r(x):
            return x[:-1] if x.endswith('R') else x

        antibiotics = self._attrs.get('antibiotics')

        if callable(antibiotics):
            antibiotics = antibiotics()

        if not antibiotics:
            try:
                antibiotics = [strip_r(x) for x in self.resistance]
            except QueryError:
                pass

        if not antibiotics:
            raise QueryError("no antibiotics specified", culprit=self)

        return antibiotics

    @property
    def is_double_stranded(self):
        return True

    @property
    def is_circular(self):
        return True

    def _find_features(self, role=None):
        hits = []

        try:
            plasmid_seq = self.seq
        except QueryError:
            return []

        features = self.db.config.get('features', [])

        for feat in features:
            try:
                feat_name = feat['name']
                feat_seq = feat['seq']
                feat_role = feat['role']
            except KeyError as err1:
                err2 = QueryError(db=self.db, feature=feat, key=err1.args[0])
                err2.brief = "found feature without required key: {key!r}"
                err2.info += "relevant config: {db.config.paths[features]}"
                err2.info += "feature: {feature}"
                raise err2 from None

            if role and feat_role != role:
                continue

            # This will fail if the resistance gene spans the ends of the 
            # plasmid sequence string.  But I'll wait to worry about that until 
            # I write a more comprehensive sequence manipulation module.

            identity = calc_sequence_identity_with_rc(feat_seq, plasmid_seq)
            if identity > feat.get('identity_threshold', 0.95):
                hits.append(feat_name)

        return hits

@autoprop.immutable
class Oligo(NucleicAcid):
    default_strandedness = 1

    def get_melting_temp_C(self):
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
        return self.melting_temp_C



class MakerPlugin:
    # This class only exists for documentation purposes: it just shows what 
    # methods a maker plugin is expected to implement.  There's no need (or 
    # reason) for plugins to actually inherit from this class.  There's not 
    # even any need for plugins to be classes; they could just as well be 
    # modules containing the functions described below.

    @staticmethod
    def maker_from_reagent(db, reagent):
        """
        Return an object (hereafter referred to as a "maker") that describes 
        how to synthesize/cleanup a single reagent.

        The returned maker object will serve two roles.  The first is to 
        provide information about the state of the reagent after the 
        synthesis/cleanup in question, e.g. concentration, volume, sequence, 
        etc.  Not all of this information is applicable to all reagents, and 
        it's all provided on an optional basis.

        The second role of the maker is to be an input to the plugin's 
        `protocols_from_makers()` function.  In this role, the maker is treated 
        as a black box.  It should contain whatever information is necessary to 
        create a protocol, but none of that information needs to be accessible 
        to FreezerBox.
        """
        raise NotImplementedError

    @staticmethod
    def protocols_from_makers(makers):
        """
        Create one or more protocols describing how to synthesize/cleanup the 
        given makers.

        Arguments:
            makers:
                A list of "maker" objects representing specific reagents to 
                synthesize/cleanup.  Each of these object will have been 
                initially created by the `maker_from_reagent()` function, and 
                can be of any type.

                Freezerbox guarantees that all of the makers passed to this 
                function will be of the same type and will not need to be 
                synthesized/cleaned up in any particular order (i.e. they can 
                be synthesized/cleaned up simultaneously).  

        Yields:
            Tuples of the form (makers, protocol) where *makers* is a subset of 
            the makers passed into this function and *protocol* is a 
            `stepwise.Protocol` object detailing the synthesis/cleanup of those 
            makers.  Ideally, the makers will be condensed into the smallest 
            number of protocols possible, e.g. by setting up master mixes, etc.
            protocol.  This function is typically implemented as a generator, 
            but it is also ok to return an iterable.
        """
        raise NotImplementedError

class MakerInterface:
    # This class only exists for documentation purposes: it just shows which 
    # methods makers (e.g. as returned by `MakerPluging.maker_from_reagent()`) 
    # can implement to tell FreezerBox about the reagent in question.  All of 
    # these methods are optional.

    # Note that I don't use autoprop on this class, because I don't want 
    # getters to be part of the interface.  Subclasses are free to use 
    # autoprop, though.

    @property
    def dependencies(self):
        """
        Return a iterable containing all the tags that this maker depends on.
        
        Most implementations return a set, since that is the most appropriate 
        data structure semantically, but any iterable is acceptable.  For 
        instance, in some cases it might be more convenient to write this 
        method as a generator (e.g. to yield dependencies).  Any duplicates in 
        the iterable will be ignored.
        """
        raise AttributeError

    @property
    def product_seq(self):
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
    """
    Represent an intermediate step in the process of synthesizing/cleaning up a 
    reagent.

    The main feature that intermediate reagents enable is the ability of 
    cleanup steps to make use of concentrations/volumes set by previous steps.  
    For example, if the user specifies a PCR reaction followed by a spin-column 
    purification, the spin-column protocol could scale itself based on the 
    volume of the PCR reaction, or print a warning if the quantity of material 
    produced by the PCR reaction exceeds the capacity of the column.

    This class is very tightly related to the `Reagent` class:

    - This class is not meant to be instantiated on its own; it's meant to be 
      used to make subclasses that also inherit from a `Reagent` class.  When 
      making these subclasses, it's important to note that `IntermediateMixin` 
      must appear before the `Reagent` class in the MRO, e.g.::

          class IntermediatePlasmid(IntermediateMixin, Plasmid):
              pass
          
    - In principle, there should be an "intermediate" version of each `Reagent` 
      class.  Defining these intermediate classes manually would basically just 
      be boilerplate though, so instead `Reagent.make_intermediate()` 
      automatically creates these classes as they are needed.

    - After instantiating an intermediate reagent object, its private `_step` 
      and `_parent` attributes must be set manually.  No public constructor or 
      method is provided to do this.  `Reagent.make_intermediate()` sets these 
      attributes, meaning that `Reagent` knows about the private details of 
      this mixin class.
    """

    def get_step(self):
        # `self._step` is set by `Reagent.make_intermediate()`.
        return self._step

    def get_parent(self):
        # `self._parent` is set by `Reagent.make_intermediate()`.
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

        plugin = load_maker_plugin(key)
        return plugin.maker_from_reagent(self.db, self)

    def get_maker_args(self):
        if self.step == 0:
            return self.synthesis_args
        else:
            return self.cleanup_args[-1]

    def get_cleanup_args(self):
        return super().cleanup_args[:self.step]

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
        loader_configs = config['database'][use]
    except KeyError as err:
        raise LoadError(f"unknown database {use!r}") from None

    db = Database(config)

    for loader_config in loader_configs:
        try:
            loader_key = loader_config['format']
        except KeyError as err:
            raise LoadError(f"no 'format' specified for database {use!r}") from None

        try:
            loader_plugin = DB_PLUGINS[loader_key].load()
        except KeyError as err:
            raise LoadError(f"no {loader_key!r} database plugin found") from None

        if defaults := getattr(loader_plugin, 'default_config'):
            loader_config = merge({}, defaults, loader_config)

        if hasattr(loader_plugin, 'schema'):
            loader_config = loader_plugin.schema(loader_config)

        loader_plugin.load(db, loader_config)

    return db

def load_maker_plugin(key):
    try:
        return MAKER_PLUGINS[key].load()
    except KeyError as err:
        raise QueryError(f"no {err.args[0]!r} maker plugins found")

def find(db, tags, reagent_cls=None):
    if isinstance(tags, str):
        hits = find(db, [tags], reagent_cls=reagent_cls)
        return hits[0]

    hits = [db[x] for x in tags]

    if reagent_cls:
        for hit in hits:
            if not isinstance(hit, reagent_cls):
                err = QueryError(
                        culprit=hit.tag,
                        hit=hit,
                        reagent_cls=reagent_cls,
                )
                err.brief = "wrong reagent type"
                err.blame += "expected {reagent_cls.pretty_name!r}, found {hit.__class__.pretty_name!r}"
                raise err

    return hits

