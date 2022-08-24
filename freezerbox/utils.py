#!/usr/bin/env python3

import sys, os, re
from stepwise import Quantity
from more_itertools import split_when, zip_equal, first
from contextlib import contextmanager
from inform import did_you_mean
from .errors import ParseError, only_raise

# I really hate that more-itertools makes me do this...
if sys.version_info >= (3, 10):
    def zip_equal(a, b):
        return zip(a, b, strict=True)

NO_DEFAULT = object()

TIME_CONVERSION_FACTORS = {
    's':        60*60,
    'sec':      60*60,
    'second':   60*60,
    'seconds':  60*60,
    'm':        60,
    'min':      60,
    'minute':   60,
    'minutes':  60,
    'h':        1,
    'hr':       1,
    'hour':     1,
    'hours':    1,
}
TEMP_CONVERSION_FACTORS = {
        '°C': 1,
         'C': 1,
}
VOLUME_CONVERSION_FACTORS = {
        'nL': 1e9,
        'uL': 1e6,
        'µL': 1e6,
        'mL': 1e3,
         'L': 1,
}
MASS_CONVERSION_FACTORS = {
        'pg': 1e12,
        'ng': 1e9,
        'ug': 1e6,
        'µg': 1e6,
        'mg': 1e3,
         'g': 1,
        'kg': 1e-3,
}
CONC_CONVERSION_FACTORS_MOLARITY = {
        'pM': 1e12,
        'nM': 1e9,
        'uM': 1e6,
        'µM': 1e6,
        'mM': 1e3,
         'M': 1,
}
CONC_CONVERSION_FACTORS_DENSITY = {
        'ng/uL': 1e3,
        'ng/µL': 1e3,
        'µg/mL': 1e3,
        'ug/mL': 1e3,
        'µg/µL': 1,
        'ug/uL': 1,
        'mg/mL': 1,
}
CONC_UNITS = {
        *CONC_CONVERSION_FACTORS_MOLARITY,
        *CONC_CONVERSION_FACTORS_DENSITY,
}
SIZE_CONVERSION_FACTORS = {
        'bp': 1e3,
        'kb': 1,
}

def normalize_seq(raw_seq):
    # Ignore nonstandard nucleotides; they're too hard to deal with properly.

    # This regular expression works because `re.sub()` only substitutes the 
    # left-most occurrence of any overlapping patterns.  The non-greedy * is 
    # necessary to avoid eliding everything between the first and last 
    # nonstandard nucleotide.
    seq = re.sub(r'/.*?/', 'X', raw_seq.strip())

    return seq.upper()

def reverse_complement(seq):
    from Bio.Seq import Seq
    return str(Seq(seq).reverse_complement())

def calc_sequence_identity(
        seq, ref_seq, *,
        match_score=1,
        mismatch_score=-1,
        open_gap_score=-0.5,
        extend_gap_score=-0.5,
):
    """
    Return the fraction of nucleotides in the given sequence that can be 
    perfectly aligned to the reference sequence.

    The basic algorithm is: perform a local sequence alignment, then count how 
    many positions in the input sequence are present in the alignment and 
    identical to the reference.  There are other ways to calculate percent 
    identity (e.g. different choice of denominator, different treatment of 
    gaps), but this should be reasonable.
    """
    from Bio.Align import PairwiseAligner

    if not seq:
        return 0

    seq = seq.upper()
    ref_seq = ref_seq.upper()

    aligner = PairwiseAligner()
    aligner.mode = 'local'
    aligner.match_score = match_score
    aligner.mismatch_score = mismatch_score
    aligner.open_gap_score = open_gap_score
    aligner.extend_gap_score = extend_gap_score

    results = aligner.align(seq, ref_seq)

    try:
        result = first(results)
    except ValueError:
        return 0

    aligned_chars = []

    for (i,j), (k,l) in zip(*result.aligned):
        aligned_chars += zip_equal(seq[i:j], ref_seq[k:l])

    n_identities = sum(a == b for a,b in aligned_chars)
    n_total = len(seq)

    return n_identities / n_total

def calc_sequence_identity_with_rc(seq, ref_seq, **kwargs):
    ref_seqs = [ref_seq, reverse_complement(ref_seq)]
    scores = [
            calc_sequence_identity(seq, x, **kwargs)
            for x in ref_seqs
    ]
    return max(scores)

@only_raise(ParseError)
def check_tag(db, tag):
    tag_pattern = db.config.get('tag_pattern', '.*')

    if m := re.fullmatch(tag_pattern, tag):
        return m

    err = ParseError(db=db, tag=tag, pattern=tag_pattern)
    err.brief = "tag doesn't match expected pattern"
    err.info += "relevant config: {db.config.paths[tag_pattern]}"
    err.blame += "expected {tag!r} to match {pattern!r}"
    raise err

@only_raise(ParseError)
def parse_bool(bool_str):
    if bool_str.lower() in ('1', '+', 'x', 'y', 'yes', 'true'):
        return True
    if bool_str.lower() in ('0', '-',  '', 'n', 'no', 'false'):
        return False

    raise ParseError(f"can't interpret {bool_str!r} as a bool")

@only_raise(ParseError)
def parse_time(time_str, default_unit=None):

    # First, try parsing the time using a custom syntax, e.g. '1m30':
    time_pattern = r'(\d+)([hm])(\d+)'
    if m := re.fullmatch(time_pattern, time_str):
        value = 60 * int(m.group(1)) + int(m.group(3))
        unit = {'h': 'm', 'm': 's'}[m.group(2)]
        return Quantity(value, unit)

    # If that doesn't work, try parsing the time normally, e.g. '1 min'
    return _parse_quantity(
            time_str, TIME_CONVERSION_FACTORS, default_unit, 'time')

@only_raise(ParseError)
def parse_time_s(time_str, default_unit=None):
    time = parse_time(time_str, default_unit)
    time = time.convert_unit('s', TIME_CONVERSION_FACTORS)
    return time.value

@only_raise(ParseError)
def parse_time_m(time_str, default_unit=None):
    time = parse_time(time_str, default_unit)
    time = time.convert_unit('m', TIME_CONVERSION_FACTORS)
    return time.value

@only_raise(ParseError)
def parse_time_h(time_str, default_unit=None):
    time = parse_time(time_str, default_unit)
    time = time.convert_unit('h', TIME_CONVERSION_FACTORS)
    return time.value

def format_time_s(x):
    if x < 60:
        return f'{x}s'

    min = x // 60
    sec = x % 60

    return f'{min}m{f"{sec:02}" if sec else ""}'

def format_time_m(x):
    if x < 60:
        return f'{x}m'

    hr = x // 60
    min = x % 60

    return f'{hr}h{f"{min:02}" if min else ""}'

@only_raise(ParseError)
def parse_temp(temp_str, default_unit=None):
    return _parse_quantity(
            temp_str, TEMP_CONVERSION_FACTORS, default_unit, 'temperature')

@only_raise(ParseError)
def parse_temp_C(temp_str, default_unit=None):
    return _parse_and_convert_quantity(
            temp_str, TEMP_CONVERSION_FACTORS, default_unit, '°C', 'temperature')

@only_raise(ParseError)
def parse_volume(vol_str, default_unit=None):
    return _parse_quantity(
            vol_str, VOLUME_CONVERSION_FACTORS, default_unit, 'volume')

@only_raise(ParseError)
def parse_volume_uL(vol_str, default_unit=None):
    return _parse_and_convert_quantity(
            vol_str, VOLUME_CONVERSION_FACTORS, default_unit, 'µL', 'volume')

@only_raise(ParseError)
def parse_volume_mL(vol_str, default_unit=None):
    return _parse_and_convert_quantity(
            vol_str, VOLUME_CONVERSION_FACTORS, default_unit, 'mL', 'volume')

@only_raise(ParseError)
def parse_mass(mass_str, default_unit=None):
    return _parse_quantity(
            mass_str, MASS_CONVERSION_FACTORS, default_unit, 'mass')

@only_raise(ParseError)
def parse_mass_ug(mass_str, default_unit=None):
    return _parse_and_convert_quantity(
            mass_str, MASS_CONVERSION_FACTORS, default_unit, 'µg', 'mass')

@only_raise(ParseError)
def parse_mass_mg(mass_str, default_unit=None):
    return _parse_and_convert_quantity(
            mass_str, MASS_CONVERSION_FACTORS, default_unit, 'mg', 'mass')

@only_raise(ParseError)
def parse_conc(conc_str, default_unit=None):
    return _parse_quantity(conc_str, CONC_UNITS, default_unit, 'concentration')

@only_raise(ParseError)
def parse_conc_nM(conc_str, mw=None, default_unit=None):
    conc = parse_conc(conc_str, default_unit)
    conc = convert_conc_unit(conc, mw, 'nM')
    return conc.value

@only_raise(ParseError)
def parse_conc_uM(conc_str, mw=None, default_unit=None):
    conc = parse_conc(conc_str, default_unit)
    conc = convert_conc_unit(conc, mw, 'µM')
    return conc.value

@only_raise(ParseError)
def parse_conc_ng_uL(conc_str, mw=None, default_unit=None):
    conc = parse_conc(conc_str, default_unit)
    conc = convert_conc_unit(conc, mw, 'ng/µL')
    return conc.value

@only_raise(ParseError)
def parse_conc_ug_uL(conc_str, mw=None, default_unit=None):
    conc = parse_conc(conc_str, default_unit)
    conc = convert_conc_unit(conc, mw, 'µg/µL')
    return conc.value

@only_raise(ParseError)
def convert_conc_unit(conc, mw, new_unit):
    def pick_conversion_factors():
        if mw is not None:
            return {
                    **CONC_CONVERSION_FACTORS_MOLARITY,
                    **{
                        k: mw * v
                        for k, v in CONC_CONVERSION_FACTORS_DENSITY.items()
                    },
            }

        if conc.unit in CONC_CONVERSION_FACTORS_MOLARITY:
            return CONC_CONVERSION_FACTORS_MOLARITY

        if conc.unit in CONC_CONVERSION_FACTORS_DENSITY:
            return CONC_CONVERSION_FACTORS_DENSITY

        return {}

    return conc.convert_unit(new_unit, pick_conversion_factors())

@only_raise(ParseError)
def parse_size(size_str, default_unit=None):
    return _parse_quantity(size_str, SIZE_CONVERSION_FACTORS, default_unit, 'size')

@only_raise(ParseError)
def parse_size_bp(size_str, default_unit=None):
    return _parse_and_convert_quantity(
            size_str, SIZE_CONVERSION_FACTORS, default_unit, 'bp', 'size')

@only_raise(ParseError)
def parse_size_kb(size_str, default_unit=None):
    return _parse_and_convert_quantity(
            size_str, SIZE_CONVERSION_FACTORS, default_unit, 'kb', 'size')

def parse_stranded_molecule(molecule, default_strandedness=None):
    """
    Parse the molecule type (e.g. suitable input for Biopython functions) 
    and strandedness from a molecule string.  
    """
    if isinstance(molecule, tuple):
        return molecule

    stranded_molecules = {
            'dna':   (0, 'DNA'),
            'ssdna': (1, 'DNA'),
            'dsdna': (2, 'DNA'),
            'rna':   (0, 'RNA'),
            'ssrna': (1, 'RNA'),
            'dsrna': (2, 'RNA'),
    }
    try:
        strandedness, molecule = stranded_molecules[molecule.lower()]
    except KeyError:
        err = ParseError(molecule=molecule)
        err.brief = "unknown molecule type: {molecule!r}"
        err.info += f"expected: {', '.join(map(repr, stranded_molecules))}"
        raise err

    if not strandedness:
        strandedness = default_strandedness

    if not strandedness:
        strandedness = {'DNA': 2, 'RNA': 1}[molecule]

    return molecule, strandedness

def mw_from_length(len, molecule='dna'):
    molecule, strandedness = parse_stranded_molecule(molecule)

    # Parameters from: 
    # https://www.thermofisher.com/us/en/home/references/ambion-tech-support/rna-tools-and-calculators/dna-and-rna-molecular-weights-and-conversions.html
    params = {
            'DNA': (303.7, 79),
            'RNA': (320.5, 159),
    }
    m, b = params[molecule]
    return (m * len + b) * strandedness

def unanimous(
        items,
        default=NO_DEFAULT,
        err_empty=ValueError("empty iterable"),
        err_multiple=lambda v1, v2: ValueError(f"found multiple values: {v1!r}, {v2!r}"),
    ):
    it = iter(items)

    try:
        value = next(it)
    except StopIteration:
        if default is not NO_DEFAULT:
            return default
        else:
            raise err_empty

    for next_value in it:
        if next_value != value:
            raise err_multiple(value, next_value)

    return value

def join_lists(x):
    from itertools import chain
    return list(chain(*x))

def join_dicts(x):
    # Originally I used `dict(ChainMap(*x))`, but I reimplemented it using 
    # basic for-loops to maintain insertion order.
    out = {}
    for d in x:
        for k, v in d.items():
            if k not in out:
                out[k] = v
    return out

def join_sets(x):
    return set.union(set(), *x)

@contextmanager
def cd(dir):
    try:
        prev_cwd = os.getcwd()
        os.chdir(dir)
        yield

    finally:
        os.chdir(prev_cwd)


def _parse_quantity(quantity_str, expected_units, default_unit, unit_type):
    try:
        if default_unit:
            quantity = Quantity.from_string_or_float(quantity_str, default_unit)
        else:
            quantity = Quantity.from_string(quantity_str)

    except ValueError:
        raise ParseError(
                "can't interpret {quantity_str!r} as a {unit_type}",
                quantity_str=quantity_str,
                unit_type=unit_type,
        ) from None

    if quantity.unit not in expected_units:
        raise ParseError(
                lambda e: f"can't interpret {e.quantity_str!r} as a {unit_type}, did you mean '{Quantity(e.quantity.value, did_you_mean(e.quantity.unit, e.expected_units))}'?",
                quantity=quantity,
                quantity_str=quantity_str,
                expected_units=expected_units,
                unit_type=unit_type,
        )

    return quantity

def _parse_and_convert_quantity(quantity_str, conversion_factors, default_unit, desired_unit, unit_type):
    quantity = _parse_quantity(
            quantity_str, conversion_factors, default_unit, unit_type)
    converted = quantity.convert_unit(desired_unit, conversion_factors)
    return converted.value


