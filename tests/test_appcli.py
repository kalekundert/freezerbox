#!/usr/bin/env python3

import freezerbox, pytest
import parametrize_from_file

from appcli.model import Log
from more_itertools import one, zip_equal
from re_assert import Matches
from mock_model import mock_plugins, MockMolecule
from operator import attrgetter
from pprint import pprint
from param_helpers import *

class MockObj:
    pass

@parametrize_from_file(
        schema=Schema({
            'db': dict,
            'obj': str,
            Optional('config_cls', default='class MockConfig(ReagentConfig): pass'): str,
            Optional('db_access', default='cache'): str,
            'key': with_py.eval,
            'expected': [with_py.eval],
            'info': [str],
    }),
)
def test_reagent_config(db, config_cls, obj, db_access, key, expected, info, monkeypatch, mock_plugins):
    with_mock_obj = Namespace(
            MockObj=MockObj,
            LoadError=freezerbox.LoadError,
    )
    with_reagent_config = Namespace(
        ReagentConfig=freezerbox.ReagentConfig,
        MockMolecule=MockMolecule,
        attrgetter=attrgetter,
    )

    db = eval_db(db)
    obj = with_mock_obj.exec(obj)['obj']
    config_cls = with_reagent_config.exec(config_cls)['MockConfig']
    config = config_cls(obj)
    layer = one(config.load())

    if db_access == 'none':
        pass

    if db_access == 'cache':
        layer.db = db

    if db_access.startswith('obj'):
        attr = db_access.split('.')[1] if '.' in db_access else 'db'
        setattr(obj, attr, db)

    if db_access == 'load':
        monkeypatch.setattr(freezerbox.model, 'load_db', lambda: db)
    elif db_access == 'load-err':
        def fail_to_load(): raise freezerbox.LoadError("mock error")
        monkeypatch.setattr(freezerbox.model, 'load_db', fail_to_load)
    else:
        monkeypatch.setattr(freezerbox.model, 'load_db', lambda: NotImplemented)

    log = Log()
    values = list(layer.iter_values(key, log))

    try:
        assert values == expected
    finally:
        print(log.err)

    for actual, pattern in zip_equal(log.err.info_strs, info):
        Matches(pattern).assert_matches(actual)

@parametrize_from_file(
        schema=Schema({
            'db': dict,
            'config_cls': str,
            'products': {str: Coerce(int)},
            Optional('products_attr', default='products'): str,
            'key': with_py.eval,
            **with_freeze.error_or({
                'expected': [with_freeze.eval],
                'info': [str],
            }),
    }),
)
def test_product_configs(db, config_cls, products, products_attr, key, expected, info, error, mock_plugins):
    with_configs = Namespace(
            ProductConfig=freezerbox.ProductConfig,
            MakerConfig=freezerbox.MakerConfig,
            PrecursorConfig=freezerbox.PrecursorConfig,
            MockMolecule=MockMolecule,
            attrgetter=attrgetter,
    )

    db = eval_db(db)
    config_cls = with_configs.exec(config_cls)['MockConfig']
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

