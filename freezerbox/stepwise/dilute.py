#!/usr/bin/env python3

import stepwise
import freezerbox
import autoprop
import byoc
import pandas as pd

from stepwise import Quantity, pl, oxford_comma
from freezerbox import (
        MakerConfig, QueryError, convert_conc_unit, join_lists,
        iter_combo_makers, group_by_identity, unanimous,
)
from byoc import Key, Method, DocoptConfig
from dataclasses import dataclass
from typing import Callable, Any
from pathlib import Path
from inform import warn, plural

def parse_stocks(stock_strs):
    return join_lists(parse_stock(x) for x in stock_strs)

def parse_stock(stock_str):
    if stock_str:
        path = Path(stock_str)
        if path.exists():
            yield from load_stocks_from_tsv(path)
            return

    fields = stock_str.split(':')

    if len(fields) == 1:
        tag, = fields
        conc = None
        mw = None

    elif len(fields) == 2:
        tag, conc = fields
        conc = parse_conc(conc)
        mw = None

    elif len(fields) == 3:
        tag, conc, mw = fields
        conc = parse_conc(conc)
        mw = parse_mw(mw)

    else:
        raise ValueError(f"expected 1-3 colon-separated fields, got {len(fields)}: {stock_str!r}")

    yield Stock(tag=tag, conc=conc, mw=mw)

def load_stocks_from_tsv(path):
    """
    Load stock concentrations from a TSV file.

    In particular, this function is designed to parse TSV files in the format 
    exported by NanoDrop machines.  Support for other formats can be added on 
    an as-needed basis.
    """
    import csv

    def read_tsv(path, encoding):
        with open(path, newline='', encoding=encoding) as f:
            reader = csv.reader(f, dialect='excel-tab')
            return [x for x in reader]

    try:
        # Nanodrop ONE
        tsv_rows = read_tsv(path, encoding='utf-8')
    except UnicodeDecodeError:
        # Nanodrop 2000/2000c
        tsv_rows = read_tsv(path, encoding='latin-1')

    if len(tsv_rows) < 2:
        raise ValueError(f"stock concentration file doesn't have the expected format.\n- path: {path}\n- expected at least two rows (a header and at least one stock concentration), but only found {len(tsv_rows)}")

    ## Parse the column names:

    @dataclass
    class ColumnSchema:
        headers: list[str]
        required: bool = True
        parse_value: Callable[[str], Any] = str

    @dataclass
    class Column:
        schema: ColumnSchema
        header: str
        index: int

    def conc_ng_uL_from_str(x):
        return Quantity(float(x), 'ng/µL')

    column_schemas = {
            'tag': ColumnSchema(
                headers=['Sample Name', 'Sample ID'],
            ),
            'conc': ColumnSchema(
                headers=['Nucleic Acid(ng/uL)', 'Nucleic Acid'],
                parse_value=conc_ng_uL_from_str,
            ),
            'mw': ColumnSchema(
                headers=['Molecular Weight', 'MW'],
                required=False,
                parse_value=float,
            ),
    }
    column_keys_from_headers = {
            header: key
            for key, schema in column_schemas.items()
            for header in schema.headers
    }

    columns = {}

    for i, header in enumerate(tsv_rows[0]):
        try:
            key = column_keys_from_headers[header]
        except KeyError:
            continue

        if key in columns:
            raise ValueError(f"stock concentration file must not have duplicate columns.\n- path: {path}\n- duplicate columns: {repr(columns[key].header)}, {repr(header)}")

        columns[key] = Column(
                schema=column_schemas[key],
                header=header,
                index=i,
        )

    for key, schema in column_schemas.items():
        if schema.required and key not in columns:
            raise ValueError(f"stock concentration file is missing a required column.\n- path: {path}\nnone of the following columns were found: {', '.join(repr(x) for x in schema.headers)}")
            
    ## Parse the actual stock concentrations:

    num_columns = len(tsv_rows[0])

    for i, row in enumerate(tsv_rows[1:]):
        if len(row) != num_columns:
            raise ValueError(f"every row in the stock concentration file must have the same number of columns as the header\n- path: {path}\n- row {i+2} has {len(row)} columns, expected {num_columns}")

        stock_kwargs = {}

        for key, col in columns.items():
            value_str = row[col.index]
            value = col.schema.parse_value(value_str)
            stock_kwargs[key] = value

        yield Stock(**stock_kwargs)

def parse_conc(conc_str):
    if not conc_str:
        return None

    try:
        conc = float(conc_str)
    except ValueError:
        pass
    else:
        return Quantity(conc, 'ng/µL')

    try:
        return Quantity.from_string(conc_str)
    except ValueError:
        pass

    raise ValueError(f"cannot parse {conc_str!r} as a concentration")

def parse_mw(mw_str):
    if not mw_str:
        return None

    return float(mw_str)

def parse_volume(vol_str):
    volumes = [
            float(v.strip())
            for v in vol_str.split(',')
    ]
    return volumes[0] if len(volumes) == 1 else volumes

@dataclass
class Stock:
    tag: str
    conc: Quantity
    mw: float

    def __init__(self, tag, conc=None, mw=None):
        self.tag = tag
        self.conc = conc
        self.mw = mw

@autoprop
class Dilute(byoc.App):
    """\
Calculate dilutions.

Usage:
    dilute <stocks>... (-v <µL> | -D <µL> | -V <µL>) [-c <conc>] [-C <conc>] 
        [-w <Da>] [-d <name>]

Arguments:
    <stocks>
        A list of stock solutions to dilute.  Any number of stocks can be 
        specified, and each argument can take one of two forms:

        Colon-separated fields:
            Specify the name and, if necessary, the concentration and molecular 
            weight for a single stock solution:

                <name>[:<conc>[:<mw>]]

            If either of the optional parameters aren't specified, they will be 
            looked up in the FreezerBox database using the given name.  Note 
            that the molecular weight is only required for certain unit 
            conversions, e.g. ng/µL to nM.  The name can be empty (or not in 
            the database) so long as enough information to calculate the 
            dilutions is supplied on the command-line.

        Path to existing TSV file:
            Read names, concentrations, and molecular weights for any number of 
            stock solutions from the given TSV file.  Information is read from 
            the following columns (any other columns are ignored):

            name:               "Sample Name" or "Sample ID"
            concentration:      "Nucleic Acid(ng/uL)" or "Nucleic Acid"
            molecular weight:   "Molecular Weight" or "MW"

            These column names are intended to match the files exported by 
            NanoDrop ONE and NanoDrop 2000 spectrophotometers, although it's 
            certainly possible to make these files yourself.

Options:
    -c --conc <conc>
        The final concentration achieve after dilution.  If not specified, 
        concentrations will be queried from the FreezerBox database.

    -C --stock-conc <conc>
        The stock concentration to use in the dilution calculations.  This 
        option will override any concentrations specified in the FreezerBox 
        database, but not any specified by the <stocks> argument.

    -v --volume <uL>
        The volume of concentrated stock solution to use in each dilution.  
        This can either be a single value or a comma-separated list of values.  
        If a single value is given, that value will be used for each dilution.  
        If multiple values are given, there must be exactly one value for each 
        stock solution, and the values will be associated with the stock 
        solutions in the order they were given.

    -D --diluent-volume <uL>
        The volume of diluent to use in each dilution.  This can either be a 
        single value or a comma-separated list of values, see the `--volume` 
        option for details.

    -V --total-volume <µL>
        The combined volume of stock and diluent to reach after each dilution.  
        This can either be a single value or a comma-separated list of values, 
        see the `--volume` option for details.

    --mw <Da>
        The molecular weight to use in the dilution calculations, e.g. if 
        converting between ng/µL and nM.  This option will override any 
        molecular weights specified in the FreezerBox database, but not any 
        specified by the <stocks> argument.

    -d --diluent <name>
        The name of the diluent to use.

Database:
    Dilution protocols can appear in the "Cleanup" column of a FreezerBox 
    database:

        dilute [conc=<conc>] [diluent=<name>]

    conc=<conc>
        See --conc.

        This setting is automatically applied as the concentration of the 
        associated database entry, unless superseded by the "Concentration" 
        column or a later cleanup step.  In other words, this concentration may 
        be used by any protocol that queries the FreezerBox database.

        Often, a concentration specified by this setting is regarded as the 
        "desired concentration", with the "actual concentration" being given in 
        the "Concentration" column in the event that the desired concentration 
        cannot be reached.

    diluent=<name>
        See --diluent.

"""
    __config__ = [
            DocoptConfig,
            MakerConfig,
    ]

    stocks = byoc.param(
            Key(DocoptConfig, '<stocks>', cast=parse_stocks),
            Method(lambda self: [Stock(self.product.tag, None, None)]),
    )
    target_conc = byoc.param(
            Key(DocoptConfig, '--conc'),
            Key(MakerConfig, 'conc'),
            cast=parse_conc,
            default=None,
    )
    stock_conc = byoc.param(
            Key(DocoptConfig, '--stock-conc'),
            cast=parse_conc,
            default=None,
    )
    stock_volume_uL = byoc.param(
            Key(DocoptConfig, '--volume'),
            cast=parse_volume,
            default=None,
    )
    diluent_volume_uL = byoc.param(
            Key(DocoptConfig, '--diluent-volume'),
            cast=parse_volume,
            default=None,
    )
    target_volume_uL = byoc.param(
            Key(DocoptConfig, '--total-volume'),
            cast=parse_volume,
            default=None,
    )
    mw = byoc.param(
            Key(DocoptConfig, '--mw'),
            cast=parse_mw,
            default=None,
    )
    diluent = byoc.param(
            Key(DocoptConfig, '--diluent'),
            Key(MakerConfig, 'diluent'),
            default=None,
    )
    show_stub = byoc.param(
            default=False,
    )

    def __bareinit__(self):
        self._db = None

    def __init__(self, stocks):
        self.stocks = stocks

    @classmethod
    def maker_from_reagent(cls, db, reagent):
        app = cls.from_bare()
        app.db = db
        app.product = reagent
        app.load(MakerConfig)
        return app

    @classmethod
    def protocols_from_makers(cls, makers):
        # This plugin implementation is directly ported from the original 
        # `make()` interface and is no longer idiomatic.

        def factory():
            app = cls.from_bare()
            app.db = db
            app.show_stub = True
            return app

        for maker in iter_combo_makers(
                    factory,
                    map(cls.from_product, products),
                    group_by={
                        'target_conc': group_by_identity,
                        'diluent': group_by_identity,
                    },
            ):
            yield maker.products, maker.protocol

    def get_db(self):
        if self._db is None:
            self._db = freezerbox.load_db()
        return self._db

    def set_db(self, db):
        self._db = db

    def get_concs(self):
        rows = []

        def first_valid(*options, strict=True, error=ValueError):
            for option in options:
                if callable(option):
                    try:
                        return option()
                    except (QueryError, AttributeError):
                        continue

                if option is not None:
                    return option

            if strict:
                raise error
            else:
                return None

        for stock in self.stocks:
            rows.append(row := {})
            row['tag'] = tag = stock.tag
            row['target_conc'] = first_valid(
                    self.target_conc,
                    lambda: self.db[tag].conc,
                    error=ValueError(f"{tag}: no target concentration specified"),
            )
            row['stock_conc'] = first_valid(
                    stock.conc,
                    self.stock_conc,
                    lambda: self.db[tag].conc,
                    error=ValueError(f"{tag}: no stock concentration specified"),
            )
            row['mw'] = first_valid(
                    stock.mw,
                    self.mw,
                    lambda: self.db[tag].mw,
                    strict=False,
            )
            row['stock_conc_converted'] = convert_conc_unit(
                    row['stock_conc'],
                    row['mw'],
                    row['target_conc'].unit,
            )

        return pd.DataFrame(rows)

    def get_dilutions(self):
        self._check_volumes()

        df = self.concs
        k = df['stock_conc_converted'] / df['target_conc']
        dont_calc = (k <= 1)
        k[dont_calc] = pd.NA  # Avoid dividing by zero.

        if uL := self.stock_volume_uL:
            df['stock_uL'] = uL
            df['diluent_uL'] = uL * (k - 1)

        elif uL := self.diluent_volume_uL:
            df['diluent_uL'] = uL
            df['stock_uL'] = uL / (k - 1)
            uL = 'any'

        elif uL := self.target_volume_uL:
            df['stock_uL'] = uL / k
            df['diluent_uL'] = uL - df['stock_uL']

        df['final_conc'] = df['target_conc']
        df.loc[dont_calc, 'final_conc'] = df.loc[dont_calc, 'stock_conc_converted']
        df.loc[dont_calc, 'stock_uL'] = uL
        df.loc[dont_calc, 'diluent_uL'] = 0

        df['too_dilute'] = df['target_conc'] != df['final_conc']
        if df['too_dilute'].any():
            tags = df['tag'][df['too_dilute']]
            warn(f"the following {plural(tags):/stock is/stocks are} too dilute: {', '.join(tags)}")

        return df

    def get_protocol(self):
        if self.show_stub:
            return self.stub_protocol
        else:
            return self.full_protocol

    def get_stub_protocol(self):
        tags = [x.tag for x in self.stocks]
        in_diluent = f' in {self.diluent}' if self.diluent else ''

        p = stepwise.Protocol()
        p += f"Dilute {oxford_comma(tags)} to {self.target_conc}{in_diluent}."
        return p

    def get_full_protocol(self):
        df = self.dilutions
        uL = lambda x: x if isinstance(x, str) else f'{x:.2f} µL'

        ## Main table:

        main_header = [
                "Name",
                "Stock Vol",
                "Diluent Vol",
        ]
        main_row = lambda x: [
                x['tag'],
                uL(x['stock_uL']),
                uL(x['diluent_uL']),
        ]
        main_align = '<>>'

        to_conc = ""
        in_diluent = ""

        try:
            target_conc = unanimous(df['target_conc'])
        except ValueError:
            show_conc = True
        else:
            show_conc = False
            to_conc = f"to {target_conc} "

        if self.diluent:
            in_diluent = f"in {self.diluent} "

        if show_conc or df['too_dilute'].any():
            main_header.append("Final Conc")
            main_row_3 = main_row
            main_row = lambda x: [
                    *main_row_3(x),
                    str(x['final_conc']),
            ]
            main_align += '>'

        main_table = stepwise.table(
                rows=[main_row(x) for _, x in df.iterrows()],
                header=main_header,
                align=main_align,
        )

        ## Supplementary table:

        def stock_str(row):
            c0, c1 = row['stock_conc'], row['stock_conc_converted']
            return f'{c0} = {c1}' if c0.unit != c1.unit else f'{c1}'

        def mw_str(row):
            mw = row['mw']
            return f'{mw:.1f}' if mw else '?'

        supp_table = stepwise.table(
                rows=[
                    [x['tag'], mw_str(x), stock_str(x), x['target_conc']]
                    for _, x in df.iterrows()
                ],
                header=['Name', 'MW', 'Stock Conc', 'Target Conc'],
                align='<>>>',
        )

        ## Protocol:

        p = stepwise.Protocol()
        p += pl(
                f"Dilute the following {plural(df):stock solution/s} {to_conc}{in_diluent}[1]:",
                main_table,
        )
        p.footnotes[1] = pl(
                "Concentrations:",
                supp_table,
        )
        return p

    def get_product_conc(self):
        return self.target_conc

    def _check_volumes(self):
        volumes = [
                ('stock volume', self.stock_volume_uL),
                ('diluent volume', self.diluent_volume_uL),
                ('target volume', self.target_volume_uL),
        ]
        given = [k for k, v in volumes if v]
        if len(given) == 0:
            raise ValueError("no volumes specified")
        if len(given) > 1:
            raise ValueError(f"specified {' and '.join(given)}")

if __name__ == '__main__':
    app = Dilute.from_bare()
    app.load(DocoptConfig)
    app.protocol.print()

