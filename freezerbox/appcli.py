#!/usr/bin/env python3

import appcli
import autoprop

from appcli import unbind_method
from more_itertools import one, always_iterable
from operator import attrgetter
from .utils import check_tag
from .errors import QueryError, ParseError, only_raise

@autoprop
class ReagentConfig(appcli.Config):
    autoload = True
    autoload_db = True
    db_getter = attrgetter('db')
    tag_getter = attrgetter('tag')
    transform = None

    @autoprop
    class Layer(appcli.Layer):

        def __init__(self, *, db_getter, tag_getter, transform_func, autoload_db):
            self.db_getter = db_getter
            self.tag_getter = tag_getter
            self.transform_func = transform_func
            self.autoload_db = autoload_db
            self.db = None

        def iter_values(self, key, log):
            # First: See if the object has a database attribute.  If it does, 
            # it costs nothing to access it, and it will allow us to log the 
            # path to the database before any subsequent steps fail.

            if self.db:
                log.info("using cached database: {db.name}", db=self.db)

            if self.db is None:
                try:
                    self.db = self.db_getter()
                except AttributeError as err:
                    if not self.autoload_db:
                        log.info("no value found: {err}", err=err)
                        return
                    else:
                        log.info("no database provided: {err}", err=err)
                else:
                    log.info("found database: {db.name}", db=self.db)

            # Second: Make sure we have a tag to look for.
            
            try:
                tag = self.tag_getter()
            except AttributeError as err:
                log.info("no value found: {err}", err=err)
                return
            else:
                log.info("found tag: {tag!r}", tag=tag)

            # Third: Load the database, if necessary.

            if self.db is None:
                from .model import load_db
                self.db = load_db()
                log.info("loaded database: {db.name}", db=self.db)

            # Fourth: Give a useful error message if the tag doesn't match the 
            # expected format.
            
            try:
                check_tag(self.db, tag)
            except ParseError as err:
                log.info("no value found: not a valid FreezerBox tag")
                return

            # Fifth: Lookup the key as an attribute of the selected reagents.

            try:
                reagent = self.db[tag]
            except QueryError:
                log.info("no value found: tag not in database")
                return
            else:
                log.info("found reagent: {reagent!r}", reagent=reagent)

            if self.transform_func:
                try:
                    reagent = self.transform_func(reagent)
                except (QueryError, AttributeError) as err:
                    log.info("no value found: {err}", err=err)
                    return
                else:
                    log.info("called: {transform!r}\nreturned: {reagent}", transform=self.transform_func, reagent=reagent)

            yield from getattr_or_call(reagent, key, log)

    def __init__(self, obj, *,
            autoload_db=None,
            db_getter=None,
            tag_getter=None,
            transform=None,
    ):
        super().__init__(obj)

        self.db_getter = db_getter or unbind_method(self.db_getter) 
        self.tag_getter = tag_getter or unbind_method(self.tag_getter) 
        self.transform = transform or unbind_method(self.transform) 

        self.autoload_db = (
                autoload_db if autoload_db is not None else self.autoload_db)

    def load(self):
        yield self.Layer(
                db_getter=self.get_db,
                tag_getter=self.get_tag,
                transform_func=self.transform,
                autoload_db=self.autoload_db,
        )

    def get_db(self):
        return self.db_getter(self.obj)

    def get_tag(self):
        return self.tag_getter(self.obj)


class DeprecatedReagentConfig:
    autoload = True
    autoload_db = True
    db_getter = lambda obj: obj.db
    tag_getter = lambda obj: obj.tag
    transform = list

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

            if self.db is None:
                try:
                    self.db = self.config.db_getter(self.obj)
                except AttributeError:
                    pass

            # Second: Parse the tags before loading the database.  Loading the 
            # database is expensive, and if the tags won't be in the database 
            # anyways, there's no reason to waste the time.
            
            try:
                tags = self.config.tag_getter(self.obj)
            except AttributeError as err:
                raise KeyError from err

            try:
                for tag in always_iterable(tags):
                    check_tag(tag)
            except ParseError as err:
                raise KeyError from err

            # Third: Load the database.

            if self.db is None and self.config.autoload_db:
                from .model import load_db
                self.db = load_db()

            if self.db is None:
                raise KeyError("no freezerbox database found")

            # Fourth: Lookup the key as an attribute of the selected reagents.

            try:
                values = [
                        key(self.db[x]) if callable(key) else getattr(self.db[x], key)
                        for x in tags
                ]

            except (QueryError, AttributeError) as err:
                raise KeyError from err

            return self.config.transform(values)

        def get_location(self):
            return self.db.name if self.db is not None else "*no database loaded*"

    def __init__(self, tag_getter=None, db_getter=None, autoload_db=None, transform=None):
        cls = self.__class__

        # Access the getter/transform functions through the class.  If accessed 
        # via the instance, they would become bound and would require a self 
        # argument. 

        self.db_getter = db_getter or cls.db_getter
        self.tag_getter = tag_getter or cls.tag_getter
        self.autoload_db = autoload_db if autoload_db is not None else self.autoload_db
        self.transform = transform or cls.transform

    def load(self, obj):
        helper = self.QueryHelper(self, obj)
        yield appcli.Layer(
                values=helper,
                location=helper.get_location,
        )



@autoprop
class ProductConfig(appcli.Config):
    autoload = False
    products_getter = lambda obj: obj.products

    class Layer(appcli.Layer):

        def __init__(self, products_getter):
            self.products_getter = products_getter

        def iter_values(self, key, log):
            try:
                products = self.products_getter()
            except AttributeError as err:
                log.info("no products found: {err}", err=err)
                return

            try:
                product = one(products)
            except ValueError:
                err = QueryError(
                        lambda e: f"expected 1 product, found {len(products)}",
                        products=products,
                )
                raise err from None
            else:
                log.info("found product: {product!r}", product=product)

            yield from self.iter_product_values(product, key, log)

        def iter_product_values(self, product, key, log):
            yield from getattr_or_call(product, key, log)

    def __init__(self, obj, *, products_getter=None):
        super().__init__(obj)
        self.products_getter = \
                products_getter or unbind_method(self.products_getter) 

    def load(self):
        yield self.Layer(self.get_products)

    def get_products(self):
        return self.products_getter(self.obj)


class MakerConfig(ProductConfig):

    class Layer(ProductConfig.Layer):

        def iter_product_values(self, product, key, log):
            dict_layer = appcli.DictLayer(product.maker_args)
            yield from dict_layer.iter_values(key, log)


class PrecursorConfig(ProductConfig):

    class Layer(ProductConfig.Layer):

        def iter_product_values(self, product, key, log):
            precursor = product.precursor
            yield from getattr_or_call(precursor, key, log)

def getattr_or_call(obj, key, log):

    if callable(key):
        try:
            value = key(obj)
        except (QueryError, AttributeError) as err:
            log.info("no value found: {err}", err=err)
            return
        else:
            log.info("called: {key!r}\nreturned: {value!r}", key=key, value=value)

    else:
        try:
            value = getattr(obj, key)
        except (QueryError, AttributeError) as err:
            log.info("no value found: {err}", err=err)
            return
        else:
            log.info("found {key!r}: {value!r}", key=key, value=value)

    yield value

