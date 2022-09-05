#!/usr/bin/env python3

import byoc
import autoprop
import stepwise
import freezerbox
import shlex

from freezerbox import (
        load_maker_plugin, group_by_synthesis, group_by_cleanup,
        iter_combo_makers, group_by_identity,
        join_lists, join_sets, unanimous, only_raise, QueryError, cd,
        parse_volume, parse_conc, parse_bool,
)
from stepwise import Quantity
from natsort import natsort_key
from more_itertools import one, first
from operator import not_
from inform import plural
from os import getcwd
from os.path import expanduser

@autoprop.cache
class Make(byoc.App):
    """\
Display a protocol for making the given reagents.

Usage:
    make <tags>... [-R] [-x <tags>]

Arguments:
    <tags>
        The names of any number of reagents in the FreezerBox database, e.g. 
        p01 or f01.  By default, any other reagents that are needed to make the 
        named reagents and that are marked as "not ready" (e.g. "n", "no", "0" 
        in the "Ready" column) will also be included in the resulting protocol.

Options:
    -R --no-recurse
        Only make the reagents specified on the command line; don't 
        automatically include dependencies that are marked as "not ready" in 
        the database.

    -x --exclude <tags>
        A comma-separated list of tags to exclude from the protocol, i.e. 
        dependencies that would normally be included in the protocol but should 
        be excluded for some idiosyncratic reason.

Protocols are derived from the "Synthesis" and "Cleanups" columns of the 
FreezerBox database.  There is an important distinction between these two 
columns.  The "Synthesis" column is for protocols that actually create new 
reagents.  This most often means creating new sequences.  Examples of such 
protocols include PCR, Gibson or Golden Gate assemblies, restriction digests, 
etc.  In contrast, the "Cleanups" column is for protocols that don't create new 
reagents.  These often relate to things like purification or storage.  Examples 
include minipreps, gel purifications, aliquoting, etc.

Each reagent can only have one synthesis protocol, but can have any number of 
cleanup protocols.  This limit on synthesis protocols ensures that every 
reagent has its own name and can be easily and unambiguously referred to in 
other protocols.

Both columns have the same basic syntax for specifying protocol parameters 
(shown below).  For the "Cleanups" column, multiple protocols can be specified 
by separating several of these specifications with semi-colons (;).

    <protocol> [<value>]... [<key>=<value>]...

The following protocols are currently installed:

<%!
from freezerbox.model import MAKER_PLUGINS
from textwrap import indent
%>\
${indent('\\n'.join(MAKER_PLUGINS), '    ')}

Except for `sw` and `order`, each of these should correspond to a stepwise 
protocol of the same (or similar) name.  Information about the parameters 
expected by each protocol can obtained by running that protocol with the `-h` 
flag, e.g. `sw pcr -h`.  Look for a section in the resulting help text labeled 
"Database".  If you are unsure of a specific protocol's name, it may be helpful 
to get a list of every installed protocol (not all of which can be used in the 
FreezerBox database) by running `sw list`.

`sw` and `order` are built-in protocols available only in FreezerBox.  They do 
not correspond to any stepwise commands, but are documented below:

`sw`
    Create reagents using arbitrary stepwise commands.

        sw <command>... [deps=<tags>] [cwd=<path>] [expt=<id>] [project=<path>] 
            [seq=<seq>] [conc=<conc>] [volume=<vol>] [molecule=<type>]

    <command>
        The arguments to pass to stepwise.  Note that this may need to be 
        quoted if characters such as equals (=), semi-colon (;), backslash (\\), 
        or quotes themselves ('") appear in the command.

    deps=<tags>
        The tags (e.g. p1, f1) of any reagents that must be synthesized before 
        the reagent in question.  If not specified, you may get protocols with 
        steps out of order.

    cwd=<path>
        The directory that should be moved to before executing the protocol 
        command.  If not specified, the command will be executed in the current 
        working directory.  This is useful for commands that are not installed 
        globally.

    expt=<id>
        The id number of an Ex Memo experiment.  If specified, the protocol 
        command will be executed from the directory corresponding to that 
        experiment.  This is basically a more succinct way to specify `cwd`, in 
        the event that you use Ex Memo.

    project=<path>
        The path to the root directory of an Ex Memo project.  This is used in 
        conjunction with the `expt` option described above.  If not specified, 
        the project encompassing the current working directory will be used.

    seq=<seq>
        The sequence of the reagent (if applicable).  This can also be 
        specified in the "Sequence" column.

    conc=<conc>
        The concentration of the reagent (if applicable), including a unit.  
        This can also be specified in the "Sequence" column.

    volume=<vol>
        The concentration of the reagent (if applicable), including a unit.  
        This can also be specified in the "Sequence" column.

    molecule=<molecule>
        What kind of nucleic acid the reagent is (if applicable), e.g. DNA, 
        RNA, ssDNA, dsRNA, etc.

    Unlike protocols with devoted plugins, protocols specified in this way 
    can't be smartly merged into succinct master mixes, because FreezerBox 
    doesn't really understand anything about them.  However, it's still useful 
    to be able to specify arbitrary commands for one-off reagents.  If you find 
    yourself using this protocol a lot, you might want to think about writing a 
    protocol plugin.  

    Note that you cannot pipe commands with this protocol.  If you need one or 
    more pipes, put your commands in a shell script and reference that script 
    from the database.

`order`
    Indicate that a reagent was ordered from a vendor.

        order vendor=<name> [seq=<seq>] [conc=<conc>] [volume=<vol>] 
            [molecule=<type>]

    vendor=<name>
        The name of the company the reagent was ordered from.

    seq=<seq>
        The sequence of the reagent (if applicable).  This can also be 
        specified in the "Sequence" column.

    conc=<conc>
        The concentration of the reagent (if applicable), including a unit.  
        This can also be specified in the "Sequence" column.

    volume=<vol>
        The concentration of the reagent (if applicable), including a unit.  
        This can also be specified in the "Sequence" column.

    molecule=<molecule>
        What kind of nucleic acid the reagent is (if applicable), e.g. DNA, 
        RNA, ssDNA, dsRNA, etc.
"""

    __config__ = [
            byoc.DocoptConfig,
    ]

    tags = byoc.param('<tags>')
    recurse_deps = byoc.param('--no-recurse', cast=not_, default=True)
    exclude_deps = byoc.param('--exclude', cast=lambda x: x.split(','), default=frozenset())

    def __init__(self, db, tags=None):
        self.db = db
        self.tags = tags or []

    def get_protocol(self):
        protocol = stepwise.Protocol()
        targets = collect_targets(
                self.db, self.tags,
                recurse_deps=self.recurse_deps,
                exclude_deps=self.exclude_deps,
        )

        for key, group in group_by_synthesis(targets):
            labels = label_makers(group)

            for makers, protocol_i in iter_protocols(key, group):
                protocol += protocol_i
                if any(getattr(x, 'label_products', True) for x in makers):
                    protocol += label_products(makers, labels)

            parents = [x.parent for x in group]
            for key, subgroup in group_by_cleanup(parents):
                for makers, protocol_i in iter_protocols(key, subgroup):
                    protocol += protocol_i

        return protocol

@autoprop
class StepwiseMaker:

    @classmethod
    def maker_from_reagent(cls, db, reagent):
        maker = cls()
        args = reagent.maker_args

        if 'deps' in args:
            maker.dependencies = {x.strip() for x in args['deps'].split(',')}
        else:
            maker.dependencies = set()

        if 'seq' in args:
            maker.product_seq = args['seq']
        if 'molecule' in args:
            maker.product_molecule = args['molecule']
        if 'volume' in args:
            maker.product_volume = parse_volume(args['volume'])
        if 'conc' in args:
            maker.product_conc = parse_conc(args['conc'])
        if 'circular' in args:
            maker.is_product_circular = parse_bool(args['circular'])
        if '5-phos' in args:
            maker.is_product_phosphorylated_5 = parse_bool(args['5phos'])
        if '3-phos' in args:
            maker.is_product_phosphorylated_3 = parse_bool(args['3phos'])

        if 'cwd' in args:
            cwd = expanduser(args['cwd'])
        elif 'expt' in args:
            import exmemo
            root = expanduser(args.get('project', getcwd()))
            work = exmemo.Workspace.from_path(root)
            expt = work.pick_experiment(args['expt'])
            cwd = expt.root_dir.resolve()
        else:
            cwd = getcwd()

        load_cmd = shlex.join(args.by_index[1:])
        if not load_cmd:
            raise QueryError("no stepwise command specified", culprit=product)

        with cd(cwd):
            maker.protocol = stepwise.load(load_cmd).protocol

        maker.protocol_str = maker.protocol.format_text()

        return maker

    @staticmethod
    def protocols_from_makers(makers):
        for _, group in group_by_identity(makers, lambda x: x.protocol_str):
            yield group, first(group).protocol



@autoprop
class OrderMaker:

    @classmethod
    def maker_from_reagent(cls, db, reagent):
        maker = cls()
        args = reagent.maker_args

        maker.product = reagent
        maker.dependencies = set()
        maker.vendor = args['vendor']
        maker.label_products = False

        if 'seq' in args:
            maker.product_seq = args['seq']
        if 'molecule' in args:
            maker.product_molecule = args['molecule']
        if 'volume' in args:
            maker.product_volume = parse_volume(args['volume'])
        if 'conc' in args:
            maker.product_conc = parse_conc(args['conc'])

        return maker

    @staticmethod
    def protocols_from_makers(makers):
        for vendor, group in group_by_identity(makers, lambda x: x.vendor):
            protocol = stepwise.Protocol()

            if len(group) == 1:
                protocol += f"Order {one(group).product.tag} from {vendor}."
            else:
                protocol += f"Order the following from {vendor}: {', '.join(x.product.tag for x in group)}"

            yield group, protocol


def iter_protocols(key, targets):
    plugin = load_maker_plugin(key)
    makers = [x.maker for x in targets]
    yield from plugin.protocols_from_makers(makers)

def collect_targets(db, tags, recurse_deps=True, exclude_deps=frozenset()):
    # I'm not totally sure that `grouped_topological_sort()` is stable, and if 
    # it's not I'd need to handle sorting differently.  But this approach 
    # passes all the tests I can come up with, so I'm going to run with it 
    # until it becomes a problem.

    def inner_collect(db, tags, recurse_deps, exclude_deps):
        for tag in tags:
            if tag in exclude_deps:
                continue

            target = db[tag]
            yield target

            if recurse_deps:
                try:
                    dep_tags = target.dependencies
                except QueryError:
                    continue

                stale_dep_tags = []
                for tag in dep_tags:
                    try:
                        dep = db[tag]
                    except QueryError:
                        continue
                    
                    if not dep.ready:
                        stale_dep_tags.append(tag)

                yield from inner_collect(
                        db, stale_dep_tags,
                        recurse_deps=recurse_deps,
                        exclude_deps=exclude_deps,
                )

    targets = inner_collect(
            db, tags,
            recurse_deps=recurse_deps,
            exclude_deps=exclude_deps,
    )
    stable_order = {
            str(tag): i
            for i, tag in enumerate(tags)
    }

    # It doesn't really make sense to use `natsorted()` at the moment, because 
    # the tag attribute is basically a tuple to begin with.  But I know that I 
    # want tags to become raw strings in the near future, so using `natsort` is 
    # how this algorithm will eventually need to be written.

    def by_stable_then_natsort(target):
        tag = str(target.tag)
        return (stable_order.get(tag, len(tags)), natsort_key(tag))

    return sorted(targets, key=by_stable_then_natsort)

def label_makers(products):
    return {id(x.maker): x.tag for x in products}

def label_products(makers, labels):
    tags = ', '.join(str(labels[id(x)]) for x in makers)
    return f"Label the {plural(makers):product/s}: {tags}"


if __name__ == '__main__':
    app = Make.from_bare()
    app.db = freezerbox.load_db()
    app.load()
    app.protocol.print()



