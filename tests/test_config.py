#!/usr/bin/env python3

import freezerbox, pytest
from pathlib import Path
from freezerbox import load_config, ReagentConfig, MakerArgsConfig, Fields, cd
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

    load_config.cache_clear()


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

def test_reagent_config_transform():
    db = freezerbox.Database(name='a')
    db['x1'] = MockReagent(name='1')
    db['x2'] = MockReagent(name='2')

    obj = MockObj()
    config = ReagentConfig(transform=first)
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

def test_reagent_config_empty_db():
    db = freezerbox.Database(name='a')

    obj = MockObj()
    config = ReagentConfig()
    layer = one(config.load(obj))

    obj.db = db
    obj.tag = []

    assert layer.values['x'] == []
    assert layer.values.db is db
    assert layer.location == 'a'

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
            synthesis=Fields(['a'], {'b': 'c'}),
    )
    i1 = x1.make_intermediate(0)

    obj = MockObj()
    config = MakerArgsConfig()
    layer = one(config.load(obj))

    obj.products = [i1]

    assert layer.values[0] == 'a'
    assert layer.values['b'] == 'c'
    assert layer.values.product is i1
    assert layer.location == 'loc'

def test_maker_args_config_cleanup():
    db = freezerbox.Database(name='loc')
    db['x1'] = x1 = MockReagent(
            synthesis=Fields(['a'], {'b': 'c'}),
            cleanups=[Fields(['d'], {'e': 'f'})],
    )
    i1 = x1.make_intermediate(1)

    obj = MockObj()
    config = MakerArgsConfig()
    layer = one(config.load(obj))

    obj.products = [i1]

    assert layer.values[0] == 'd'
    assert layer.values['e'] == 'f'
    assert layer.values.product is i1
    assert layer.values.precursor is i1.precursor
    assert layer.location == 'loc'

def maker_args_config_from_ctor():
    return MakerArgsConfig(
            products_getter=lambda self: self.my_products,
    )

def maker_args_config_from_subclass():

    class MyConfig(MakerArgsConfig):
        products_getter = lambda self: self.my_products

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
            synthesis=Fields(['a'], {'b': 'c'}),
            cleanups=[Fields(['d'], {'e': 'f'})],
    )
    i1 = x1.make_intermediate(0)

    obj = MockObj()
    config = config_factory()
    layer = one(config.load(obj))

    obj.my_products = [i1]

    assert layer.values[0] == 'a'
    assert layer.values['b'] == 'c'
    assert layer.values.product is i1
    assert layer.location == 'loc'

def test_maker_args_config_err():
    db = freezerbox.Database(name='loc')
    db['x1'] = x1 = MockReagent(
            synthesis=Fields(['a'], {'b': 'c'}),
    )
    i1 = x1.make_intermediate(0)

    obj = MockObj()
    config = MakerArgsConfig()
    layer = one(config.load(obj))

    obj.products = []

    with pytest.raises(KeyError, match="expected 1 product, found 0"):
        layer.values[0]

