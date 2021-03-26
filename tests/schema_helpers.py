#!/usr/bin/env python3

import po4
import pytest
import parametrize_from_file
from voluptuous import Schema, Invalid, Coerce, And, Or, Optional

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

eval_po4 = eval_with(po4=po4)
eval_pytest = eval_with().all(pytest)

empty_list = And('', lambda x: [])
empty_dict = And('', lambda x: {})
