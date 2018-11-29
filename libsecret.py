import re
import sys
from typing import Any, List, Optional

from pydbus import SessionBus

# Important docs:
#   https://github.com/LEW21/pydbus/blob/master/doc/tutorial.rst#accessing-exported-objects
#   https://specifications.freedesktop.org/secret-service/
#
# Maybe in a pinch:
#   https://lazka.github.io/pgi-docs/Secret-1/classes/Collection.html

bus = SessionBus()

def proxy_object(path=None):
    return bus.get('.secrets',  # aka org.freedesktop.secrets
                   path)

def shorten_collection_name(path: str) -> str:
    return re.sub('^/org/freedesktop/secrets/collection/', '', path)

def get_collections() -> List[str]:
    return [shorten_collection_name(path)
            for path in proxy_object().Collections]

def get_collection_by_alias(name: str) -> str:
    return shorten_collection_name(proxy_object().ReadAlias(name))

def main(argv: List[str]=None):
    if argv is None:
        argv = sys.argv[1:]

    for c in get_collections():
        print(c)
    print()
    for alias in ['default', 'session']:
        print('{} -> {}'.format(alias, get_collection_by_alias(alias)))

if __name__ == '__main__':
    sys.exit(main())
