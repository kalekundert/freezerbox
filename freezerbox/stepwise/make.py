#!/usr/bin/env python3

import appcli
import autoprop
import stepwise

from inform import plural
from ..group_by import group_by_synthesis, group_by_cleanup
from ..model import load_maker_factory

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
            for maker in iter_makers(key, group):
                protocol += maker.protocol
                protocol += label_products(maker.products)

            parents = [x.parent for x in group]
            for key, subgroup in group_by_cleanup(parents):
                for maker in iter_makers(key, subgroup):
                    protocol += maker.protocol

        return protocol

def iter_makers(key, targets):
    factory = load_maker_factory(key)
    yield from factory(targets)

def label_products(products):
    tags = ', '.join(str(x.tag) for x in products)
    return f"Label the {plural(products):product/s}: {tags}"

if __name__ == '__main__':
    app = Make.from_params()
    app.db = load_db()
    app.load()
    app.protocol.print()



