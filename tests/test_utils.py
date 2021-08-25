#!/usr/bin/env python3

import pytest
import parametrize_from_file

from freezerbox import Tag
from freezerbox.model import *
from freezerbox.utils import *
from stepwise import Quantity
from schema_helpers import *
from pytest import approx

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

parse_schema = lambda input_name, schema={}: Schema({
    input_name: str,
    Optional('kwargs', default={}): eval_freezerbox,
    **error_or({
        'parsed': eval_freezerbox,
        'converted': {str: eval},
    }),
    **schema,
})

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
            **error_or({
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
            **error_or({
                'expected': eval,
            }),
        }),
)
def test_parse_bool(bool_str, expected, error):
    with error:
        assert parse_bool(bool_str) == expected

@parametrize_from_file(schema=parse_schema('time_str'))
def test_parse_time(time_str, kwargs, parsed, converted, error):
    with error:
        assert parse_time(time_str, **kwargs) == parsed
    with error:
        assert parse_time_s(time_str, **kwargs) == approx(converted['s'])
    with error:
        assert parse_time_m(time_str, **kwargs) == approx(converted['m'])
    with error:
        assert parse_time_h(time_str, **kwargs) == approx(converted['h'])

@parametrize_from_file(
        schema=Schema({
            'given': eval,
            'expected': str,
        })
)
def test_format_time_s(given, expected):
    assert format_time_s(given) == expected

@parametrize_from_file(
        schema=Schema({
            'given': eval,
            'expected': str,
        })
)
def test_format_time_m(given, expected):
    assert format_time_m(given) == expected

@parametrize_from_file(schema=parse_schema('temp_str'))
def test_parse_temp(temp_str, kwargs, parsed, converted, error):
    with error:
        assert parse_temp(temp_str, **kwargs) == parsed
    with error:
        assert parse_temp_C(temp_str, **kwargs) == approx(converted['C'])

@parametrize_from_file(schema=parse_schema('vol_str'))
def test_parse_volume(vol_str, kwargs, parsed, converted, error):
    with error:
        assert parse_volume(vol_str, **kwargs) == parsed
    with error:
        assert parse_volume_uL(vol_str, **kwargs) == approx(converted['uL'])
    with error:
        assert parse_volume_mL(vol_str, **kwargs) == approx(converted['mL'])

@parametrize_from_file(schema=parse_schema('mass_str'))
def test_parse_mass(mass_str, kwargs, parsed, converted, error):
    with error:
        assert parse_mass(mass_str, **kwargs) == parsed
    with error:
        assert parse_mass_ug(mass_str, **kwargs) == approx(converted['ug'])
    with error:
        assert parse_mass_mg(mass_str, **kwargs) == approx(converted['mg'])

@parametrize_from_file(schema=parse_schema('conc_str', {'mw': eval}))
def test_parse_conc(conc_str, mw, kwargs, parsed, converted, error):
    from itertools import combinations_with_replacement

    converted['uM'] = converted['nM'] / 1000
    converted['ug/uL'] = converted['ng/uL'] / 1000

    with error:
        assert parse_conc(conc_str, **kwargs) == parsed

    with error:
        assert parse_conc_nM(conc_str, mw, **kwargs) == converted['nM']
    with error:
        assert parse_conc_uM(conc_str, mw, **kwargs) == converted['uM']
    with error:
        assert parse_conc_ng_uL(conc_str, mw, **kwargs) == converted['ng/uL']
    with error:
        assert parse_conc_ug_uL(conc_str, mw, **kwargs) == converted['ug/uL']

    for unit, value in converted.items():
        q_given = parsed
        mw_given = mw if unit != q_given.unit else None
        q_expected = Quantity(value, unit)
        q_converted = convert_conc_unit(q_given, mw_given, unit)
        assert q_converted == pytest.approx(
                q_expected,
                abs=Quantity(1e-6, unit),
        )

@parametrize_from_file(schema=parse_schema('size_str'))
def test_parse_size(size_str, kwargs, parsed, converted, error):
    with error:
        assert parse_size(size_str, **kwargs) == parsed
    with error:
        assert parse_size_bp(size_str, **kwargs) == converted['bp']
    with error:
        assert parse_size_kb(size_str, **kwargs) == converted['kb']

@parametrize_from_file(
        schema=Schema({
            'molecule': eval,
            Optional('default_strandedness', default='None'): eval,
            **error_or({
                'expected': eval,
            }),
        })
)
def test_parse_stranded_molecule(molecule, default_strandedness, expected, error):
    with error:
        actual = parse_stranded_molecule(molecule, default_strandedness)
        assert actual == expected

@parametrize_from_file(
        schema=Schema({
            'len': Coerce(int),
            'molecule': eval,
            'expected': Coerce(float),
        }),
)
def test_mw_from_length(len, molecule, expected):
    assert mw_from_length(len, molecule) == approx(expected)

@parametrize_from_file(
        schema=Schema({
            'items': eval,
            Optional('kwargs', default={}): {str: eval},
            **error_or({
                'expected': eval,
            }),
        }),
)
def test_unanimous(items, kwargs, expected, error):
    with error:
        assert unanimous(items, **kwargs) == expected

@parametrize_from_file(schema=Schema({str: eval}))
def test_join_lists(given, expected):
    assert join_lists(given) == expected

@parametrize_from_file(schema=Schema({str: eval}))
def test_join_dicts(given, expected):
    assert join_dicts(given) == expected

@parametrize_from_file(schema=Schema({str: eval}))
def test_join_sets(given, expected):
    assert join_sets(given) == expected

