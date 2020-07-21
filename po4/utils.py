#!/usr/bin/env python3

import re
from Bio.Seq import Seq
from Bio.Alphabet import generic_dna
from more_itertools import split_when
from .errors import ParseError, only_raise

DnaSeq = lambda x: Seq(normalize_seq(x), generic_dna)
no_default = object()

def normalize_seq(raw_seq):
    # Ignore nonstandard nucleotides; they're too hard to deal with properly.

    # This regular expression works because `re.sub()` only substitutes the 
    # left-most occurrence of any overlapping patterns.  The non-greedy * is 
    # necessary to avoid eliding everything between the first and last 
    # nonstandard nucleotide.
    seq = re.sub(r'/.*?/', 'X', raw_seq)

    return seq.upper()

def get_tag_prefixes(*args):
    from .model import Construct

    def add(prefixes, cls):
        if cls.tag_prefix:
            prefixes.add(cls.tag_prefix)
        for subcls in cls.__subclasses__():
            add(prefixes, subcls)

    prefixes = set()
    for cls in args or [Construct]:
        add(prefixes, cls)
    
    return prefixes

def get_tag_pattern(*args):
    prefix_chars = ''.join(sorted(get_tag_prefixes(*args)))
    return fr'[{prefix_chars}]\d+'

@only_raise(ParseError)
def parse_tag(tag_str):
    from .model import Tag, get_tag_prefixes

    if isinstance(tag_str, Tag):
        return tag_str
    if isinstance(tag_str, tuple):
        return Tag(*tag_str)

    pfo = get_tag_prefixes()
    if m := re.fullmatch(fr'\s*(?P<type>[{pfo}])(?P<id>\d+)\s*', tag_str):
        return Tag(m.group('type'), int(m.group('id')))
    else:
        raise ParseError(f"expected a tag (e.g. 'p100'), not {tag_str!r}")

@only_raise(ParseError)
def parse_params(params_str, *, sep=r'\s', on_duplicate=None, on_unmatched=None):
    params = {}
    param_pattern = fr'''\s*
            (?P<key>\w+)=(
              (?P<value>[^"'][^{sep}]*)|
              (?P<quote>["'])(?P<value_quoted>.*?)(?P=quote)
            )
            ({sep}|$)
    '''

    unmatched = set(range(len(params_str)))

    for m in re.finditer(param_pattern, params_str, re.VERBOSE):
        key = m.group('key')
        value = m.group('value') or m.group('value_quoted')

        if key in params:
            if on_duplicate:
                on_duplicate(params, key, value)
            else:
                raise ParseError(f"duplicate key {key!r} in {params_str!r}")

        params[key] = value
        unmatched -= set(range(m.start(), m.end()))

    if unmatched:
        if on_unmatched:
            on_unmatched(params_str, unmatched)
        else:
            groups = split_when(
                    sorted(unmatched), 
                    lambda a, b: b != a + 1
            )
            substrs = ', '.join(
                    repr(params_str[x[0]:x[-1]+1])
                    for x in groups
            )
            if substrs == repr(params_str):
                raise ParseError(f"can't parse {params_str!r}")
            else:
                raise ParseError(f"can't parse {params_str!r}: didn't expect {substrs}")

    return params

def parse_param(params, key, pattern, default=no_default):
    if key not in params:
        if default is not no_default:
            return default
        else:
            raise ParseError(f"missing required {key!r} parameter")

    if m := re.fullmatch(pattern, p := params[key]):
        return m.groups() or m.group()
    else:
        raise ParseError(f"expected {key}≈{pattern!r}, found {p!r}")

@only_raise(ParseError)
def parse_bool(bool_str):
    if bool_str.lower() in ('1', 'y', 'yes', 'true'):
        return True
    if bool_str.lower() in ('0', 'n', 'no', 'false'):
        return False

    raise ParseError(f"can't interpret {bool_str!r} as a bool")

@only_raise(ParseError)
def parse_time_s(time_str):
    time_units = {
            's':        1,
            'sec':      1,
            'second':   1,
            'seconds':  1,
            'm':        60,
            'min':      60,
            'minute':   60,
            'minutes':  60,
            'h':        60*60,
            'hr':       60*60,
            'hour':     60*60,
            'hours':    60*60,
    }
    time_pattern_1 = fr'(?P<time>\d+)\s*(?P<unit>{"|".join(time_units)})'
    time_pattern_2 = fr'(?P<min>\d+)m(?P<sec>\d+)'

    if m := re.fullmatch(time_pattern_1, time_str):
        return int(m.group('time')) * time_units[m.group('unit')]
    if m := re.fullmatch(time_pattern_2, time_str):
        return 60 * int(m.group('min')) + int(m.group('sec'))

    raise ParseError(f"can't interpret {time_str!r} as a time, did you forget a unit?")

@only_raise(ParseError)
def parse_temp_C(temp_str):
    temp_pattern = fr'(?P<temp>\d+)\s*°?C'

    if m := re.fullmatch(temp_pattern, temp_str):
        return int(m.group('temp'))

    raise ParseError(f"can't interpret {temp_str!r} as a temperature, did you forget a unit?")

@only_raise(ParseError)
def parse_volume_uL(vol_str):
    vol_pattern = fr'(?P<vol>\d+)\s*(?P<si_prefix>[nµum])L'
    si_prefixes = {
            'n': 1e-3,
            'u': 1,
            'µ': 1,
            'm': 1e3,
    }

    if m := re.fullmatch(vol_pattern, vol_str):
        return float(m.group('vol')) * si_prefixes[m.group('si_prefix')]

    raise ParseError(f"can't interpret {vol_str!r} as a volume, did you forget a unit?")

@only_raise(ParseError)
def parse_conc_nM(conc_str, mw):
    conc_pattern = r'(?P<conc>\d+)\s?(?P<unit>[nuµ]M|ng/[uµ]L)'
    unit_conversion = {
            'nM': 1,
            'uM': 1e3,
            'µM': 1e3,
            'ng/uL': 1e6 / mw,
            'ng/µL': 1e6 / mw,
    }

    if m := re.match(conc_pattern, conc_str):
        return float(m.group('conc')) * unit_conversion[m.group('unit')]
    else:
        raise ParseError(f"can't interpret {conc_str!r} as a concentration, did you forget a unit?")

@only_raise(ParseError)
def parse_conc_uM(conc_str, mw):
    return parse_conc_nM(conc_str, mw) / 1000

@only_raise(ParseError)
def parse_conc_ng_uL(conc_str, mw):
    conc_pattern = r'(?P<conc>\d+)\s?(?P<unit>[nuµ]M|ng/[uµ]L)'
    unit_conversion = {
            'ng/uL': 1,
            'ng/µL': 1,
            'nM': mw / 1e6,
            'uM': mw / 1e3,
            'µM': mw / 1e3,
    }

    if m := re.match(conc_pattern, conc_str):
        return float(m.group('conc')) * unit_conversion[m.group('unit')]
    else:
        raise ParseError(f"can't interpret {conc_str!r} as a concentration, did you forget a unit?")

@only_raise(ParseError)
def parse_size_bp(size_str):
    bp_parsers = [
            (
                fr'(?P<size>\d+)\s*bp',
                int,
            ), (
                fr'(?P<size>\d+.?\d*)\s*kb',
                lambda x: int(float(x) * 1000),
            ),
    ]

    for pattern, size_from_str in bp_parsers:
        if m := re.fullmatch(pattern, size_str):
            return size_from_str(m.group('size'))

    raise ParseError(f"can't interpret {size_str!r} as a size in base pairs, did you forget a unit?")

