import re
import sys
from typing import List, Optional, Type, TypeVar

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

    @classmethod
    def by_path(cls: Type[T_Collection], path: str) -> T_Collection:
        return cls(strip_prefix('collection/', path))

    @classmethod
    def by_alias(cls: Type[T_Collection], alias: str) -> Optional[T_Collection]:
        return cls.by_path(proxy().ReadAlias(alias))

    @classmethod
    def list(cls: Type[T_Collection]) -> List[T_Collection]:
        return [cls.by_path(path) for path in proxy().Collections]


def main(argv: List[str]=None):
    if argv is None:
        argv = sys.argv[1:]

    for c in Collection.list():
        print(c.name)
    print()
    for alias in ['default', 'session']:
        print('{} -> {}'.format(alias, Collection.by_alias(alias).name))


if __name__ == '__main__':
    sys.exit(main())
