#!/usr/bin/env python3

"""\
Query the DNA database.

Usage:
    po4 check [<db>]
    po4 which

Commands:
    check:  Make sure everything in the current database makes sense.
    which:  List the available databases.

Arguments:
    <db>
        The name of a database to use.  This corresponds to the "use" setting 
        in the configuration files.  If not given, the default database for the 
        current working directory will be used.
"""

import docopt
from tqdm import tqdm
from .. import load_config, load_db, CheckError

def main():
    args = docopt.docopt(__doc__)

    if args['check']:
        check(args['<db>'])

    if args['which']:
        which()

def check(use=None):
    db = load_db(use)
    n_total = len(db)
    n_passed = 0

    for tag, construct in tqdm(db.items()):
        try:
            construct.check()
            n_passed += 1
        except CheckError as err:
            err.report()

    print(f"{n_total} sequences found.")
    print(f"{n_passed} passed all checks.")

def which():
    config = load_config()

    if 'use' not in config:
        print("No default database.")
    else:
        print(f"Default database: {config['use']!r}")

    print()

    if 'database' not in config:
        print("No available databases.")
    else:
        print("Available databases:")
        for db in config['database']:
            print(f"  {db!r} ({config['database'][db]['type']})")



