#!/usr/bin/env python3

import appdirs
from pathlib import Path
from configurator import Config
from functools import lru_cache

@lru_cache
def load_config():
    config = Config()
    cwd = Path.cwd()
    dirs = [cwd, *cwd.parents]

    for dir in reversed(dirs):
        paths = [
                dir / '.config' / 'po4' / 'conf.toml',
                dir / '.po4rc',
        ]
        for path in paths:
            if path.exists():
                subconf = Config.from_path(path, parser='toml')
                config.merge(subconf)

        dir = dir.parent

    return config.data
    
    
