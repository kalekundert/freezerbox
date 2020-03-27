#!/usr/bin/env python3

import pytest
from po4 import only_raise

class ParentError(Exception):
    pass

class ChildError(ParentError):
    pass

class UnrelatedError(Exception):
    pass

@pytest.mark.parametrize(
        'only_err, raise_err, catch_err', [
            (   ParentError,    ParentError,    ParentError),
            (   ParentError,     ChildError,     ChildError),
            (   ParentError, UnrelatedError,    ParentError),

            (    ChildError,    ParentError,     ChildError),
            (    ChildError,     ChildError,     ChildError),
            (    ChildError, UnrelatedError,     ChildError),

            (UnrelatedError,    ParentError, UnrelatedError),
            (UnrelatedError,     ChildError, UnrelatedError),
            (UnrelatedError, UnrelatedError, UnrelatedError),
])
def test_only_raise(only_err, raise_err, catch_err):

    @only_raise(only_err)
    def f(err):
        raise err

    with pytest.raises(catch_err):
        f(raise_err)

