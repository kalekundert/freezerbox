#!/usr/bin/env python3

import pytest
from pathlib import Path
from po4 import LoadError, load_db
from utils import parametrize_via_toml

@parametrize_via_toml('test_load.toml')
def test_load_db_err(config, error):
    with pytest.raises(LoadError, match=error):
        load_db(config=config)
