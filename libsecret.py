import re
import sys
from typing import List, Optional, Tuple, Type, TypeVar

from pydbus import SessionBus


# Important docs:
#   https://github.com/LEW21/pydbus/blob/master/doc/tutorial.rst#accessing-exported-objects
#   https://specifications.freedesktop.org/secret-service/
#
# Maybe in a pinch:
#   https://lazka.github.io/pgi-docs/Secret-1/classes/Collection.html


bus = SessionBus()


def proxy(path=None):
    return bus.get('.secrets',  # aka org.freedesktop.secrets
                   path)


def strip_prefix(subpath: str, path: str) -> str:
    prefix = '/org/freedesktop/secrets/' + subpath
    if not path.startswith(prefix):
        raise RuntimeError('unexpected path: {}'.format(path))
    return path[len(prefix):]


T_Collection = TypeVar('T_Collection', bound='Collection')

class Collection:
    def __init__(self, name: str) -> None:
        self.name = name

    # Keyed by name.
    __cache = {}  # Dict[str, Collection]

    @staticmethod
    def get(name: str) -> 'Collection':
        if name not in Collection.__cache:
            Collection.__cache[name] = Collection(name)
        return Collection.__cache[name]

    @staticmethod
    def by_path(path: str) -> 'Collection':
        return Collection.get(strip_prefix('collection/', path))

    @staticmethod
    def by_alias(alias: str) -> Optional['Collection']:
        return Collection.by_path(proxy().ReadAlias(alias))

    @staticmethod
    def list() -> List['Collection']:
        return [Collection.by_path(path) for path in proxy().Collections]

    def proxy(self):
        return proxy('collection/{}'.format(self.name))

    @property
    def items(self) -> List['Item']:
        return [Item.by_path(path) for path in self.proxy().Items]


T_Item = TypeVar('T_Item', bound='Item')

class Item:
    def __init__(self, collection: Collection, name: str) -> None:
        self.collection = collection
        self.name = name

    # Keyed by (collection_name, name).
    __cache = {}  # Dict[Tuple[str, str], Collection]

    @staticmethod
    def get(collection_name: str, name: str) -> 'Item':
        key = (collection_name, name)
        if key not in Item.__cache:
            Item.__cache[key] = Item(Collection.get(collection_name),
                                      name)
        return Item.__cache[key]

    @staticmethod
    def by_path(path: str) -> 'Item':
        collection_name, name = strip_prefix('collection/', path).split('/', 1)
        return Item.get(collection_name, name)


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


if __name__ == '__main__':
    sys.exit(main())
