#!/usr/bin/env python3

from stepwise import Quantity
from pathlib import Path
from voluptuous import Schema, Optional, Required, All, Any, Coerce
from mako.template import Template
from ..model import REAGENT_CLASSES, Database, Plasmid, find
from ..utils import check_tag, parse_bool
from ..fields import parse_fields, parse_fields_list
from ..errors import LoadError

schema = Schema({
        'format': 'excel',
        Required('reagent'): Any(*REAGENT_CLASSES),
        Required('path'): All(str, Coerce(Path)),
        Optional('worksheet'): str,
        Optional('sequence'): str,
        Optional('tag_template'): str,
        'columns': {str: Any(
            'tag', 'seq', 'molecule', 'synthesis', 'cleanups', 'ready', 'name',
            'alt_names', 'date', 'desc', 'length', 'conc', 'mw', 'circular',
            'resistance', 'antibiotics', 'origin', 'parent_strain', 'plasmids',
        )},
})
default_config = {
        'columns': {
            'Tag': 'tag',
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
            'Resistance': 'resistance',
            'Antibiotics': 'antibiotics',
            'Origin': 'origin',
            'Strain': 'parent_strain',
            'Plasmids': 'plasmids',
        }
}

def load(db, config):
    import pandas as pd
    from warnings import catch_warnings, filterwarnings

    path = config['path']
    sheet = config.get('worksheet', 0)
    reagent = config['reagent']
    columns = config['columns']
    columns_user = {v: k for k, v in columns.items()}
    
    seq_path_template = config.get('sequence')
    reagent_cls = REAGENT_CLASSES[reagent]

    if not path.exists():
        raise LoadError("database not found: {path}", path=path)

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
        df = pd.read_excel(path, sheet_name=sheet)

    df = df.rename(columns=columns)
    df = df.astype(object).where(pd.notnull(df), None)

    def _find_tag(kwargs, config):
        try:
            return kwargs.pop('tag')
        except KeyError:
            pass

        try:
            tag_template = config['tag_template']
        except KeyError:
            err = LoadError(tag_col=columns_user.get('tag', 'tag'))
            err.brief = "reagent must have tag"
            err.blame += "expected to find tag in {tag_col!r} column"
            raise err from None

        try:
            return Template(tag_template).render(i=i, **row)
        except Exception as err1:
            err2 = LoadError(tag_template=tag_template, err=err1)
            err2.brief = "can't create tag from template"
            err2.info += "template: {tag_template}"
            err2.blame += "{err.__class__.__name__}: {err}"
            raise err2 from None

    for i, row in df.iterrows():
        kwargs = {k: v for k, v in row.items() if v is not None}
        if not kwargs:
            continue

        with LoadError.add_info('path: {path}', 'sheet: {sheet}', 'row: {i}', path=path, sheet=sheet, row=row, i=i+1):
            tag = _find_tag(kwargs, config)

        if not kwargs.get('seq') and hasattr(reagent_cls, 'seq'):
            kwargs['seq'] = _defer(
                    _load_seq_from_tag, db, tag, seq_path_template)
        if x := kwargs.get('alt_names'):
            kwargs['alt_names'] = _comma_list(x)
        if x := kwargs.get('conc'):
            kwargs['conc'] = _defer(Quantity.from_string, x)
        if x := kwargs.get('synthesis'):
            kwargs['synthesis'] = _defer(parse_fields, x)
        if x := kwargs.get('cleanups'):
            kwargs['cleanups'] = _defer(parse_fields_list, x)
        if x := kwargs.get('ready'):
            kwargs['ready'] = _defer(parse_bool, x)
        if x := kwargs.get('circular'):
            kwargs['circular'] = _defer(parse_bool, x)
        if x := kwargs.get('resistance'):
            kwargs['resistance'] = _comma_list(x)
        if x := kwargs.get('antibiotics'):
            kwargs['antibiotics'] = _comma_list(x)
        if x := kwargs.get('plasmids'):
            kwargs['plasmids'] = _defer(
                    find, db, _comma_list(x), reagent_cls=Plasmid)

        db[tag] = reagent_cls(**kwargs)

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

def _load_seq_from_tag(db, tag, path_template):
    path = _path_from_tag(db, tag, path_template)
    return _load_seq(path)

def _load_seq(path):
    import autosnapgene as snap

    if not path.exists():
        return

    if path.suffix == '.dna':
        return snap.parse(path).dna_sequence
    if path.suffix == '.prot':
        return snap.parse(path).protein_sequence

    err = LoadError(path=path)
    err.brief = "can't load sequence info from {path.suffix!r} files"
    err.info += "path: {path}"
    raise err

def _path_from_tag(db, tag, path_template):
    path_str = path_template.format(
            tag=tag,
            tag_match=_TagMatch(db, tag),
    )
    return Path(path_str)

def _comma_list(list_str):
    return [x.strip() for x in list_str.split(',')]

class _TagMatch:

    def __init__(self, db, tag):
        self.db = db
        self.tag = tag
        self.match = None

    def __getitem__(self, key):
        # Defer matching the regular expression until we're asked for it, so 
        # that we can raise a useful error message if it doesn't match.
        if not self.match:
            self.match = check_tag(self.db, self.tag)

        return self.match.group(key)

