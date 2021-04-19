#!/usr/bin/env python3

import freezerbox
import pytest
import parametrize_from_file
import networkx as nx
import stepwise
from voluptuous import Schema, Invalid, Coerce, And, Or, Optional
from unittest.mock import MagicMock
from mock_model import MockReagent

class eval_with:

    def __init__(self, globals=None, **kw_globals):
        self.globals = globals or {}
        self.globals.update(kw_globals)

    def __call__(self, code):
        try:
            return eval(code, self.globals)
        except Exception as err:
            raise Invalid(str(err)) from err

    def all(self, module):
        self.globals.update({
                k: module.__dict__[k]
                for k in module.__all__
        })
        return self

eval_freezerbox = eval_with(
        freezerbox=freezerbox,
        nx=nx,
        Quantity=stepwise.Quantity,
        Fields=freezerbox.Fields,
        MockReagent=MockReagent,
)
eval_pytest = eval_with().all(pytest)

empty_list = And('', lambda x: [])
empty_dict = And('', lambda x: {})

def empty_ok(x):
    return Or(x, And('', lambda y: type(x)()))

class nullcontext:
    # This context manager is built in to python>=3.7

    def __enter__(self):
        pass

    def __exit__(self, *exc):
        pass

def error_or(**expected):
    schema = {}

    # Either specify an error or an expected value, not both.
    # KBK: This doesn't work for some reason.
    #schema[Or('error', *expected, only_one=True)] = object

    schema[Optional('error', default='none')] = error

    def check(schema):
        # This function basically just reimplements `Or`, but with a better 
        # error message.  The error message for `Or` is confusing because it 
        # only mentions the first option and not the second.  That's especially 
        # bad in this case, where the first option is basically an internal 
        # implementation detail.  This function changes the error message so 
        # that only the second option is mentioned, which is the least 
        # confusing in this case.
        # 
        # It's worth noting that the real problem is that voluptuous checks 
        # default values.  I can't imagine a case where this is actually 
        # useful. I might think about making a PR for that.

        def do_check(x):
            if isinstance(x, MagicMock):
                return x
            return Schema(schema)(x)
        return do_check

    schema.update({
        Optional(k, default=MagicMock()): check(v)
        for k, v in expected.items()
    })
    return schema

# Something to think about: I'd like to put a version of this function in the 
# `parametrize_from_file` package.  I need a general way to specify the local 
# variables, though.  And to `eval()` the exception type...

def error(x):
    if x == 'none':
        return nullcontext()

    err_eval = eval_with(
            freezerbox=freezerbox,
            nx=nx,
            QueryError=freezerbox.QueryError,
            ParseError=freezerbox.ParseError,
            LoadError=freezerbox.LoadError,
    )
    err_type = err_eval(x['type'])
    err_messages = x.get('message', [])
    if not isinstance(err_messages, list):
        err_messages = list(err_messages)

    # Normally I'd use `@contextmanager` to make a context manager like this, 
    # but generator-based context managers cannot be reused.  This is a problem 
    # for tests, because if a test using this context manager is parametrized, 
    # the same context manager instance will need to be reused multiple times.  
    # The only way to support this is to implement the context manager from 
    # scratch.

    class expect_error:

        def __enter__(self):
            self.raises = pytest.raises(err_type)
            self.err = self.raises.__enter__()

        def __exit__(self, *args):
            if self.raises.__exit__(*args):
                for msg in err_messages:
                    self.err.match(msg)
                return True

    return expect_error()


class Params:

    @classmethod
    def parametrize(cls, f):
        args = cls.args

        params = []
        for k, v in cls.__dict__.items():
            if k.startswith('params'):
                params.extend(v)

        # Could also check to make sure parameters make sense.

        return pytest.mark.parametrize(args, params)(f)

