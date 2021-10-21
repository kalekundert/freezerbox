#!/usr/bin/env python3

import rtoml

from pathlib import Path
from functools import lru_cache
from mergedeep import merge
from collections.abc import Mapping

BUILTIN_CONF = Path(__file__).parent / 'conf.toml'

@lru_cache
def load_config():
    config = rtoml.load(BUILTIN_CONF)
    config_paths = _fill(config, BUILTIN_CONF)

    cwd = Path.cwd()
    dirs = [cwd, *cwd.parents]

    for dir in reversed(dirs):
        paths = [
                dir / '.config' / 'freezerbox' / 'conf.toml',
                dir / '.freezerboxrc',
        ]
        for path in paths:
            if path.exists():
                local_config = rtoml.load(path)
                local_config_paths = _fill(local_config, path)

                merge(config, local_config)
                merge(config_paths, local_config_paths)

    return Config(config, config_paths)

class DictView(Mapping):

    def __init__(self, dict):
        self.dict = dict

    def __repr__(self):
        return f'{self.__class__.__name__}({self.dict!r})'

    def __iter__(self):
        return self.dict.__iter__()

    def __len__(self):
        return self.dict.__len__()

    def __getitem__(self, key):
        return self.dict.__getitem__(key)

class Config(DictView):

    def __init__(self, config, paths={}):
        super().__init__(config)

        # Guarantee that there is a path for every config option.  This should 
        # never come up if loading a database via `load_db()`, but it does make 
        # it easier to construct databases on the fly.  This happens a lot in 
        # testing.
        all_paths = _fill(config, 'unspecified')
        merge(all_paths, paths)

        self.paths = DictView(all_paths)

def _fill(given, value):
    return {
            k: _fill(v, value) if isinstance(v, dict) else value
            for k, v in given.items()
    }
