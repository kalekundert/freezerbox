#!/usr/bin/env python3

import functools
from inform import Error, get_culprit

class Po4Error(Error):

    def __init__(self, *args, **kwargs):
        if 'culprit' not in kwargs:
            kwargs['culprit'] = get_culprit()
        super().__init__(*args, **kwargs)

class LoadError(Po4Error):
    pass

class QueryError(Po4Error):
    pass

class ParseError(QueryError):
    pass

class CheckError(Po4Error):
    pass

class UsageError(Po4Error):
    pass



class only_raise:
    """
    Guarantee that the decorated function can only raise the given type of 
    exception.

    Any unhandled exception raised by the decorated function will be caught and 
    re-raised using an exception of the given type. 
    """

    def __init__(self, err_cls):
        self.err_cls = err_cls

    def __call__(self, f):

        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            try:
                return f(*args, **kwargs)
            except self.err_cls as err:
                raise err from None
            except Exception as err:
                raise self.err_cls(str(err)) from err

        return wrapper
