#!/usr/bin/env python3

import functools
from tidyexc import Error, only_raise

class Po4Error(Error):

    @property
    def brief_str(self):
        brief_str = super().brief_str
        culprit = self.data.get('culprit')

        if culprit:
            culprit = getattr(culprit, '_tag', None) or culprit
            brief_str = f"{culprit}: {brief_str}"

        return brief_str


class LoadError(Po4Error):
    # For errors relating to loading the database.
    pass

class QueryError(Po4Error):
    # For errors relating to looking up information from the database.
    pass

class ParseError(QueryError):
    # For errors relating to parsing a value from the database, e.g. a unit.
    pass

class CheckError(Po4Error):
    # For errors found when checking the database for self-consistency.
    pass


