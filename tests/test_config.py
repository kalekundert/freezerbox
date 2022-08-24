#!/usr/bin/env python3

from freezerbox.config import *
from freezerbox.utils import cd
from param_helpers import *

@parametrize_from_file(
        schema=defaults(cwd='.'),
        indirect=['tmp_files'],
)
def test_load_config(tmp_files, cwd, expected_config, expected_paths):
    load_config.cache_clear()

    with_paths = Namespace(
            DIR=tmp_files,
            BUILTIN_CONF=BUILTIN_CONF,
    )
    expected_paths = with_paths.eval(expected_paths)

    with cd(tmp_files / cwd):
        config = load_config()

        # Remove feature sequences, just to simplify test files:
        for feat in config.get('features', []):
            feat.pop('seq', None)

        assert config == expected_config
        assert config.paths == expected_paths

def test_dict_view():
    d = {'a': 'b'}
    v = DictView(d)

    assert v == d
    assert v == v
    assert len(v) == 1
    assert repr(v) == "DictView({'a': 'b'})"
    assert list(iter(v)) == ['a']
    assert v['a'] == 'b'

