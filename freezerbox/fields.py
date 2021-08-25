#!/usr/bin/env python3

"""
A simple format for extracting fields from a string.
"""

from .errors import ParseError
from parsy import (
        ParseError as ParsyError,
        generate, regex, string, alt, test_char,
)
from contextlib import contextmanager

QUOTES = {'"': '"', "'": "'", '“': '”'}

class Fields:

    def __init__(self, indexed, named):
        self.by_index = indexed
        self.by_name = named

    def __repr__(self):
        return f'Fields({self.by_index!r}, {self.by_name!r})'

    def __str__(self):
        index_strs = map(_quote_word, self.by_index)
        name_strs = (f'{k}={_quote_word(v)}' for k, v in self.by_name.items())
        return ' '.join((*index_strs, *name_strs))

    def __eq__(self, other):
        return self.by_index == other.by_index and \
               self.by_name == other.by_name

    def __contains__(self, key):
        if isinstance(key, str):
            return key in self.by_name

        if isinstance(key, int):
            return key < len(self.by_index)

        return False

    def __getitem__(self, key):
        if isinstance(key, str):
            return self.by_name[key]

        if isinstance(key, int):
            try:
                return self.by_index[key]
            except IndexError:
                raise KeyError(key)

        raise KeyError(key)

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError as err:
            return default

def parse_fields_list(fields_str):
    with _reformat_errors():
        return fields_list.parse(fields_str)
        
def parse_fields(fields_str):
    with _reformat_errors():
        return fields.parse(fields_str)

@generate
def fields_list():
    sep = regex(r'\s*;\s+')
    parsed = yield fields.sep_by(sep)
    return parsed

@generate
def fields():
    by_index = []
    by_name = {}
    space = regex(r'\s+')

    @generate
    def field():
        # Always try matching named fields before indexed fields.  This is 
        # necessary the parser for an indexed field will match the first half 
        # of a named field but stop at the '='.  The next parser will then fail 
        # when it tries to continue from there.
        if by_name:
            yield named_field
        else:
            yield named_field | indexed_field

    @generate
    def named_field():
        k, v = yield key_value
        by_name[k] = v

    @generate
    def indexed_field():
        v = yield word
        by_index.append(v)
    
    yield field.sep_by(space, min=1)
    return Fields(by_index, by_name)

@generate
def key_value():
    key = yield word
    yield string('=')
    value = yield word
    return key, value

@generate
def word():
    open_quote_char = yield alt(*map(string, QUOTES)).desc("quote").optional()

    if open_quote_char is None:
        return unquoted_word

    else:
        close_quote_char = QUOTES[open_quote_char]
        escape = regex(fr'\\[\\{close_quote_char}]').map(lambda x: x[-1]).desc("escaped quote")
        value_char = escape | regex(fr'[^\\{close_quote_char}]+')
        word = yield value_char.many().concat()
        yield string(close_quote_char).desc("quote")
        return word

unquoted_word = regex(r'''[^=;\s'"]+''').desc('word')

@contextmanager
def _reformat_errors():
    try:
        yield

    except ParsyError as e1:
        e2 = ParseError(
                stream=e1.stream,
                index=e1.index,
                expected=e1.expected,
        )

        def format_stream(e):
            return f"parsing:  {e.stream!r}"

        def format_expected(e):
            expected = ' or '.join(
                    sorted(map(str, e.expected)),
            )
            return f"expected:  {e.index * ' '}^ {expected}"

        e2.brief = "can't parse fields"
        e2.info += format_stream
        e2.blame += format_expected

        raise e2 from e1

def _quote_word(x):
    x = str(x)
    try:
        unquoted_word.parse(x)
    except ParsyError:
        x = x.replace('\\', '\\\\').replace("'", r"\'")
        return f"'{x}'"
    else:
        return x

