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

GIB: Gibson assembly
    bb: backbone plasmid (required)
    ins: comma-separated list of inserts (required)
"""

import sys, re, shlex
import stepwise
import autoprop
from itertools import groupby
from subprocess import run
from statistics import mean
from numbers import Real
from more_itertools import one
from inform import Inform, Error, warn
from po4.model import load_db
from po4.protocols import *
from po4.errors import UsageError, QueryError

@autoprop
class Make:

    def __init__(self, db, tags=None, options=None):
        self.db = db
        self.tags = tags or []
        self.options = options or []

    def get_protocol(self):
        self._protocol = stepwise.Protocol()

        factories = {
                PcrProtocol:        self._make_pcr_command,
                InversePcrProtocol: self._make_inverse_pcr_command,
                DigestProtocol:     self._make_digest_command,
                AnnealProtocol:     self._make_anneal_command,
                GoldenGateProtocol: self._make_golden_gate_command,
                GibsonProtocol:     self._make_gibson_command,
                LigateProtocol:     self._make_ligate_command,
                IvtProtocol:        self._make_ivt_command,
        }

        constructs = [self.db[x] for x in self.tags]
        by_protocol_type = lambda x: type(x.protocol)

        for key, group in groupby(constructs, key=by_protocol_type):
            group = list(group)
            make_command = factories.get(key, lambda x:
                    warn(f"{key.name!r} protocols are not yet supported"))
            make_command(group)

        if not self._protocol:
            raise UsageError("no protocols found")

        return self._protocol

    def _make_pcr_command(self, constructs, cmd='pcr'):
        protocols = [x.protocol for x in constructs]

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

        self._add_command(constructs, [
                cmd,
                join(x.template_tag for x in protocols),
                join(x.primer_tags[0] for x in protocols),
                join(x.primer_tags[1] for x in protocols),
                '-a', join(str_sig(x.annealing_temp_C) for x in protocols),
                '-x', str(max(int(x.extension_time_s) for x in protocols)),
                *get_num_rxns_flag(constructs),
                *get_master_mix_flag(),
                *get_volume_flag(constructs),
        ])

    def _make_inverse_pcr_command(self, constructs):
        self._make_pcr_command(constructs, cmd='invpcr')

    def _make_ivt_command(self, constructs):
        protocols = [x.protocol for x in constructs]
        
        def get_short_flag():
            transcript_lens = (len(x.product_seq) for x in protocols)
            return ['-s'] if all(x <= 300 for x in transcript_lens) else []

        return self._add_command(constructs, [
                'ivt',
                *(x.template_tag for x in protocols),
                *get_short_flag(),
        ])

    def _make_digest_command(self, constructs):
        for enz, group in groupby(constructs, key=lambda x: x.protocol.enzymes):
            group = list(group)
            self._add_command(group, [
                    'digest',
                    join(x.protocol.template_tag for x in group),
                    join(enz),
            ])

    def _make_anneal_command(self, constructs):
        protocols = [x.protocol for x in constructs]

        def get_conc_flag():
            return get_unanimous_flag(
                    '-c', constructs, lambda x: x.conc_uM,
                    "reactions have different oligo concentrations",
            )

        def get_stock_conc_flag():
            return get_unanimous_flag(
                    '-C', constructs, lambda x: x.stock_uM,
                    "reactions have different oligo stock concentrations",
            )

        def get_master_mix_flag():
            if len(protocols) == 1:
                return []

            master_mix = []
            for i in range(2):
                unique_oligos = set(x.oligo_tags[i] for x in protocols)
                if len(unique_oligos) == 1:
                    master_mix.append(str(i+1))

            return ['-m', ','.join(master_mix)] if master_mix else []

        self._add_command(constructs, [
                'anneal',
                join(x.oligo_tags[0] for x in protocols),
                join(x.oligo_tags[1] for x in protocols),
                *get_num_rxns_flag(constructs),
                *get_volume_flag(constructs),
                *get_conc_flag(),
                *get_stock_conc_flag(),
                *get_master_mix_flag(),
        ])

    def _make_assembly_command(self, constructs, cmd, flags=()):
        protocols = [x.protocol for x in constructs]

        def fragment_from_tags(tags):
            def get_conc_str(tag):
                try:
                    conc = self.db[tag].conc_str
                    return re.sub(r'\s*ng/[µu]L$', '', conc)
                except QueryError:
                    return '50'

            def mean_if_similar(x, too_diff):
                if min(x) < 0.5 * max(x): raise too_diff
                return mean(x)

            def tabulate(x):
                from textwrap import indent
                from tabulate import tabulate
                return indent(
                        tabulate(x.items(), tablefmt='plain'),
                        '    ',
                )

            name = join(tags)

            concs = {
                    x: get_conc_str(x)
                    for x in tags
            }
            conc = one(
                    set(concs.values()),
                    too_long=UsageError(f"fragments have different concentrations:\n{tabulate(concs)}"),
            )

            # If the concentration happens to be in moles, we don't need to 
            # worry about the lengths of the fragments.  A bit hacky.
            if conc.endswith('M'):
                return f'{name}:{conc}'

            lengths = {
                    x: self.db[x].length
                    for x in tags
            }
            length = mean_if_similar(
                    lengths.values(),
                    too_diff=UsageError(f"fragments have concentrations in ng/µL and lengths that differ by more than 50%:\n{tabulate(lengths)}"),
            )

            return f'{name}:{conc}:{length}'

        def fragment_names():
            from itertools import count
            yield 'bb'
            for i in count(1):
                yield str(i)

        num_inserts = one(
                {len(x.insert_tags) for x in protocols},
                too_long=UsageError("all assemblies must have the same number of inserts"),
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

        def get_master_mix_flag():
            master_mix = []
            for name, tags in zip(fragment_names(), tag_groups):
                if len(set(tags)) == 1:
                    master_mix.append(name)

            if master_mix and len(protocols) > 1:
                return ['-m', ','.join(master_mix)]
            else:
                return []

        stepwise_cmd = [
                cmd,
                *fragments,
                *get_num_rxns_flag(constructs),
                *get_volume_flag(constructs),
                *get_master_mix_flag(),
                *flags
        ]

        self._add_command(constructs, stepwise_cmd)

    def _make_golden_gate_command(self, constructs):
        self._make_assembly_command(
                constructs,
                cmd='golden_gate',
                flags=[
                    *get_unanimous_flag('-e', constructs, lambda x: x.enzyme, "assemblies use different enzymes"),
                ],
        )

    def _make_gibson_command(self, constructs):
        self._make_assembly_command(
                constructs,
                cmd='gibson',
        )

    def _make_ligate_command(self, constructs):
        protocols = [x.protocol for x in constructs]

        def get_kinase_flag():
            use_kinase = any(x.use_kinase for x in protocols)
            return ['-k'] if use_kinase else []

        self._make_assembly_command(
                constructs,
                cmd='ligate',
                flags=[
                    *get_kinase_flag(),
                ],
        )

    def _add_command(self, constructs, cmd):
        assert constructs
        assert cmd

        self._protocol += stepwise.load([*cmd, *self.options])

        label = f"Label the {plural(constructs):product/s}:"
        tags = ','.join(str(x.tag) for x in constructs)
        step = f'{label} {tags}'

        self._protocol += step if len(step) < 49 else f'{label}\n{tags}'

def join(items):
    items = list(items)
    if len(set(items)) == 1:
        return items[0]
    else:
        return ','.join(items)

def str_sig(value):
    return str(float(value)).strip('0').rstrip('.')


def get_volume_flag(constructs):
    return get_unanimous_flag(
            '-v',
            constructs,
            lambda x: x.volume_uL,
            "reactions have different volumes"
    )

def get_num_rxns_flag(constructs, default=1):
    n = len(constructs)
    return ['-n', str(n)] if n != default else []

def get_unanimous_flag(flag, constructs, value_getter, error):
    value = get_unanimous_value(constructs, value_getter, error)
    value_str = str_sig(value) if isinstance(value, Real) else str(value)
    return [flag, value_str] if value else []

def get_unanimous_value(constructs, value_getter, error):
    return one(
            {value_getter(x.protocol) for x in constructs},
            too_long=UsageError(f"{error}: {','.join(repr(x.tag) for x in constructs)}"),
    )


if __name__ == '__main__':
    import docopt

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
        print(make.protocol)
    except Error as err:
        err.report()
