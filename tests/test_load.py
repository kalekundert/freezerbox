#!/usr/bin/env python3

from freezerbox import load_db
from schema_helpers import *

@parametrize_from_file(
        schema=Schema({
            'config': {str: eval},
            'error': error,
        }),
)
def test_load_db_err(config, error):
    with error:
        load_db(config=config)
