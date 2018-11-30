import sys
from typing import List

import click

from .core import Collection, PromptDismissedError, proxy


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
    print(c.name)


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