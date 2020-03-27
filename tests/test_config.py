#!/usr/bin/env python3

import os
from contextlib import contextmanager
from pathlib import Path
from po4 import load_config

DUMMY_CONFIG = Path(__file__).parent / 'dummy_config'

def test_config():
    with cd(DUMMY_CONFIG):
        load_config.cache_clear()
        config = load_config()

        # Only check the values that are explicitly set by the test, because 
        # any other values could be affected by real configuration files 
        # present on the tester's system.

        assert config['use'] == 'db1'
        assert config['database']['db1']['type'] == 'type1'
        assert config['database']['db1']['option'] == 'option1'
        assert config['database']['db2']['type'] == 'type2'
        assert config['database']['db2']['option'] == 'option2'

    with cd(DUMMY_CONFIG / 'subdir'):
        load_config.cache_clear()
        config = load_config()

        assert config['use'] == 'db2'
        assert config['database']['db1']['type'] == 'type1'
        assert config['database']['db1']['option'] == 'option1'
        assert config['database']['db2']['type'] == 'type2'
        assert config['database']['db2']['option'] == 'option2'


@contextmanager
def cd(dir):
    try:
        prev_cwd = Path.cwd()
        os.chdir(dir)
        yield

    finally:
        os.chdir(prev_cwd)
