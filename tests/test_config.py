#!/usr/bin/env python3

import freezerbox, pytest
import parametrize_from_file

from pathlib import Path
from freezerbox import load_config, ReagentConfig, MakerConfig, Fields, cd
from appcli.model import Log
from more_itertools import one, first, zip_equal
from test_model import MockReagent
from re_assert import Matches
from operator import attrgetter
from mock_model import mock_plugins
from pprint import pprint
from schema_helpers import *

MOCK_CONFIG = Path(__file__).parent / 'mock_config'

class MockObj:
    pass

def test_config():
    with cd(MOCK_CONFIG):
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

    with cd(MOCK_CONFIG / 'subdir'):
        load_config.cache_clear()
        config = load_config()

        assert config['use'] == 'db2'
        assert config['database']['db1']['type'] == 'type1'
        assert config['database']['db1']['option'] == 'option1'
        assert config['database']['db2']['type'] == 'type2'
        assert config['database']['db2']['option'] == 'option2'

    load_config.cache_clear()

@parametrize_from_file(
        schema=Schema({
            'db': eval_db,
            'obj': exec_with(
                'obj',
                MockObj=MockObj,
            ),
            Optional('config_cls', default='class MockConfig(ReagentConfig): pass'): exec_with(
                'MockConfig',
                ReagentConfig=freezerbox.ReagentConfig,
                attrgetter=attrgetter,
            ),
            Optional('db_access', default='cache'): str,
            'key': eval_with(
                attrgetter=attrgetter,
            ),
            'expected': empty_ok([eval_python]),
            'info': [str],
    }),
)
def test_reagent_config(db, config_cls, obj, db_access, key, expected, info, monkeypatch, mock_plugins):
    db.name = '/path/to/db'
    config = config_cls(obj)
    layer = one(config.load())

    if db_access == 'cache':
        layer.db = db

    if db_access.startswith('obj'):
        attr = db_access.split('.')[1] if '.' in db_access else 'db'
        setattr(obj, attr, db)

    if db_access == 'load':
        monkeypatch.setattr(freezerbox.model, 'load_db', lambda: db)
    else:
        monkeypatch.setattr(freezerbox.model, 'load_db', lambda: NotImplemented)

    log = Log()
    values = list(layer.iter_values(key, log))

    assert values == expected

    for actual, pattern in zip_equal(log.err.info_strs, info):
        Matches(pattern).assert_matches(actual)

@parametrize_from_file(
        schema=Schema({
            'db': eval_db,
            'config_cls': exec_with(
                'MockConfig',
                ProductConfig=freezerbox.ProductConfig,
                MakerConfig=freezerbox.MakerConfig,
                PrecursorConfig=freezerbox.PrecursorConfig,
                attrgetter=attrgetter,
            ),
            'products': {str: Coerce(int)},
            Optional('products_attr', default='products'): str,
            'key': eval_with(
                attrgetter=attrgetter,
            ),
            **error_or({
                'expected': empty_ok([eval_freezerbox]),
                'info': [str],
            }),
    }),
)
def test_product_configs(db, config_cls, products, products_attr, key, expected, info, error, mock_plugins):
    db.name = 'path/to/db'
    if not products:
        products = db.keys()

    obj = MockObj()

    if products_attr:
        setattr(obj, products_attr, [
            db[k].make_intermediate(i)
            for k,i in products.items()
        ])

    config = config_cls(obj)
    layer = one(config.load())

    with error:
        log = Log()
        values = list(layer.iter_values(key, log))
        pprint(log.err.info_strs)

        assert values == expected

        for actual, pattern in zip_equal(log.err.info_strs, info):
            Matches(pattern).assert_matches(actual)

