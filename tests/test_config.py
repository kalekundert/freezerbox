#!/usr/bin/env python3

import os, po4, pytest
from contextlib import contextmanager
from pathlib import Path
from po4 import load_config, Po4Config, Po4TargetConfig
from more_itertools import one, first

from test_model import DummyConstruct

DUMMY_CONFIG = Path(__file__).parent / 'dummy_config'

class DummyObj:
    pass

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


def test_po4_config_tags_1():
    db = po4.Database(name='a')
    db['d1'] = DummyConstruct(name='1')

    obj = DummyObj()
    config = Po4Config()
    layer = one(config.load(obj))

    obj.po4_db = db
    obj.tag = 'd1'

    assert layer.values['name'] == ['1']
    assert layer.location == 'a'

def test_po4_config_tags_2():
    db = po4.Database(name='a')
    db['d1'] = DummyConstruct(name='1')
    db['d2'] = DummyConstruct(name='2')

    obj = DummyObj()
    config = Po4Config()
    layer = one(config.load(obj))

    obj.po4_db = db
    obj.tag = 'd1', 'd2'

    assert layer.values['name'] == ['1', '2']
    assert layer.location == 'a'

def test_po4_config_tags_not_found():
    db = po4.Database(name='a')
    db['d1'] = DummyConstruct(name='1')

    obj = DummyObj()
    config = Po4Config()
    layer = one(config.load(obj))

    obj.po4_db = db
    obj.tag = 'd2'

    with pytest.raises(KeyError):
        layer.values['name']

    assert layer.location == 'a'

def test_po4_config_tags_not_parseable():
    db = po4.Database(name='a')
    db['d1'] = DummyConstruct(name='1')

    obj = DummyObj()
    config = Po4Config()
    layer = one(config.load(obj))

    obj.po4_db = db
    obj.tag = 'not-a-tag'

    with pytest.raises(KeyError):
        layer.values['name']

    assert layer.location == 'a'

def test_po4_config_key_not_found():
    db = po4.Database(name='a')
    db['d1'] = DummyConstruct(name='1')

    obj = DummyObj()
    config = Po4Config()
    layer = one(config.load(obj))

    obj.po4_db = db
    obj.tag = 'd1'

    with pytest.raises(KeyError):
        layer.values['not-a-key']

    assert layer.location == 'a'

def test_po4_config_pick():
    db = po4.Database(name='a')
    db['d1'] = DummyConstruct(name='1')
    db['d2'] = DummyConstruct(name='2')

    obj = DummyObj()
    config = Po4Config(pick=first)
    layer = one(config.load(obj))

    obj.po4_db = db
    obj.tag = ['d1', 'd2']

    assert layer.values['name'] == '1'
    assert layer.location == 'a'

def test_po4_config_db_autoload(monkeypatch):
    db = po4.Database(name='a')
    db['d1'] = DummyConstruct(name='1')
    monkeypatch.setattr(po4.model, 'load_db', lambda: db)

    obj = DummyObj()
    config = Po4Config()
    layer = one(config.load(obj))

    obj.tag = 'd1'

    assert layer.values['name'] == ['1']
    assert layer.location == 'a'

def test_po4_config_db_not_found():
    obj = DummyObj()
    config = Po4Config(autoload_db=False)
    layer = one(config.load(obj))

    obj.tag = 'd1'

    with pytest.raises(KeyError, match="no PO₄ database found"):
        layer.values['name']

    assert layer.location == '*no database loaded*'

def po4_config_from_ctor():
    return Po4Config(
            db_getter=lambda self: self.my_db,
            tag_getter=lambda self: self.my_tag,
    )

def po4_config_from_subclass():

    class MyConfig(Po4Config):
        db_getter = lambda self: self.my_db
        tag_getter = lambda self: self.my_tag

    return MyConfig()

@pytest.mark.parametrize(
        'config_factory', [
            po4_config_from_ctor,
            po4_config_from_subclass,
        ]
)
def test_po4_config_getters(config_factory):
    db = po4.Database(name='a')
    db['d1'] = DummyConstruct(name='1')

    obj = DummyObj()
    config = config_factory()
    layer = one(config.load(obj))

    obj.my_db = db
    obj.my_tag = 'd1'

    assert layer.values['name'] == ['1']
    assert layer.location == 'a'


def test_po4_target_config():
    db = po4.Database(name='loc')
    db['d1'] = d1 = DummyConstruct(name='1')

    obj = DummyObj()
    config = Po4TargetConfig()
    layer = one(config.load(obj))

    obj.po4_db = db
    obj.po4_target = po4.Target(d1, po4.Fields(['a'], {'b': 'c'}))

    assert layer.values[0] == 'a'
    assert layer.values['b'] == 'c'
    assert layer.values.product is d1
    assert layer.location == 'loc'

def po4_target_config_from_ctor():
    return Po4TargetConfig(
            db_getter=lambda self: self.my_db,
            target_getter=lambda self: self.my_target,
    )

def po4_target_config_from_subclass():

    class MyConfig(Po4TargetConfig):
        db_getter = lambda self: self.my_db
        target_getter = lambda self: self.my_target

    return MyConfig()

@pytest.mark.parametrize(
        'config_factory', [
            po4_target_config_from_ctor,
            po4_target_config_from_subclass,
        ]
)
def test_po4_target_config_getters_inherit(config_factory):
    db = po4.Database(name='loc')
    db['d1'] = d1 = DummyConstruct(name='1')

    obj = DummyObj()
    config = config_factory()
    layer = one(config.load(obj))

    obj.my_db = db
    obj.my_target = po4.Target(d1, po4.Fields(['a'], {'b': 'c'}))

    assert layer.values[0] == 'a'
    assert layer.values['b'] == 'c'
    assert layer.values.product is d1
    assert layer.location == 'loc'
