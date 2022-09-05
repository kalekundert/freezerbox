#!/usr/bin/env python3

import pytest
import freezerbox
import stepwise

class MockReagent(freezerbox.Reagent):
    pass

class MockMolecule(freezerbox.Molecule):
    pass

    def _calc_mw(self):
        raise freezerbox.QueryError

class MockNucleicAcid(freezerbox.NucleicAcid):
    pass

class MockMakerPlugin:

    @staticmethod
    def maker_from_reagent(db, reagent):
        from freezerbox import parse_bool

        args = reagent.maker_args

        maker = MockMaker()

        # Initialize attributes that control how the protocol is formatted. 
        # These attributes will only be used in `protocols_from_makers()`:

        maker._steps = args.get('protocol', [])
        maker._merge = args.get('merge', False)

        # Initialize attributes that provide information about the reagent 
        # itself.  These attributes may be read by FreezerBox:

        deps = args.get('deps', [])
        if isinstance(deps, str):
            deps = deps.split(',')
        maker.dependencies = deps

        if 'seq' in args:
            maker.product_seq = args['seq']

        if 'molecule' in args:
            maker.product_molecule = args['molecule']

        if 'conc' in args:
            maker.product_conc = stepwise.Quantity.from_string(args['conc'])

        if 'volume' in args:
            maker.product_volume = stepwise.Quantity.from_string(args['volume'])

        if 'circular' in args:
            maker.is_product_circular = parse_bool(args['circular'])

        if '5phos' in args:
            maker.is_product_phosphorylated_5 = parse_bool(args['5phos'])

        if '3phos' in args:
            maker.is_product_phosphorylated_3 = parse_bool(args['3phos'])

        return maker

    @staticmethod
    def protocols_from_makers(makers):
        from more_itertools import flatten

        # Group the makers based on their *merge* attribute.  The purpose of 
        # this is to make it easy to test different ways of grouping makers.
        groups = {}

        for maker in makers:
            groups.setdefault(maker._merge, []).append(maker)

        ungrouped = groups.pop(False, [])

        for k, group in sorted(groups.items()):
            steps = list(flatten(x._steps for x in group))
            yield group, stepwise.Protocol(steps=steps)

        for maker in ungrouped:
            yield [maker], stepwise.Protocol(steps=maker._steps)

class MockMaker:
    pass

class MockEntryPoint:

    def __init__(self, plugin):
        self.plugin = plugin

    def load(self):
        return self.plugin


@pytest.fixture
def mock_plugins(monkeypatch):
    from string import ascii_lowercase
    monkeypatch.setattr(freezerbox.model, 'MAKER_PLUGINS', {
        **freezerbox.model.MAKER_PLUGINS,
        'mock': MockEntryPoint(MockMakerPlugin),
        **{k: MockEntryPoint(MockMakerPlugin) for k in ascii_lowercase},
    })

