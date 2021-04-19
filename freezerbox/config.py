#!/usr/bin/env python3

import appdirs
import appcli

from pathlib import Path
from configurator import Config
from functools import lru_cache
from more_itertools import always_iterable

from .utils import parse_tag
from .errors import QueryError, ParseError

@lru_cache
def load_config():
    config = Config()
    cwd = Path.cwd()
    dirs = [cwd, *cwd.parents]

    for dir in reversed(dirs):
        paths = [
                dir / '.config' / 'freezerbox' / 'conf.toml',
                dir / '.freezerboxrc',
        ]
        for path in paths:
            if path.exists():
                subconf = Config.from_path(path, parser='toml')
                config.merge(subconf)

        dir = dir.parent

    return config.data

PRODUCT = object()
PRECURSOR = object()

class ReagentConfig:
    db_getter = lambda obj: obj.db
    tag_getter = lambda obj: obj.tag
    autoload_db = True
    pick = list

    class QueryHelper:

        def __init__(self, config, obj):
            self.config = config
            self.obj = obj
            self.db = None

        def __getitem__(self, key):
            # First: See if the object has a database attribute.  If it does, 
            # it costs nothing to access it, and it will allow us to include 
            # the path to the database in error messages if any subsequent 
            # steps fail.

            if not self.db:
                try:
                    self.db = self.config.db_getter(self.obj)
                except AttributeError:
                    pass

            # Second: Parse the tags before loading the database.  Loading the 
            # database is expensive, and if the tags won't be in the database 
            # anyways, there's no reason to waste the time.
            
            tags = self.config.tag_getter(self.obj)

            try:
                tags = [
                        parse_tag(x)
                        for x in always_iterable(tags)
                ]
            except ParseError as err:
                raise KeyError from err

            # Third: Load the database.

            if not self.db and self.config.autoload_db:
                from .model import load_db
                self.db = load_db()

            if not self.db:
                raise KeyError("no freezerbox database found")

            # Fourth: Lookup values.

            try:
                values = [
                        getattr(self.db[x], key)
                        for x in tags
                ]

            except (QueryError, AttributeError) as err:
                raise KeyError from err

            return self.config.pick(values)

        def get_location(self):
            return self.db.name if self.db else "*no database loaded*"

    def __init__(self, tag_getter=None, db_getter=None, autoload_db=None, pick=None):
        cls = self.__class__

        # Access the getter/pick functions through the class.  If accessed via 
        # the instance, they would become bound and would require a self 
        # argument. 

        self.db_getter = db_getter or cls.db_getter
        self.tag_getter = tag_getter or cls.tag_getter
        self.autoload_db = autoload_db if autoload_db is not None else self.autoload_db
        self.pick = pick or cls.pick

    def load(self, obj):
        helper = self.QueryHelper(self, obj)
        yield appcli.Layer(
                values=helper,
                location=helper.get_location,
        )


class MakerArgsConfig:
    product_getter = lambda obj: obj.product

    class QueryHelper:

        def __init__(self, config, obj):
            self.config = config
            self.obj = obj

        def __getitem__(self, key):
            product = self.config.product_getter(self.obj)

            if key is PRODUCT:
                return product

            if key is PRECURSOR:
                return product.precursor

            return product.maker_args[key]

        def get_location(self):
            product = self.config.product_getter(self.obj)
            return product.db.name


    def __init__(self, db_getter=None, product_getter=None):
        cls = self.__class__

        # Access the getter through the class.  If accessed via the instance, 
        # it would become bound and would require a self argument. 

        self.product_getter = product_getter or cls.product_getter

    def load(self, obj):
        helper = self.QueryHelper(self, obj)
        yield appcli.Layer(
                values=helper,
                location=helper.get_location,
        )

