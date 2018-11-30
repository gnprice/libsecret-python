import sys
from typing import List

import click

from .core import Collection, proxy
from .core import LibsecretError, NotFoundError, PromptDismissedError


@click.group()
def main():
    pass


@main.command()
@click.argument('path', required=False)
def introspect(path):
    try:
        print(proxy(path).Introspect())
    except KeyError:
        sys.exit(1)


@main.group()
def collection():
    pass


@collection.command(name='list')
def collection_list():
    for c in Collection.list():
        print(c.name)


@collection.command(name='create')
@click.argument('label')
@click.argument('alias', required=False)
def collection_create(label, alias):
    try:
        c = Collection.create(label, alias)
    except PromptDismissedError:
        raise click.ClickException('Prompt dismissed')
    except LibsecretError as e:
        raise click.ClickException(e.args[0])
    print(c.name)


@collection.command(name='delete')
@click.option('-i', '--interactive', flag_value='i', default=True)
@click.option('-f', '--force', 'interactive', flag_value='')
@click.argument('names', nargs=-1)
@click.pass_context
def collection_delete(ctx, interactive, names):
    if not names:
        return
    # Using actual True/False for flag_value misbehaves; winds up always False!
    if bool(interactive):
        info_fullname = '{} {} {}'.format(
            ctx.parent.parent.info_name, ctx.parent.info_name, ctx.info_name)
        question = '\n'.join([
            '{}:'.format(info_fullname),
            '  {}'.format(' '.join(names)),
            'Really delete these collections?'])
        if not click.confirm(question):
            click.echo('Nothing deleted.')
            return
    for name in names:
        collection_delete_one(name)

def collection_delete_one(name):
    try:
        Collection.get(name).delete()
    except NotFoundError:
        raise click.ClickException('No such collection: {}'.format(name))


@main.group()
def alias():
    pass


@alias.command(name='get')
@click.argument('name')
def alias_get(name):
    print(Collection.by_alias(name).name)


@main.command()
@click.option('--collection')
def search(collection):
    if collection is None:
        # later, this is one of several alternatives
        raise click.UsageError('search requires --collection')

    items = Collection.get(collection).items
    for item in items:
        print(item.name)
