#!/usr/bin/env python3

"""\
Query the DNA database.

Usage:
    po4 query <tags>... [--attrs <list>]
    po4 check [<db>]
    po4 which

Commands:
    query:  Display information about of the given constructs.
    check:  Make sure everything in the current database makes sense.
    which:  List the available databases.

Options:
    -a --attrs <list>      [default: seq]
        A comma-separated list of attributes to display.

Arguments:
    <tags>
        One or more tags to search for in the database.

    <db>
        The name of a database to use.  This corresponds to the "use" setting 
        in the configuration files.  If not given, the default database for the 
        current working directory will be used.
"""

import docopt
from tqdm import tqdm
from po4 import load_config, load_db, CheckError, QueryError

def main():
    args = docopt.docopt(__doc__)

    if args['query']:
        seq(args['<tags>'], args['--attrs'].split(','))

    if args['check']:
        check(args['<db>'])

    if args['which']:
        which()

def seq(tags, attrs):
    db = load_db()

    print('\t'.join(['tag', *attrs]))

    for tag in tags:
        try:
            hit = db[tag]
        except QueryError:
            print(tag)
            continue

        row = []
        for attr in attrs:
            try:
                row.append(getattr(hit, attr))
            except (QueryError, AttributeError):
                row.append('')

        print('\t'.join(str(x) for x in [hit.tag, *row]))

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



