#!/usr/bin/env python3

import pandas as pd
import autosnapgene as snap
from pathlib import Path
from voluptuous import Required, All, Any, Coerce
from warnings import catch_warnings, filterwarnings
from stepwise import Quantity
from ..model import Database, Tag
from ..model import NucleicAcid, Protein, Buffer, Plasmid, Oligo
from ..fields import parse_fields, parse_fields_list
from ..utils import *

schema = {
        'type': 'excel',
        Required('dir'): All(str, Coerce(Path)),
        'columns': {str: Any(
            'seq', 'molecule', 'synthesis', 'cleanups', 'ready', 'name',
            'alt_names', 'date', 'desc', 'length', 'conc', 'mw', 'circular',
        )},
}
default_config = {
        'columns': {
            'Sequence': 'seq',
            'Molecule': 'molecule',
            'Synthesis': 'synthesis',
            'Cleanups': 'cleanups',
            'Ready': 'ready',
            'Name': 'name',
            'Cross-refs': 'alt_names',
            'Date': 'date',
            'Description': 'desc',
            'Length': 'length',
            'Conc': 'conc',
            'MW': 'mw',
            'Circular': 'circular',
        }
}

def load(config):
    root = config['dir']

    db_xlsx = {
            NucleicAcid: root / 'fragments.xlsx',
            Plasmid:     root / 'plasmids.xlsx',
            Oligo:       root / 'oligos.xlsx',
            Protein:     root / 'proteins.xlsx',
            Buffer:      root / 'buffers.xlsx',
    }
    seq_dirs = {
            NucleicAcid: root / 'fragments',
            Plasmid:     root / 'plasmids',
            Oligo:       root / 'oligos',
            Protein:     root / 'proteins',
    }

    for dir in seq_dirs.values():
        dir.mkdir(exist_ok=True, parents=True)

    db = Database(str(root))

    for cls, path in db_xlsx.items():
        if not path.exists():
            continue

        with catch_warnings():
            filterwarnings(
                    'ignore',
                    category=UserWarning,
                    message="Workbook contains no default style, apply openpyxl's default",
            )
            filterwarnings(
                    'ignore',
                    category=DeprecationWarning,
                    message="`np.float` is a deprecated alias for the builtin `float`.",
            )
            df = pd.read_excel(path)

        df = df.set_index(df.index + 2)
        df = df.rename(columns=config['columns'])
        df = df.astype(object).where(pd.notnull(df), None)

        for i, row in df.iterrows():
            tag = Tag(cls.tag_prefix, i)
            kwargs = {k: v for k, v in row.items() if v is not None}

            if not kwargs.get('seq') and cls is not Buffer:
                kwargs['seq'] = _defer(_seq_from_tag, seq_dirs[cls], tag)
            if x := kwargs.get('alt_names'):
                kwargs['alt_names'] = [y.strip() for y in x.split(',')]
            if x := kwargs.get('conc'):
                kwargs['conc'] = _defer(Quantity.from_string, x)
            if x := kwargs.get('synthesis'):
                kwargs['synthesis'] = _defer(parse_fields, x)
            if x := kwargs.get('cleanups'):
                kwargs['cleanups'] = _defer(parse_fields_list, x)
            if x := kwargs.get('circular'):
                kwargs['circular'] = _defer(parse_bool, x)
            if x := kwargs.get('ready'):
                kwargs['ready'] = _defer(parse_bool, x)

            db[tag] = cls(**kwargs)

    return db

def _defer(f, *args, **kwargs):
    """
    Create a closure that calls the given function with the given arguments.

    The point of this function is to avoid the surprising behavior that can 
    occur if you define a closure in a scope where variables are changing (e.g. 
    in a for-loop).  The confusing thing is that closures have access to the 
    scope they were defined in, but only as it exists when they are ultimately 
    called.  So if the scope changes between when the closure is defined and 
    when it's called, the closure will use the final value of any variables.

    This function serves to create a static local scope containing the 
    variables needed by the closure, which avoids the problem.

    More information: 
    https://stackoverflow.com/questions/10452770/python-lambdas-binding-to-local-values
    """
    class defer:

        def __repr__(self):
            return '<deferred>'

        def __call__(self):
            return f(*args, **kwargs)

    return defer()

def _seq_from_tag(dir, tag):
    if path := _path_from_tag(dir, tag):
        return snap.parse(path).dna_sequence

def _path_from_tag(dir, tag):
    # Figure out the path to the actual file, allowing for several different 
    # naming conventions.
    for path in dir.iterdir():
        if re.fullmatch(f'({tag.type})?0*{tag.id}([_-].*)?.dna', path.name):
            return path

