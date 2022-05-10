#!/usr/bin/env python3

import byoc
import autoprop

from byoc import unbind_method
from more_itertools import one, always_iterable
from operator import attrgetter
from .utils import check_tag
from .errors import QueryError, ParseError, LoadError, only_raise

@autoprop
class ReagentConfig(byoc.Config):
    """
    Provide access to the `Reagent` object identified by the tag attribute of 
    the object making use of this config.
    """
    autoload = True
    autoload_db = True
    db_getter = attrgetter('db')
    tag_getter = attrgetter('tag')
    reagent_cls = None
    transform = None

    @autoprop
    class Layer(byoc.Layer):

        def __init__(self, *, db_getter, tag_getter, reagent_cls, transform_func, autoload_db):
            self.db_getter = db_getter
            self.tag_getter = tag_getter
            self.reagent_cls = reagent_cls
            self.transform_func = transform_func
            self.autoload_db = autoload_db
            self.db = None

        def iter_values(self, key, log):
            # See if the object has a database attribute.  If it does, it costs 
            # nothing to access it, and it will allow us to log the path to the 
            # database before any subsequent steps fail.

            if self.db:
                log.info(f"using cached database: {self.db.name}")

            if self.db is None:
                try:
                    self.db = self.db_getter()
                except AttributeError as err:
                    if not self.autoload_db:
                        log.info(f"no value found: {err}")
                        return
                    else:
                        log.info(f"no database provided: {err}")
                except LoadError as err:
                    log.info(f"failed to load database: {err}")
                    return
                else:
                    log.info(f"found database: {self.db.name}")

            # Make sure we have a tag to look for.
            
            try:
                tag = self.tag_getter()
            except AttributeError as err:
                log.info(f"no value found: {err}")
                return
            else:
                log.info(f"found tag: {tag!r}")

            # Load the database, if necessary.

            if self.db is None:
                from .model import load_db
                try:
                    self.db = load_db()
                except LoadError as err:
                    log.info(f"failed to load database: {err}")
                    return
                else:
                    log.info(f"loaded database: {self.db.name}")

            # Give a useful error message if the tag doesn't match the expected 
            # format.
            
            try:
                check_tag(self.db, tag)
            except ParseError as err:
                log.info("no value found: not a valid FreezerBox tag")
                return

            # Find the reagent:

            try:
                reagent = self.db[tag]
            except QueryError:
                log.info("no value found: tag not in database")
                return
            else:
                log.info(f"found reagent: {reagent!r}")

            # Make sure the reagent is of the expected type.

            if self.reagent_cls and not isinstance(reagent, self.reagent_cls):
                log.info(f"expected {self.reagent_cls.__name__}, got {type(reagent).__name__}")
                return

            # Let subclasses customize the value that gets yielded.

            if self.transform_func:
                try:
                    reagent = self.transform_func(reagent)
                except (QueryError, AttributeError) as err:
                    log.info(f"no value found: {err}")
                    return
                else:
                    log.info(f"called: {self.transform_func!r}\nreturned: {reagent}")

            yield from getattr_or_call(reagent, key, log)

    def __init__(self, obj, *,
            autoload_db=None,
            db_getter=None,
            tag_getter=None,
            reagent_cls=None,
            transform=None,
    ):
        super().__init__(obj)

        self.db_getter = db_getter or unbind_method(self.db_getter) 
        self.tag_getter = tag_getter or unbind_method(self.tag_getter) 
        self.reagent_cls = reagent_cls or self.reagent_cls
        self.transform = transform or unbind_method(self.transform) 

        self.autoload_db = (
                autoload_db if autoload_db is not None else self.autoload_db)

    def load(self):
        yield self.Layer(
                db_getter=self.get_db,
                tag_getter=self.get_tag,
                reagent_cls=self.reagent_cls,
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
        yield byoc.Layer(
                values=helper,
                location=helper.get_location,
        )



@autoprop
class BaseProductConfig(byoc.Config):
    autoload = False
    products_getter = lambda obj: obj.products
    reagent_cls = None

    class Layer(byoc.Layer):

        def __init__(self, *, products_getter, reagent_cls):
            self.products_getter = products_getter
            self.reagent_cls = reagent_cls

        def iter_values(self, key, log):
            # Get the products for this maker.

            try:
                products = self.products_getter()
            except AttributeError as err:
                log.info(f"no products found: {err}")
                return

            # Require that there is only a single product.

            try:
                product = one(products)
            except ValueError:
                err = QueryError(
                        lambda e: f"expected 1 product, found {len(e.products)}",
                        products=products,
                )
                raise err from None
            else:
                log.info(f"found product: {product!r}")

            # Make sure the product is of the expected type.

            if self.reagent_cls and not isinstance(product, self.reagent_cls):
                log.info(f"expected {self.reagent_cls.__name__}, got {type(product).__name__}")
                return

            yield from self.iter_product_values(product, key, log)

        def iter_product_values(self, product, key, log):
            raise NotImplementedError

    def __init__(self, obj, *, products_getter=None, reagent_cls=None):
        super().__init__(obj)
        self.products_getter = \
                products_getter or unbind_method(self.products_getter) 
        self.reagent_cls = reagent_cls or self.reagent_cls

    def load(self):
        yield self.Layer(
                products_getter=self.get_products,
                reagent_cls=self.reagent_cls,
        )

    def get_products(self):
        return self.products_getter(self.obj)


class ProductConfig(BaseProductConfig):
    """
    Provide access to the `Reagent` object representing the product of a maker.
    """

    class Layer(BaseProductConfig.Layer):

        def iter_product_values(self, product, key, log):
            yield from getattr_or_call(product, key, log)


class MakerConfig(BaseProductConfig):
    """
    Provide access to the information in the "synthesis" or "cleanup" column of 
    the database for a reagent.

    This is a more convenient but less powerful version of `BaseProductConfig`.
    """

    class Layer(BaseProductConfig.Layer):

        def iter_product_values(self, product, key, log):
            dict_layer = byoc.DictLayer(product.maker_args)
            yield from dict_layer.iter_values(key, log)


class PrecursorConfig(BaseProductConfig):

    class Layer(BaseProductConfig.Layer):

        def iter_product_values(self, product, key, log):
            precursor = product.precursor
            yield from getattr_or_call(precursor, key, log)

def getattr_or_call(obj, key, log):

    if callable(key):
        try:
            value = key(obj)
        except (QueryError, AttributeError) as err:
            log += f"no value found: {err}"
            return
        else:
            log += lambda: f"called: {key!r}\nreturned: {safe_repr(value)}"

    else:
        try:
            value = getattr(obj, key)
        except (QueryError, AttributeError) as err:
            log += f"no value found: {err}"
            return
        else:
            log += lambda: f"found {key!r}: {safe_repr(value)}"

    yield value

def safe_repr(obj):
    try:
        return repr(obj)
    except Exception as err:
        return f'{obj.__class__.__name__}() <repr failed: {err}>'
