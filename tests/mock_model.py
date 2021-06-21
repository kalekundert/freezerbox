#!/usr/bin/env python3

import pytest
import freezerbox
import stepwise

class MockReagent(freezerbox.Reagent):
    tag_prefix = 'x'

class MockMolecule(freezerbox.Molecule):
    tag_prefix = 'x'

    def _calc_mw(self):
        raise freezerbox.QueryError

class MockNucleicAcid(freezerbox.NucleicAcid):
    tag_prefix = 'x'

class MockSoloMaker:

    @classmethod
    def make(cls, db, products):
        yield from (cls(x) for x in products)

    def __init__(self, product):
        args = product.maker_args

        self.products = [product]
        self.dependencies = args.get('deps', [])

        if isinstance(self.dependencies, str):
            self.dependencies = self.dependencies.split(',')

        if 'protocol' in args:
            self.protocol = stepwise.Protocol(steps=args['protocol'])

        # Maker attributes:
        if 'conc' in args:
            self.product_conc = stepwise.Quantity.from_string(args['conc'])

        if 'volume' in args:
            self.product_volume = stepwise.Quantity.from_string(args['volume'])

        # Synthesis attributes:
        if 'seq' in args:
            self.product_seqs = [args['seq']]

        if 'molecule' in args:
            self.product_molecule = args['molecule']

        if 'circular' in args:
            self.is_product_circular = freezerbox.parse_bool(args['circular'])


class MockComboMaker:

    @classmethod
    def make(cls, db, products):
        yield cls(list(products))

    def __init__(self, products):
        from more_itertools import flatten

        steps = list(flatten(
            x.maker_args.get('protocol', [])
            for x in products
        ))
        deps = list(flatten(
            x.maker_args.get('deps', [])
            for x in products
        ))

        self.products = products
        self.protocol = stepwise.Protocol(steps=steps)
        self.dependencies = deps
class MockEntryPoint:

    def __init__(self, plugin):
        self.plugin = plugin

    def load(self):
        return self.plugin

MockMaker = MockSoloMaker

@pytest.fixture
def mock_plugins(monkeypatch):
    from string import ascii_lowercase
    monkeypatch.setattr(freezerbox.model, 'MAKER_PLUGINS', {
        **freezerbox.model.MAKER_PLUGINS,
        'mock': MockEntryPoint(MockSoloMaker),
        'merge': MockEntryPoint(MockComboMaker),
        **{k: MockEntryPoint(MockSoloMaker) for k in ascii_lowercase},
    })

