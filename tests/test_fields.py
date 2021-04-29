#!/usr/bin/env python3

import freezerbox
import pytest
import parametrize_from_file

from freezerbox.fields import \
        Fields, word, key_value, parse_fields, parse_fields_list, _quote_word
from freezerbox.errors import ParseError
from parsy import ParseError as ParsyError
from schema_helpers import *

fields_dict = empty_ok({
    'by_index': empty_ok([str]),
    'by_name': empty_ok({str: str}),
})
fields_dict_list = empty_ok([fields_dict])


@parametrize_from_file
def test_word(given, expected):
    assert word.parse(given) == expected

@parametrize_from_file
def test_word_err(given):
    with pytest.raises(ParsyError):
        word.parse(given)

@parametrize_from_file
def test_key_value(given, expected):
    assert key_value.parse(given) == (expected['key'], expected['value'])

@parametrize_from_file
def test_key_value_err(given):
    with pytest.raises(ParsyError):
        key_value.parse(given)

@parametrize_from_file(
        schema=Schema({
            'given': str,
            'expected': fields_dict,
        }),
)
def test_fields(given, expected):
    parsed = parse_fields(given)
    assert parsed.by_index == expected['by_index']
    assert parsed.by_name == expected['by_name']

@parametrize_from_file
def test_fields_err(given, messages):
    with pytest.raises(ParseError) as err:
        parse_fields(given)

    for message in messages:
        assert message in str(err.value)

@parametrize_from_file(
        schema=Schema({
            'given': str,
            'expected': fields_dict_list,
        }),
)
def test_fields_list(given, expected):
    parsed = [
            {'by_index': x.by_index, 'by_name': x.by_name}
            for x in parse_fields_list(given)
    ]
    assert parsed == expected

@parametrize_from_file
def test_fields_list_err(given, messages):
    with pytest.raises(ParseError) as err:
        parse_fields_list(given)

    for message in messages:
        assert message in str(err.value)

@parametrize_from_file
def test_fields_repr(expr):
    fields = eval_freezerbox(expr)
    assert repr(fields) == expr

@parametrize_from_file
def test_fields_str(given, expected):
    fields = eval_freezerbox(given)
    assert str(fields) == expected


def test_fields_eq():
    f1 = Fields(['a'], {'b': 2})
    f2 = Fields(['a'], {'b': 2})
    g1 = Fields(['x'], {'b': 2})
    g2 = Fields(['a'], {'x': 2})
    g3 = Fields(['a'], {'b': 'x'})

    assert f1 == f2
    assert f1 != g1
    assert f1 != g2
    assert f1 != g3

def test_fields_getitem_get():
    fields = Fields(['a', 'b'], {'c': 3, 'd': 4})

    assert fields[0] == fields.get(0) == 'a'
    assert fields[1] == fields.get(1) == 'b'

    assert fields.get(2) == None
    with pytest.raises(KeyError):
        fields[2]

    assert fields['c'] == fields.get('c') == 3
    assert fields['d'] == fields.get('d') == 4

    assert fields.get('e') == None
    with pytest.raises(KeyError):
        fields['e']

def test_fields_contains():
    f1 = Fields([], {})

    assert 0 not in f1
    assert 'a' not in f1

    f2 = Fields(['a'], {'b': 2})
    assert 0 in f2
    assert 1 not in f2
    assert 2 not in f2
    assert 'a' not in f2
    assert 'b' in f2

    f3 = Fields(['a', 'b'], {'c': 3, 'd': 4})

    assert 0 in f3
    assert 1 in f3
    assert 3 not in f3
    assert 4 not in f3
    assert 'a' not in f3
    assert 'b' not in f3
    assert 'c' in f3
    assert 'd' in f3

@parametrize_from_file
def test_quote_word(given, expected):
    assert _quote_word(given) == expected
