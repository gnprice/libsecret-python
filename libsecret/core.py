from contextlib import contextmanager
import re
from typing import Any, Callable, List, Optional, Tuple, Type, TypeVar

from gi.repository import Gio, GLib
from pydbus import SessionBus, Variant

from .windowid import active_window_id


# Important handy docs on the upstream API are linked in NOTES.
#
# TODO ideas are in NOTES.


class LibsecretError(RuntimeError):
    pass

class NotFoundError(LibsecretError):
    pass

class BadObjectPathError(LibsecretError):
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
        raise BadObjectPathError('unexpected path: {}'.format(path))
    return path[len(prefix):]


@contextmanager
def expect_error(domain: str, code: 'gobject.GEnum', fmt: str='Server error: {}'):
    try:
        yield
    except GLib.GError as e:
        # Background doc:
        #   https://developer.gnome.org/glib/stable/glib-Error-Reporting.html
        # Errors have a domain, a code, and a message.
        #
        # When the error gets to us here in Python, it looks like
        #    e.domain == 'g-dbus-error-quark'
        #    e.code == 7
        #    e.message == ("GDBus.Error:org.freedesktop.DBus.Error.NotSupported:"
        #                 +" Only the 'default' alias is supported")
        #
        # "Quark" basically means enum; see:
        #    https://developer.gnome.org/glib/stable/glib-Quarks.html
        # So this is "error 7 in the GDBus error enum".  And indeed,
        #    Gio.DBusError(7) == Gio.DBusError.NOT_SUPPORTED
        #
        # Awkward that the domain and code have been effectively
        # pre-stuffed into the message.  I believe this is DBus's doing,
        # and that this is why the C API docs say to call g_dbus_error_strip_remote_error:
        #    https://developer.gnome.org/gio/stable/gio-GDBusError.html
        # But Gio.DBusError.strip_remote_error seems to have no effect;
        # perhaps because it's written as a mutator, and the bindings
        # let it mutate a throwaway copy.
        if e.domain == domain and e.code == code:
            # Cf g_dbus_error_strip_remote_error:
            #   https://gitlab.gnome.org/GNOME/glib/blob/2.56.1/gio/gdbuserror.c#L760
            # (thanks, "source" link in the lazka.github.io PyGObject docs!)
            message = re.sub('^ .*? : .*? : \ ', '', e.message, flags=re.X)
            raise LibsecretError(message) from None
        raise    


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
        path = proxy().ReadAlias(alias)
        if path == '/':
            raise NotFoundError()
        return Collection.by_path(path)

    @staticmethod
    def list() -> List['Collection']:
        return [Collection.by_path(path) for path in proxy().Collections]

    @staticmethod
    def create(label: str, alias: Optional[str]=None) -> str:
        properties = {'org.freedesktop.Secret.Collection.Label':
                      Variant.new_string(label)}
        # gnome-keyring can raise this, with "Only the 'default' alias is supported".
        with expect_error('g-dbus-error-quark', Gio.DBusError.NOT_SUPPORTED):
            path, prompt_path = proxy().CreateCollection(properties, alias or '')
        if path == '/':
            path = Prompt.complete(prompt_path)
        return Collection.by_path(path)

    def proxy(self):
        return proxy('collection/{}'.format(self.name))

    @property
    def items(self) -> List['Item']:
        return [Item.by_path(path) for path in self.proxy().Items]

    def delete(self) -> None:
        try:
            prompt_path = self.proxy().Delete()
        except KeyError:
            raise NotFoundError() from None
        if prompt_path != '/':
            Prompt.complete(prompt_path)


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
