#!/usr/bin/env python3

import po4
import pytest
import parametrize_from_file

from po4.fields import word, key_value, parse_fields, parse_fields_list
from po4.errors import ParseError
from parsy import ParseError as ParsyError
from voluptuous import Schema, And, Or, Optional

empty_list = And('', lambda x: [])
empty_dict = And('', lambda x: {})
fields_dict = Or(
        {
            'by_index': Or([str], empty_list),
            'by_name': Or({str: str}, empty_dict),
        },
        empty_dict,
)
fields_dict_list = Or([fields_dict], empty_list)

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

def test_fields_getitem():
    fields = po4.Fields(['a', 'b'], {'c': 3, 'd': 4})

    assert fields[0] == 'a'
    assert fields[1] == 'b'

    with pytest.raises(KeyError):
        fields[2]

    assert fields['c'] == 3
    assert fields['d'] == 4

    with pytest.raises(KeyError):
        fields['e']

