#!/usr/bin/env python3

"""\
Display a protocol for making the given fragment.

Usage:
    make <tag>... [--] [<options>...]

Arguments:
    <tag>
        The name of a plasmid or fragment in the database, e.g. p01 or f01.

    <options>
        Options that will be passed directly to all protocols invoked.

The protocol is parsed from the "Construction" column of these tables.  The 
syntax for a protocol is:

    <method>: [<key>=<value> ]...

The following methods are currently understood:

PCR: Polymerase chain reaction
    template: name of template (required)
    primers: forward and reverse primers, separated by a comma (required)
    Ta: annealing temperature (default: derived from primers)
    tx: extension time (default: derived from product length)
    scale: volume of the reaction (default: 10 µL)

INV: Inverse PCR
    Same as for PCR.

RE: Restriction enzyme digest
    template: name of template (required)
    enzyme: name of enzyme, must be sold by NEB (required)

IVT: In vitro transcription
    template: name of DNA template (required)

GG: Golden gate assembly
    bb: backbone plasmid (required)
    ins: comma-separated list of inserts (required)
    enzyme: Type IIS enzyme (default: BsaI)
"""

import sys, re
import shlex
from itertools import groupby
from subprocess import run
from statistics import mean
from more_itertools import one
from inform import Inform, Error, warn
from po4.model import load_db
from po4.protocols import *
from po4.errors import UsageError, QueryError

class Make:

    def __init__(self, db, tags=None, options=None):
        self.db = db
        self.tags = tags or []
        self.options = options or []
        self.stepwise_commands = []

    def run(self):
        self._make_commands()
        stepwise_pipeline = ' | '.join(
                shlex.join(x)
                for x in self.stepwise_commands
        )
        run(stepwise_pipeline, shell=True)

    def _make_commands(self):
        self.stepwise_commands = []

        factories = {
                PcrProtocol:        self._make_pcr_command,
                InversePcrProtocol: self._make_inverse_pcr_command,
                DigestProtocol:     self._make_digest_command,
                IvtProtocol:        self._make_ivt_command,
                GoldenGateProtocol: self._make_golden_gate_command,
        }

        constructs = [self.db[x] for x in self.tags]
        by_protocol_type = lambda x: type(x.protocol)

        for key, group in groupby(constructs, key=by_protocol_type):
            group = list(group)
            make_command = factories.get(key, lambda x:
                    warn(f"{key.name!r} protocols are not yet supported"))
            make_command(group)

        if not self.stepwise_commands:
            raise UsageError("no protocols found")

    def _make_pcr_command(self, constructs, cmd='pcr'):
        protocols = [x.protocol for x in constructs]

        def get_volume_flag():
            volume_uL = one(
                    {x.volume_uL for x in protocols},
                    too_long=UsageError(f"PCR reactions have different scales: {','.join(repr(x.tag) for x in constructs)}"),
            )
            return ['-v', str_sig(volume_uL)] if volume_uL else []

        def get_master_mix_flag():
            all_reagents = {'dna', 'primers'}
            master_mix = set(all_reagents)
            num_templates = len({x.template_tag for x in protocols})
            num_primers = len({x.primer_tags for x in protocols})

            if num_templates > 1:
                master_mix.discard('dna')
            if num_primers > 1:
                master_mix.discard('primers')

            if master_mix == all_reagents:
                return []
            if not master_mix:
                return ['-M']

            return ['-m', ','.join(master_mix)]

        self._add_command([
                cmd,
                join(x.template_tag for x in protocols),
                join(x.primer_tags[0] for x in protocols),
                join(x.primer_tags[1] for x in protocols),
                str(len(protocols)),
                join(str_sig(x.annealing_temp_C) for x in protocols),
                str(max(int(x.extension_time_s) for x in protocols)),
                *get_master_mix_flag(),
                *get_volume_flag(),
        ])

    def _make_inverse_pcr_command(self, constructs):
        self._make_pcr_command(constructs, cmd='invpcr')

    def _make_ivt_command(self, constructs):
        return self._add_command([
                'ivt',
                str(len(constructs)),
        ])

    def _make_digest_command(self, constructs):
        protocols = [x.protocol for x in constructs]

        for enz, group in groupby(protocols, key=lambda x: x.enzymes):
            self._add_command([
                    'digest',
                    join(x.template_tag for x in protocols),
                    join(enz),
            ])

    def _make_golden_gate_command(self, constructs):
        protocols = [x.protocol for x in constructs]

        def fragment_from_tags(tags):
            def get_conc(tag):
                try:
                    conc = self.db[tag].conc_str
                    return re.sub(r'\s*ng/[µu]L$', '', conc)
                except QueryError:
                    return '50'

            def tabulate(x):
                from textwrap import indent
                from tabulate import tabulate
                return indent(
                        tabulate(x.items(), tablefmt='plain'),
                        '    ',
                )

            name = join(tags)

            concs = {
                    x: get_conc(x)
                    for x in tags
            }
            conc = one(
                    set(concs.values()),
                    too_long=UsageError(f"inserts have different concentrations:\n{tabulate(concs)}"),
            )

            lengths = {
                    x: self.db[x].length
                    for x in tags
            }
            if min(lengths.values()) > 0.5 * max(lengths.values()):
                length = int(mean(lengths.values()))
            else:
                raise UsageError(f"inserts have lengths that differ by more than 50%:\n{tabulate(lengths)}")

            return f'{name}:{conc}:{length}'

        def fragment_names():
            from itertools import count
            yield 'bb'
            for i in count(1):
                yield str(i)

        num_inserts = one(
                {len(x.insert_tags) for x in protocols},
                too_long=UsageError("All golden gate assemblies must have the same number of inserts"),
        )
        tag_groups = [
                [x.backbone_tag for x in protocols]
        ] + [
                [x.insert_tags[i] for x in protocols]
                for i in range(num_inserts)
        ]
        fragments = [
                fragment_from_tags(x)
                for x in tag_groups
        ]

        master_mix = []
        for name, tags in zip(fragment_names(), tag_groups):
            if len(set(tags)) == 1:
                master_mix.append(name)

        stepwise_cmd = [
                'golden_gate',
                *fragments,
                '-e', join(x.enzyme for x in protocols),
        ]
        if (n := len(protocols)) > 1:
            stepwise_cmd += [
                '-n', str(n),
            ]
            if not master_mix:
                stepwise_cmd += ['-M']
            elif len(master_mix) < len(fragments):
                stepwise_cmd += ['-m', ','.join(master_mix)]


        self._add_command(stepwise_cmd)

    def _add_command(self, cmd):
        stepwise_cmd = ['stepwise', *cmd, *self.options]
        self.stepwise_commands.append(stepwise_cmd)

def join(items):
    items = list(items)
    if len(set(items)) == 1:
        return items[0]
    else:
        return ','.join(items)

def str_sig(value):
    return str(float(value)).strip('0').rstrip('.')


if __name__ == '__main__':
    import docopt
    Inform(stream_policy='header')

    try: 
        i = sys.argv.index('--')
        args = docopt.docopt(__doc__, sys.argv[1:i])
        args['<options>'] = sys.argv[i:][1:]
    except ValueError:
        args = docopt.docopt(__doc__)
        args['<options>'] = []

    db = load_db()
    make = Make(db)
    make.tags = args['<tag>']
    make.options = args['<options>']

    try:
        make.run()
    except Error as err:
        err.report()
