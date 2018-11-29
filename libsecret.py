import sys
from typing import Any, List, Optional

import gi
gi.require_version('Secret', '1')
from gi.repository import Secret

# Important docs:
#   https://specifications.freedesktop.org/secret-service/
#   https://lazka.github.io/pgi-docs/Secret-1/classes/Collection.html

Collection = Any

def get_service():
    return Secret.Service.get_sync(Secret.ServiceFlags.NONE)

def get_collections() -> List[Collection]:
    s = get_service()
    s.load_collections_sync()
    return s.get_collections()

def collection_for_alias(name: str) -> Optional[Collection]:
    return Secret.Collection.for_alias_sync(
        get_service(), name, Secret.CollectionFlags.NONE)

def main(argv: List[str]=None):
    if argv is None:
        argv = sys.argv[1:]

    for c in get_collections():
        print(repr(c.get_label()))

if __name__ == '__main__':
    sys.exit(main())
