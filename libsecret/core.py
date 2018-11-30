import re
from typing import Any, Callable, List, Optional, Tuple, Type, TypeVar

from gi.repository import GLib
from pydbus import SessionBus, Variant

from .windowid import active_window_id


# Important handy docs on the upstream API are linked in NOTES.
#
# TODO ideas are in NOTES.


class LibsecretError(RuntimeError):
    pass

class PromptDismissedError(LibsecretError):
    pass


bus = SessionBus()


ProxyT = Any

def proxy(path: Optional[str]=None) -> ProxyT:
    return bus.get(
        '.secrets',  # aka org.freedesktop.secrets
        path)        # aka /org/freedesktop/secrets${path:+/$path}


def strip_prefix(subpath: str, path: str) -> str:
    prefix = '/org/freedesktop/secrets/' + subpath
    if not path.startswith(prefix):
        raise RuntimeError('unexpected path: {}'.format(path))
    return path[len(prefix):]


_main_loop = GLib.MainLoop()

def rpc(path: str, invoke: Callable[[ProxyT], None]) -> Tuple:
    result = [None]
    def dbus_cb(_, _1, _2, _3, params) -> None:
        _main_loop.quit()
        result[0] = params
    with bus.subscribe(sender='org.freedesktop.secrets', object=path,
                       # TODO might be good to pin down the other attributes
                       signal_fired=dbus_cb):
        invoke(proxy(path))
        _main_loop.run()
    return result[0]


class Prompt:
    def __init__(self, path: str) -> None:
        self.path = path

    @staticmethod
    def complete(prompt_path: str) -> str:
        window_id = active_window_id()
        dismissed, result = rpc(prompt_path, lambda p: p.Prompt(window_id))
        if dismissed:
            raise PromptDismissedError()
        return result


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

    @staticmethod
    def create(label: str, alias: Optional[str]=None) -> str:
        properties = {'org.freedesktop.Secret.Collection.Label':
                      Variant.new_string(label)}
        path, prompt_path = proxy().CreateCollection(properties, alias or '')
        if path == '/':
            path = Prompt.complete(prompt_path)
        return Collection.by_path(path)

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

    def proxy(self):
        return proxy('collection/{}/{}'.format(
            self.collection.name, self.name))

    @property
    def attributes(self):
        return self.proxy().Attributes
