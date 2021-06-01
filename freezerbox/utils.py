#!/usr/bin/env python3

import re, os
from stepwise import Quantity
from more_itertools import split_when
from contextlib import contextmanager
from .errors import ParseError, only_raise

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
    from .model import Reagent

    def add(prefixes, cls):
        if cls.tag_prefix:
            prefixes.add(cls.tag_prefix)
        for subcls in cls.__subclasses__():
            add(prefixes, subcls)

    prefixes = set()
    for cls in args or [Reagent]:
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
def parse_time_m(time_str):
    return parse_time_s(time_str) / 60

@only_raise(ParseError)
def parse_time_h(time_str):
    return parse_time_s(time_str) / 3600

@only_raise(ParseError)
def parse_temp_C(temp_str):
    temp_pattern = fr'(?P<temp>[0-9.]+)\s*°?C'

    if m := re.fullmatch(temp_pattern, temp_str):
        return float(m.group('temp'))

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
def parse_mass_ug(mass_str):
    mass_pattern = fr'(?P<mass>\d+)\s*(?P<si_prefix>[nµum])g'
    si_prefixes = {
            'n': 1e-3,
            'u': 1,
            'µ': 1,
            'm': 1e3,
    }

    if m := re.fullmatch(mass_pattern, mass_str):
        return float(m.group('mass')) * si_prefixes[m.group('si_prefix')]

    raise ParseError(f"can't interpret {mass_str!r} as a mass, did you forget a unit?")

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
def convert_conc_unit(conc, mw, new_unit):
    molar_conversion_factors = {
            'pM': 1e12,
            'nM': 1e9,
            'uM': 1e6,
            'µM': 1e6,
            'mM': 1e3,
            'M': 1,
    }
    mass_volume_conversion_factors = {
            'ng/uL': 1e3,
            'ng/µL': 1e3,
            'µg/µL': 1,
            'ug/uL': 1,
            'mg/mL': 1,
    }

    def pick_conversion_factors():
        if mw is not None:
            return {
                    **molar_conversion_factors,
                    **{
                        k: mw * v
                        for k, v in mass_volume_conversion_factors.items()
                    },
            }

        if conc.unit in molar_conversion_factors:
            return molar_conversion_factors

        if conc.unit in mass_volume_conversion_factors:
            return mass_volume_conversion_factors

        return {}

    return conc.convert_unit(new_unit, pick_conversion_factors())

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

def unanimous(items):
    it = iter(items)

    try:
        value = next(it)
    except StopIteration:
        raise ValueError("empty iterable")

    for next_value in it:
        if next_value != value:
            raise ValueError(f"found multiple values: {value!r}, {next_value!r}")

    return value

def join_lists(x):
    from itertools import chain
    return list(chain(*x))

def join_dicts(x):
    from collections import ChainMap
    return dict(ChainMap(*x))

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

