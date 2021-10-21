#!/usr/bin/env python3

from freezerbox import load_db
from schema_helpers import *

# Only cases where the database cannot be loaded are tested here.  The cases 
# where the database can be successfully loaded are tested with the loaders 
# themselves.

@parametrize_from_file(
        schema=Schema({
            'config': {str: eval},
            'error': error,
        }),
)
def test_load_db_err(config, error):
    with error:
        load_db(config=config)
