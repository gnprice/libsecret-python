import sys
from typing import List

from .core import Collection


def main(argv: List[str]=None):
    if argv is None:
        argv = sys.argv[1:]

    for c in Collection.list():
        print(c.name)

    print()
    for alias in ['default', 'session']:
        print('{} -> {}'.format(alias, Collection.by_alias(alias).name))

    print()
    items = Collection.get('login').items
    print('{} items; a few:'.format(len(items)))
    for item in items[:3]:
        print('  {}'.format(item.name))
