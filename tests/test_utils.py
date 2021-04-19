#!/usr/bin/env python3

import pytest
import parametrize_from_file

from freezerbox import Tag
from freezerbox.model import *
from freezerbox.utils import *
from stepwise import Quantity
from schema_helpers import *

class PrefixParams(Params):
    args = 'args, expected'
    params = [
            # 'x' is from the various mock reagents.
            ([],                                    'xbrfpo'),
            ([Reagent],                             'xbrfpo'),
            ([Buffer],                              'b'),
            ([Protein],                             'r'),
            ([Protein, NucleicAcid],                'xrfpo'),
            ([NucleicAcid],                         'xfpo'),
            ([NucleicAcid, Plasmid],                'xfpo'),
            ([NucleicAcid, Oligo],                  'xfpo'),
            ([NucleicAcid, Plasmid, Oligo],         'xfpo'),
            ([Plasmid],                             'p'),
            ([Oligo],                               'o'),
            ([Plasmid, Oligo],                      'po'),
    ]

@parametrize_from_file
def test_normalize_seq(raw_seq, expected):
    assert normalize_seq(raw_seq) == expected

@PrefixParams.parametrize
def test_get_tag_prefixes(args, expected):
    assert get_tag_prefixes(*args) == set(expected)

@PrefixParams.parametrize
def test_get_tag_pattern(args, expected):
    assert re.fullmatch(
            fr'\[[{expected}]+\]\\d\+',
            get_tag_pattern(*args),
    )

@parametrize_from_file(
        schema=Schema({
            'tag_str': str,
            **error_or(**{
                'expected': {
                    'type': str,
                    'id': Coerce(int),
                },
            }),
        }),
)
def test_parse_tag(tag_str, expected, error):
    with error:
        assert parse_tag(tag_str) == Tag(**expected)

@parametrize_from_file(
        schema=Schema({
            'bool_str': str,
            **error_or(**{
                'expected': eval,
            }),
        }),
)
def test_parse_bool(bool_str, expected, error):
    with error:
        assert parse_bool(bool_str) == expected

@parametrize_from_file(
        schema=Schema({
            'time_str': str,
            **error_or(**{
                'expected': Coerce(float),
            }),
        }),
)
def test_parse_time_s(time_str, expected, error):
    with error:
        assert parse_time_s(time_str) == pytest.approx(expected)

@parametrize_from_file(
        schema=Schema({
            'temp_str': str,
            **error_or(**{
                'expected': Coerce(float),
            }),
        }),
)
def test_parse_temp_C(temp_str, expected, error):
    with error:
        assert parse_temp_C(temp_str) == pytest.approx(expected)

@parametrize_from_file(
        schema=Schema({
            'vol_str': str,
            **error_or(**{
                'expected': Coerce(float),
            }),
        }),
)
def test_parse_volume_uL(vol_str, expected, error):
    with error:
        assert parse_volume_uL(vol_str) == expected

@parametrize_from_file(
        schema=Schema({
            'conc_str': str,
            'mw': Coerce(float),
            'expected_nM': Coerce(float),
            'expected_ng_uL': Coerce(float),
        }),
)
def test_parse_conc(conc_str, mw, expected_nM, expected_ng_uL):
    from itertools import combinations

    conc = {
            'nM': parse_conc_nM(conc_str, mw),
            'uM': parse_conc_uM(conc_str, mw),
            'ng/uL': parse_conc_ng_uL(conc_str, mw),
    }
    expected = {
            'nM': expected_nM,
            'uM': expected_nM / 1000,
            'ng/uL': expected_ng_uL,
    }

    for k in conc:
        assert conc[k] == pytest.approx(expected[k])

    for k1, k2 in combinations(conc, 2):
        q_given = Quantity(conc[k1], k1)
        q_expected = Quantity(expected[k2], k2)
        q_converted = convert_conc_unit(q_given, mw, k2)

        assert q_converted.value == pytest.approx(q_expected.value)
        assert q_converted.unit == q_expected.unit

@parametrize_from_file(
        schema=Schema({
            'conc_str': str,
            'mw': Coerce(float),
            'error': error,
        }),
)
def test_parse_conc_err(conc_str, mw, error):
    with error:
        parse_conc_nM(conc_str, mw)
    with error:
        parse_conc_uM(conc_str, mw)
    with error:
        parse_conc_ng_uL(conc_str, mw)

@parametrize_from_file(
        schema=Schema({
            'size_str': str,
            **error_or(**{
                'expected': Coerce(int),
            }),
        }),
)
def test_parse_size_bp(size_str, expected, error):
    with error:
        assert parse_size_bp(size_str) == expected
