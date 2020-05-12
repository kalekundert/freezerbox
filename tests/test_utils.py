#!/usr/bin/env python3

import pytest
from po4 import Tag, ParseError
from po4.model import Construct, Plasmid, Fragment, Oligo
from po4.utils import *
from utils import Params, parametrize_via_toml
from test_model import DummyConstruct

class PrefixParams(Params):
    args = 'args, expected'
    params = [
            ([Construct, Plasmid, Fragment, Oligo], 'dfop'),
            ([Construct, Plasmid, Fragment,      ], 'dfop'),
            ([Construct, Plasmid,           Oligo], 'dfop'),
            ([Construct, Plasmid,                ], 'dfop'),
            ([Construct,          Fragment, Oligo], 'dfop'),
            ([Construct,          Fragment,      ], 'dfop'),
            ([Construct,                    Oligo], 'dfop'),
            ([Construct,                         ], 'dfop'),
            ([           Plasmid, Fragment, Oligo], 'fop'),
            ([           Plasmid, Fragment,      ], 'fp'),
            ([           Plasmid,           Oligo], 'op'),
            ([           Plasmid,                ], 'p'),
            ([                    Fragment, Oligo], 'fo'),
            ([                    Fragment,      ], 'f'),
            ([                              Oligo], 'o'),
            ([                                   ], 'dfop'),
    ]

@parametrize_via_toml('test_utils.toml')
def test_normalize_seq(raw_seq, expected):
    assert normalize_seq(raw_seq) == expected

@PrefixParams.parametrize
def test_get_tag_prefixes(args, expected):
    assert get_tag_prefixes(*args) == set(expected)

@PrefixParams.parametrize
def test_get_tag_pattern(args, expected):
    assert get_tag_pattern(*args) == fr'[{expected}]\d+'

@parametrize_via_toml('test_utils.toml')
def test_parse_tag(tag_str, expected):
    assert parse_tag(tag_str) == Tag(**expected)

@parametrize_via_toml('test_utils.toml')
def test_parse_tag_err(tag_str, error):
    with pytest.raises(ParseError, match=error):
        parse_tag(tag_str)

@parametrize_via_toml('test_utils.toml')
def test_parse_params(params_str, expected):
    assert parse_params(params_str) == expected

@parametrize_via_toml('test_utils.toml')
def test_parse_params_err(params_str, error):
    with pytest.raises(ParseError, match=error):
        parse_params(params_str)

@parametrize_via_toml('test_utils.toml')
def test_parse_param(params, key, pattern, default, expected):
    if isinstance(expected, list):
        expected = tuple(expected)
    assert parse_param(params, key, pattern, default) == expected

@parametrize_via_toml('test_utils.toml')
def test_parse_param_err(params, key, pattern, error):
    with pytest.raises(ParseError, match=error):
        parse_param(params, key, pattern)

@parametrize_via_toml('test_utils.toml')
def test_parse_bool(bool_str, expected):
    assert parse_bool(bool_str) == expected

@parametrize_via_toml('test_utils.toml')
def test_parse_bool_err(bool_str, error):
    with pytest.raises(ParseError, match=error):
        parse_bool(bool_str)

@parametrize_via_toml('test_utils.toml')
def test_parse_time_s(time_str, expected):
    assert parse_time_s(time_str) == expected

@parametrize_via_toml('test_utils.toml')
def test_parse_time_s_err(time_str, error):
    with pytest.raises(ParseError, match=error):
        parse_time_s(time_str)

@parametrize_via_toml('test_utils.toml')
def test_parse_temp_C(temp_str, expected):
    assert parse_temp_C(temp_str) == expected

@parametrize_via_toml('test_utils.toml')
def test_parse_temp_C_err(temp_str, error):
    with pytest.raises(ParseError, match=error):
        parse_temp_C(temp_str)

@parametrize_via_toml('test_utils.toml')
def test_parse_volume_uL(vol_str, expected):
    assert parse_volume_uL(vol_str) == expected

@parametrize_via_toml('test_utils.toml')
def test_parse_volume_uL_err(vol_str, error):
    with pytest.raises(ParseError, match=error):
        parse_volume_uL(vol_str)

@parametrize_via_toml('test_utils.toml')
def test_parse_conc_nM(conc_str, mw, expected_nM, expected_ng_uL):
    assert parse_conc_nM(conc_str, mw)    == pytest.approx(expected_nM)
    assert parse_conc_uM(conc_str, mw)    == pytest.approx(expected_nM / 1000)
    assert parse_conc_ng_uL(conc_str, mw) == pytest.approx(expected_ng_uL)

@parametrize_via_toml('test_utils.toml')
def test_parse_conc_err(conc_str, mw, error):
    with pytest.raises(ParseError, match=error):
        parse_conc_nM(conc_str, mw)
    with pytest.raises(ParseError, match=error):
        parse_conc_ng_uL(conc_str, mw)
@parametrize_via_toml('test_utils.toml')
def test_parse_size_bp(size_str, expected):
    assert parse_size_bp(size_str) == expected

@parametrize_via_toml('test_utils.toml')
def test_parse_size_bp_err(size_str, error):
    with pytest.raises(ParseError, match=error):
        parse_size_bp(size_str)

