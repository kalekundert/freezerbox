#!/usr/bin/env python3

import appcli
import autoprop
import stepwise
import freezerbox

from freezerbox import (
        load_maker_factory, group_by_synthesis, group_by_cleanup,
        iter_combo_makers, group_by_identity,
        join_lists, join_sets, unanimous, only_raise, QueryError,
)
from stepwise import Quantity
from more_itertools import one, first
from inform import plural

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

    def __init__(self):
        self.dependencies = set()
        self._product_seqs = []
        self._product_concs = []
        self._product_volumes = []
        self._product_molecules = []

    @classmethod
    def make(cls, db, products):
        yield from iter_combo_makers(
                cls,
                map(cls.from_product, products),
                group_by={
                    '_protocol_str': group_by_identity,
                },
                merge_by={
                    'protocol': first,
                    'dependencies': join_sets,
                    '_product_seqs': join_lists,
                    '_product_concs': join_lists,
                    '_product_volumes': join_lists,
                    '_product_molecules': join_lists,
                }
        )

    @classmethod
    def from_product(cls, product):
        maker = cls()
        args = product.maker_args

        maker.products = [product]

        if 'deps' in args:
            maker.dependencies = {x.strip() for x in args['deps'].split(',')}
        if 'seq' in args:
            maker._product_seqs = [args['seq']]
        if 'conc' in args:
            maker._product_concs = [Quantity.from_string(args['conc'])]
        if 'volume' in args:
            maker._product_volumes = [Quantity.from_string(args['volume'])]
        if 'molecule' in args:
            maker._product_molecules = [args['molecule']]

        load_cmd = ' '.join(args.by_index[1:])
        if not load_cmd:
            raise QueryError("no stepwise command specified", culprit=product)

        maker.protocol = stepwise.load(load_cmd).protocol
        maker._protocol_str = maker.protocol.format_text()

        return maker

    def get_product_seqs(self):
        return self._product_seqs

    @only_raise(QueryError)
    def get_product_conc(self):
        return unanimous(self._product_concs)

    @only_raise(QueryError)
    def get_product_volume(self):
        return unanimous(self._product_volumes)

    @only_raise(QueryError)
    def get_product_molecule(self):
        return unanimous(self._product_molecules)


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



