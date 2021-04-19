#!/usr/bin/env python3

import os, freezerbox, pytest
from contextlib import contextmanager
from pathlib import Path
from freezerbox import load_config, ReagentConfig, MakerArgsConfig
from more_itertools import one, first

from test_model import MockReagent

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

@contextmanager
def cd(dir):
    try:
        prev_cwd = Path.cwd()
        os.chdir(dir)
        yield

    finally:
        os.chdir(prev_cwd)


def test_reagent_config_tags_1():
    db = freezerbox.Database(name='a')
    db['x1'] = MockReagent(name='1')

    obj = MockObj()
    config = ReagentConfig()
    layer = one(config.load(obj))

    obj.db = db
    obj.tag = 'x1'

    assert layer.values['name'] == ['1']
    assert layer.location == 'a'

def test_reagent_config_tags_2():
    db = freezerbox.Database(name='a')
    db['x1'] = MockReagent(name='1')
    db['x2'] = MockReagent(name='2')

    obj = MockObj()
    config = ReagentConfig()
    layer = one(config.load(obj))

    obj.db = db
    obj.tag = 'x1', 'x2'

    assert layer.values['name'] == ['1', '2']
    assert layer.location == 'a'

def test_reagent_config_tags_not_found():
    db = freezerbox.Database(name='a')
    db['x1'] = MockReagent(name='1')

    obj = MockObj()
    config = ReagentConfig()
    layer = one(config.load(obj))

    obj.db = db
    obj.tag = 'x2'

    with pytest.raises(KeyError):
        layer.values['name']

    assert layer.location == 'a'

def test_reagent_config_tags_not_parseable():
    db = freezerbox.Database(name='a')
    db['x1'] = MockReagent(name='1')

    obj = MockObj()
    config = ReagentConfig()
    layer = one(config.load(obj))

    obj.db = db
    obj.tag = 'not-a-tag'

    with pytest.raises(KeyError):
        layer.values['name']

    assert layer.location == 'a'

def test_reagent_config_key_not_found():
    db = freezerbox.Database(name='a')
    db['x1'] = MockReagent(name='1')

    obj = MockObj()
    config = ReagentConfig()
    layer = one(config.load(obj))

    obj.db = db
    obj.tag = 'x1'

    with pytest.raises(KeyError):
        layer.values['not-a-key']

    assert layer.location == 'a'

def test_reagent_config_pick():
    db = freezerbox.Database(name='a')
    db['x1'] = MockReagent(name='1')
    db['x2'] = MockReagent(name='2')

    obj = MockObj()
    config = ReagentConfig(pick=first)
    layer = one(config.load(obj))

    obj.db = db
    obj.tag = ['x1', 'x2']

    assert layer.values['name'] == '1'
    assert layer.location == 'a'

def test_reagent_config_db_autoload(monkeypatch):
    db = freezerbox.Database(name='a')
    db['x1'] = MockReagent(name='1')
    monkeypatch.setattr(freezerbox.model, 'load_db', lambda: db)

    obj = MockObj()
    config = ReagentConfig()
    layer = one(config.load(obj))

    obj.tag = 'x1'

    assert layer.values['name'] == ['1']
    assert layer.location == 'a'

def test_reagent_config_db_not_found():
    obj = MockObj()
    config = ReagentConfig(autoload_db=False)
    layer = one(config.load(obj))

    obj.tag = 'x1'

    with pytest.raises(KeyError, match="no freezerbox database found"):
        layer.values['name']

    assert layer.location == '*no database loaded*'

def reagent_config_from_ctor():
    return ReagentConfig(
            db_getter=lambda self: self.my_db,
            tag_getter=lambda self: self.my_tag,
    )

def reagent_config_from_subclass():

    class MyConfig(ReagentConfig):
        db_getter = lambda self: self.my_db
        tag_getter = lambda self: self.my_tag

    return MyConfig()

@pytest.mark.parametrize(
        'config_factory', [
            reagent_config_from_ctor,
            reagent_config_from_subclass,
        ]
)
def test_reagent_config_getters(config_factory):
    db = freezerbox.Database(name='a')
    db['x1'] = MockReagent(name='1')

    obj = MockObj()
    config = config_factory()
    layer = one(config.load(obj))

    obj.my_db = db
    obj.my_tag = 'x1'

    assert layer.values['name'] == ['1']
    assert layer.location == 'a'


def test_maker_args_config_synthesis():
    db = freezerbox.Database(name='loc')
    db['x1'] = x1 = MockReagent(
            synthesis=freezerbox.Fields(['a'], {'b': 'c'}),
    )
    i1 = x1.make_intermediate(0)

    obj = MockObj()
    config = MakerArgsConfig()
    layer = one(config.load(obj))

    obj.product = i1

    assert layer.values[0] == 'a'
    assert layer.values['b'] == 'c'
    assert layer.values[freezerbox.PRODUCT] is i1
    assert layer.location == 'loc'

def test_maker_args_config_cleanup():
    db = freezerbox.Database(name='loc')
    db['x1'] = x1 = MockReagent(
            synthesis=freezerbox.Fields(['a'], {'b': 'c'}),
            cleanups=[freezerbox.Fields(['d'], {'e': 'f'})],
    )
    i1 = x1.make_intermediate(1)

    obj = MockObj()
    config = MakerArgsConfig()
    layer = one(config.load(obj))

    obj.product = i1

    assert layer.values[0] == 'd'
    assert layer.values['e'] == 'f'
    assert layer.values[freezerbox.PRODUCT] is i1
    assert layer.values[freezerbox.PRECURSOR] is i1.precursor
    assert layer.location == 'loc'

def maker_args_config_from_ctor():
    return MakerArgsConfig(
            product_getter=lambda self: self.my_product,
    )

def maker_args_config_from_subclass():

    class MyConfig(MakerArgsConfig):
        product_getter = lambda self: self.my_product

    return MyConfig()

@pytest.mark.parametrize(
        'config_factory', [
            maker_args_config_from_ctor,
            maker_args_config_from_subclass,
        ]
)
def test_maker_args_config_getters_inherit(config_factory):
    db = freezerbox.Database(name='loc')
    db['x1'] = x1 = MockReagent(
            synthesis=freezerbox.Fields(['a'], {'b': 'c'}),
            cleanups=[freezerbox.Fields(['d'], {'e': 'f'})],
    )
    i1 = x1.make_intermediate(0)

    obj = MockObj()
    config = config_factory()
    layer = one(config.load(obj))

    obj.my_product = i1

    assert layer.values[0] == 'a'
    assert layer.values['b'] == 'c'
    assert layer.values[freezerbox.PRODUCT] is i1
    assert layer.location == 'loc'
