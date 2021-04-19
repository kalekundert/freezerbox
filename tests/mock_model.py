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
    def make(cls, intermediates):
        yield from (cls(x) for x in intermediates)

    def __init__(self, product):
        args = product.maker_args

        self.products = [product]

        if 'protocol' in args:
            self.protocol = stepwise.Protocol(steps=args['protocol'])

        if 'deps' in args:
            self.dependencies = args['deps']
        else:
            self.dependencies = []

        if 'seq' in args:
            self.product_seqs = [args['seq']]

        if 'molecule' in args:
            self.product_molecule = args['molecule']

        if 'conc' in args:
            self.product_conc = stepwise.Quantity.from_string(args['conc'])

        if 'circular' in args:
            self.is_product_circular = freezerbox.parse_bool(args['circular'])


class MockComboMaker:

    @classmethod
    def make(cls, intermediates):
        yield cls(list(intermediates))

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

MockMaker = MockSoloMaker
