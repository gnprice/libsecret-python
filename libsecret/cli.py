import sys
from typing import List

import click

from .core import Collection


@click.group()
def main():
    pass


@main.group()
def collection():
    pass


@collection.command(name='list')
def collection_list():
    for c in Collection.list():
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
