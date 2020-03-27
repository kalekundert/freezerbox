#!/usr/bin/env python3

import pandas as pd
import autosnapgene as snap
from pathlib import Path
from voluptuous import Required, All, Any, Coerce
from ..model import Database, Tag, Plasmid, Fragment, Oligo
from ..protocols import Protocol
from ..utils import *

schema = {
        'type': 'excel',
        Required('dir'): All(str, Coerce(Path)),
        'columns': {str: Any(
            'seq', 'protocol', 'name', 'alt_names', 'date', 'desc', 
            'length', 'conc', 
        )},
}
default_config = {
        'columns': {
            'Sequence': 'seq',
            'Construction': 'protocol',
            'Name': 'name',
            'Cross-refs': 'alt_names',
            'Date': 'date',
            'Description': 'desc',
            'Length': 'length',
            'Conc': 'conc',
        }
}

def load(config):
    root = config['dir']

    db_xlsx = {
            Plasmid:  root / 'plasmids.xlsx',
            Fragment: root / 'fragments.xlsx',
            Oligo:    root / 'oligos.xlsx',
    }
    seq_dirs = {
            Plasmid:  root / 'plasmids',
            Fragment: root / 'fragments',
            Oligo:    root / 'oligos',
    }

    for dir in seq_dirs.values():
        dir.mkdir(exist_ok=True, parents=True)

    db = Database(str(root))

    for cls, path in db_xlsx.items():
        df = pd.read_excel(path)
        df = df.set_index(df.index + 2)
        df = df.rename(columns=config['columns'])
        df = df.where(pd.notnull(df), None)

        for i, row in df.iterrows():
            tag = Tag(cls.tag_prefix, i)
            kwargs = dict(row)

            if not kwargs.get('seq'):
                kwargs['seq'] = _defer(_seq_from_tag, seq_dirs[cls], tag)
            if x := kwargs.get('alt_names'):
                kwargs['alt_names'] = x.split(',')
            if x := kwargs.get('protocol'):
                kwargs['protocol'] = _defer(Protocol.from_text, db, x)

            db[tag] = cls(**kwargs)

    return db

def _defer(f, *args, **kwargs):
    """
    Create a closure that call the given function with the given arguments.

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
    return lambda: f(*args, **kwargs)

def _seq_from_tag(dir, tag):
    if path := _path_from_tag(dir, tag):
        return snap.parse(path).dna_sequence

def _path_from_tag(dir, tag):
    # Figure out the path to the actual file, allowing for several different 
    # naming conventions.
    for path in dir.iterdir():
        if re.fullmatch(f'({tag.type})?0*{tag.id}([_-].*)?.dna', path.name):
            return path

