#!/usr/bin/env python3

import appcli
import autoprop
import stepwise
import freezerbox

from inform import plural
from freezerbox.group_by import group_by_synthesis, group_by_cleanup
from freezerbox.model import load_maker_factory
from stepwise import Quantity
from more_itertools import one

@autoprop
class Make(appcli.App):
    """\
Display a protocol for making the given reagents.

Usage:
    make <tag>...

Arguments:
    <tag>
        The name of a reagent in the freezerbox database, e.g. p01 or f01.
"""

    __config__ = [
            appcli.DocoptConfig(),
    ]

    tags = appcli.param('<tag>')

    def __init__(self, db, tags=None):
        self.db = db
        self.tags = tags or []

    def get_protocol(self):
        protocol = stepwise.Protocol()
        products = [self.db[x] for x in self.tags]

        for key, group in group_by_synthesis(products):
            for maker in iter_makers(self.db, key, group):
                protocol += maker.protocol
                if getattr(maker, 'label_products', True):
                    protocol += label_products(maker.products)

            parents = [x.parent for x in group]
            for key, subgroup in group_by_cleanup(parents):
                for maker in iter_makers(self.db, key, subgroup):
                    protocol += maker.protocol

        return protocol

@autoprop
class StepwiseMaker:

    @classmethod
    def make(cls, db, products):
        yield from map(cls.from_product, products)

    @classmethod
    def from_product(cls, product):
        maker = cls()
        args = product.maker_args

        maker.products = [product]
        maker.dependencies = set()
        maker.load_cmd = ' '.join(args.by_index[1:])

        if 'seq' in args:
            maker.product_seqs = [args['seq']]
        if 'deps' in args:
            maker.dependencies = {x.strip() for x in args['deps'].split(',')}
        if 'conc' in args:
            maker.product_conc = Quantity.from_string(args['conc'])
        if 'volume' in args:
            maker.product_volume = Quantity.from_string(args['volume'])
        if 'molecule' in args:
            maker.product_molecule = args['molecule']

        return maker

    def get_protocol(self):
        return stepwise.load(self.load_cmd)


@autoprop
class OrderMaker:

    @classmethod
    def make(cls, db, products):
        yield from map(cls.from_product, products)

    @classmethod
    def from_product(cls, product):
        maker = cls()
        args = product.maker_args

        maker.products = [product]
        maker.dependencies = set()
        maker.vendor = args['vendor']
        maker.label_products = False

        if 'seq' in args:
            maker.product_seqs = [args['seq']]
        if 'conc' in args:
            maker.product_conc = Quantity.from_string(args['conc'])
        if 'volume' in args:
            maker.product_volume = Quantity.from_string(args['volume'])
        if 'molecule' in args:
            maker.product_molecule = args['molecule']

        return maker

    def get_protocol(self):
        p = stepwise.Protocol()
        p += f"Order {one(self.products).tag} from {self.vendor}."
        return p

def iter_makers(db, key, products):
    factory = load_maker_factory(key)
    yield from factory(db, products)

def label_products(products):
    tags = ', '.join(str(x.tag) for x in products)
    return f"Label the {plural(products):product/s}: {tags}"

if __name__ == '__main__':
    app = Make.from_params()
    app.db = freezerbox.load_db()
    app.load()
    app.protocol.print()



