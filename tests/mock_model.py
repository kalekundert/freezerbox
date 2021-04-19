#!/usr/bin/env python3

import pytest
import freezerbox

class MockReagent(freezerbox.Reagent):
    tag_prefix = 'x'

class MockMolecule(freezerbox.Molecule):
    tag_prefix = 'x'

    def _calc_mw(self):
        raise QueryError

class MockNucleicAcid(freezerbox.NucleicAcid):
    tag_prefix = 'x'

class MockMaker:

    @classmethod
    def make(cls, intermediates):
        yield from (MockMaker(x) for x in intermediates)

    def __init__(self, product):
        args = product.maker_args

        self.products = [product]

        if 'seq' in args:
            self.product_seqs = [args['seq']]

        if 'molecule' in args:
            self.product_molecule = args['molecule']

        if 'conc' in args:
            self.product_conc = Quantity.from_string(args['conc'])

        if 'circular' in args:
            self.is_product_circular = args['circular']

        if 'deps' in args:
            self.dependencies = args['deps']
        else:
            self.dependencies = []

@pytest.fixture(autouse=True)
def monkeypatch_maker_plugins(monkeypatch):
    from string import ascii_lowercase
    monkeypatch.setattr(freezerbox.model, 'MAKER_PLUGINS', {
        k: MockMaker for k in ascii_lowercase
    })


