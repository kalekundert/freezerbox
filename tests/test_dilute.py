#!/usr/bin/env python3

import freezerbox
import parametrize_from_file
import inform

from stepwise import Q, pl, table, format_text
from freezerbox import Database, parse_fields, parse_fields_list, cd
from freezerbox.stepwise.dilute import *
from schema_helpers import *
from mock_model import *
from pytest import approx
from math import inf

given_expected_error = Schema({
    'given': eval,
     **error_or({
         'expected': eval_with(Stock=Stock, Q=Q, approx=approx),
     }),
})
app_expected_error=Schema({
    'app': exec_with('app', Dilute=Dilute, Stock=Stock, Q=Q),
    **error_or({
        'expected': eval_with(
            Q=Q,
            approx=approx,
            approx_Q=approx_Q,
            pl=pl,
            table=table,
        ),
    }),
})
db_app_expected_error=Schema({
    'db': eval_db,
    **app_expected_error.schema,
})
app_expected_error_stderr=Schema({
    Optional('stderr', default=''): str,
    **app_expected_error.schema,
})

@parametrize_from_file(schema=given_expected_error)
def test_parse_stock(given, expected, error):
    with error, cd(TEST_DIR):
        assert list(parse_stock(given)) == expected

@parametrize_from_file(schema=given_expected_error)
def test_parse_conc(given, expected, error):
    with error:
        assert parse_conc(given) == expected

@parametrize_from_file(schema=given_expected_error)
def test_parse_mw(given, expected, error):
    with error:
        assert parse_mw(given) == expected

@parametrize_from_file(schema=given_expected_error)
def test_parse_volume(given, expected, error):
    with error:
        assert parse_volume(given) == approx(expected)

@parametrize_from_file(schema=db_app_expected_error)
def test_dilute_concs(db, app, expected, error):
    with error:
        app.db = db
        assert app.concs.to_dict('records') == expected

@parametrize_from_file(schema=app_expected_error_stderr)
def test_dilute_dilutions(app, expected, error, stderr, capsys):
    # The default informer has already stored references to `sys.stdout` and 
    # `sys.stderr`, so it won't be affected by `capsys`.  In order to actually 
    # capture these streams, we need to make a new informer within the test.

    # Copied from `stepwise/__init__.py`:
    informer = inform.Inform(stream_policy='header')

    # Don't accidentally use the database present on the testing system.
    app.db = freezerbox.Database()

    with error:
        dilutions = app.dilutions[['stock_uL', 'diluent_uL', 'final_conc']]
        assert dilutions.to_dict('records') == expected

        cap = capsys.readouterr()
        assert stderr in cap.err

    informer.disconnect()

@parametrize_from_file(schema=db_app_expected_error)
def test_dilute_protocol(db, app, expected, error):
    expected['footnotes'] = {
            int(k): v
            for k, v in expected['footnotes'].items()
    }
    app.db = db

    with error:
        p = app.protocol

        print("EXPECTED STEPS")
        print('\n\n'.join(format_text(x, inf) for x in expected['steps']))
        print()
        print("EXPECTED FOOTNOTES")
        print('\n\n'.join(format_text(x, inf) for x in expected['footnotes'].values()))
        print()
        print("ACTUAL")
        print(p.format_text())

        assert p.steps == expected['steps']
        assert p.footnotes == expected['footnotes']

def test_make(mock_plugins):
    db = Database()
    db['x1'] = MockMolecule(
            synthesis=parse_fields('a'),
            cleanups=parse_fields_list('dilute conc=10nM'),
    )
    assert db['x1'].conc_nM == 10

