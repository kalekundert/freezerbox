#!/usr/bin/env python3

import pytest
import parametrize_from_file

from freezerbox.model import *
from freezerbox.utils import *
from stepwise import Quantity
from param_helpers import *
from pytest import approx

parse_schema = [
        cast(
            parsed=with_freeze.eval,
            converted=with_py.eval,
            kwargs=with_py.eval,
        ),
        defaults(kwargs={}),
        with_freeze.error_or('parsed', 'converted'),
]

@parametrize_from_file
def test_normalize_seq(raw_seq, expected):
    assert normalize_seq(raw_seq) == expected

def test_reverse_complement():
    # Don't need extensive tests, because we're just checking that we're 
    # invoking biopython correctly.
    assert reverse_complement('ATCG') == 'CGAT'

@parametrize_from_file(
        schema=[
            cast(kwargs=with_py.eval, expected=with_py.eval),
            defaults(kwargs={}),
        ],
)
def test_calc_sequence_identity(seq, ref, kwargs, expected):
    id = calc_sequence_identity(seq, ref, **kwargs)
    assert id == pytest.approx(float(expected))

@parametrize_from_file(
        schema=[
            cast(kwargs=with_py.eval, expected=with_py.eval),
            defaults(kwargs={}),
        ],
)
def test_calc_sequence_identity_with_rc(seq, ref, kwargs, expected):
    id = calc_sequence_identity_with_rc(seq, ref, **kwargs)
    assert id == pytest.approx(float(expected))

@parametrize_from_file(
        schema=[
            defaults(db={}),
            cast(tag=with_py.eval, expected=with_py.eval(keys=True)),
            with_freeze.error_or('expected'),
        ],
)
def test_check_tag(db, tag, expected, error):
    db = eval_db(db)
    with error:
        m = check_tag(db, tag)
        assert {k: m.group(k) for k, v in expected.items()} == expected

@parametrize_from_file(
        schema=[
            cast(expected=with_py.eval),
            with_freeze.error_or('expected'),
        ],
)
def test_parse_bool(bool_str, expected, error):
    with error:
        assert parse_bool(bool_str) == expected

@parametrize_from_file(schema=parse_schema)
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
        schema=cast(given=with_py.eval),
)
def test_format_time_s(given, expected):
    assert format_time_s(given) == expected

@parametrize_from_file(
        schema=cast(given=with_py.eval),
)
def test_format_time_m(given, expected):
    assert format_time_m(given) == expected

@parametrize_from_file(schema=parse_schema)
def test_parse_temp(temp_str, kwargs, parsed, converted, error):
    with error:
        assert parse_temp(temp_str, **kwargs) == parsed
    with error:
        assert parse_temp_C(temp_str, **kwargs) == approx(converted['C'])

@parametrize_from_file(schema=parse_schema)
def test_parse_volume(vol_str, kwargs, parsed, converted, error):
    with error:
        assert parse_volume(vol_str, **kwargs) == parsed
    with error:
        assert parse_volume_uL(vol_str, **kwargs) == approx(converted['uL'])
    with error:
        assert parse_volume_mL(vol_str, **kwargs) == approx(converted['mL'])

@parametrize_from_file(schema=parse_schema)
def test_parse_mass(mass_str, kwargs, parsed, converted, error):
    with error:
        assert parse_mass(mass_str, **kwargs) == parsed
    with error:
        assert parse_mass_ug(mass_str, **kwargs) == approx(converted['ug'])
    with error:
        assert parse_mass_mg(mass_str, **kwargs) == approx(converted['mg'])

@parametrize_from_file(schema=[*parse_schema, cast(mw=with_py.eval)])
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

@parametrize_from_file(schema=parse_schema)
def test_parse_size(size_str, kwargs, parsed, converted, error):
    with error:
        assert parse_size(size_str, **kwargs) == parsed
    with error:
        assert parse_size_bp(size_str, **kwargs) == converted['bp']
    with error:
        assert parse_size_kb(size_str, **kwargs) == converted['kb']

@parametrize_from_file(
        schema=[
            cast(
                molecule=with_py.eval,
                default_strandedness=with_py.eval,
                expected=with_py.eval,
            ),
            defaults(default_strandedness=None),
            with_freeze.error_or('expected'),
        ],
)
def test_parse_stranded_molecule(molecule, default_strandedness, expected, error):
    with error:
        actual = parse_stranded_molecule(molecule, default_strandedness)
        assert actual == expected

@parametrize_from_file(
        schema=cast(len=int, molecule=with_py.eval, expected=float),
)
def test_mw_from_length(len, molecule, expected):
    assert mw_from_length(len, molecule) == approx(expected)

@parametrize_from_file(
        schema=[
            cast(
                items=with_py.eval,
                kwargs=with_py.eval,
                expected=with_py.eval,
            ),
            defaults(kwargs={}),
            with_freeze.error_or('expected'),
        ],
)
def test_unanimous(items, kwargs, expected, error):
    with error:
        assert unanimous(items, **kwargs) == expected

@parametrize_from_file(schema=with_py.eval)
def test_join_lists(given, expected):
    assert join_lists(given) == expected

@parametrize_from_file(schema=with_py.eval)
def test_join_dicts(given, expected):
    actual = join_dicts(given)

    assert actual == expected
    assert list(actual.keys()) == list(expected.keys())

@parametrize_from_file(schema=with_py.eval)
def test_join_sets(given, expected):
    assert join_sets(given) == expected

