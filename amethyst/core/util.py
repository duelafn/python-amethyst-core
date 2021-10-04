# -*- coding: utf-8 -*-
"""

"""
# SPDX-License-Identifier: LGPL-3.0

__all__ = """
cached_property
coalesce
dict_of
get_class
identity
list_of
set_of
smartmatch
tupley
""".split()

import importlib
import inspect
import re
import threading
import types

_NOT_FOUND = object()


def identity(x):
    """The identity function, returns its (single) argument"""
    return x


# Dumb container for python 2 support in list_of() and dict_of()
class _Container(object):
    pass

def list_of(conv, container=list, package=None, frame=1):
    """
    An :py:class:`amethyst.core.obj.Attr` helper function which will
    validate a list of values. Sample usage::

        class MyObject(Object):
            foo = Attr(list_of(float))

        obj = MyObject(foo="23")
        print(obj.foo)            # [ 23 ]        -  a list with an int

        obj.foo = (1, 2, "23")
        print(obj.foo)            # [ 1, 2, 23 ]  -  a list not a tuple


    :param conv: The conversion function or class. If a class, objects in
    the list which are not already objects of this class will be inflated
    using the class. If passed a string, it will be converted to a class
    (or function) using the :py:func:`get_class` function.

    :param container: Constructor which can take a generator and return
    your desired list-like object. For instance, the :py:func:`set_of`
    function passes `container=set`.

    :param package: String or package object to use as the base for
    relative imports. When specified, is passed unmodified to
    :py:func:`get_class`.

    :param frame: Frame depth, as described in :py:func:`get_class`.

    """
    c = _Container()  # Closure variable for python 2 support (don't have "nonlocal")
    if frame and package is None and not callable(conv) and (conv.startswith('.') or '.' not in conv):
        package = inspect.getmodule(inspect.stack()[frame][0])

    def wrapper(thingun):
        # May not pre-compute these to allow list_of("Foo") to be called
        # within the declaration of the Foo class.
        if not getattr(c, 'initialized', False):
            c.initialized = True
            c.conv = conv if callable(conv) else get_class(conv, package=package, frame=None)
            c.conv_is_type = isinstance(c.conv, type)
        return container(
            (x if c.conv_is_type and isinstance(x, c.conv) else c.conv(x))
            for x in tupley(thingun)
        )
    return wrapper


def set_of(conv, package=None, frame=1):
    """
    Like :py:func:`list_of`, but uses a set container rather than a list
    container.
    """
    return list_of(conv, container=set, frame=frame+1)


def dict_of(conv, key_conv=identity, set_key=None, package=None, frame=1):
    """
    An :py:class:`amethyst.core.obj.Attr` helper function which will
    validate a dict of values and optionally keys. Sample usage::

        class MyObject(Object):
            name = Attr()
            foo = Attr(dict_of("MyObject"))

        obj1 = MyObject(name="Alice")
        obj2 = MyObject(foo={ "a": obj1, "b": dict(name="Bob") })

    In the example, ``obj2.foo`` will be a dictionary with two items. Both
    values will be MyObject objects, the "b" item having been auto-inflated.

    .. WARNING::
       The produced attribute value is a normal python dict. Automatic
       inflation only occurs when initially setting the attribute. Normal
       accesses to the attribute dictionary will not validate or
       auto-inflate. For instance, ``obj2.foo["c"] = dict(name="Carol")``
       will store a python dict to key "c", not a MyObject.

    :param conv: The conversion function or class. If a class, values in
    the dict which are not already objects of this class will be inflated
    using the class. If passed a string, it will be converted to a class
    (or function) using the :py:func:`get_class` function.

    :param key_conv: Conversion function for keys, defaults to identity
    function.

    :param set_key: Optional callable passed key name and inflated value
    object. Can be used to set an attribute on the value objects based on
    keys. For instance, we might use ``set_key=lambda k, v: setattr(v,
    "name", v.name or k)`` to set default "name" attributes.

    :param package: String or package object to use as the base for
    relative imports. When specified, is passed unmodified to
    :py:func:`get_class`.

    :param frame: Frame depth, as described in :py:func:`get_class`.

    """
    c = _Container()  # Closure variable for python 2 support (don't have "nonlocal")
    if package is None and (
            (not callable(conv) and (conv.startswith('.') or '.' not in conv))
         or (not callable(key_conv) and (key_conv.startswith('.') or '.' not in key_conv))
    ):
        package = inspect.getmodule(inspect.stack()[frame][0])

    def wrapper(d):
        # May not pre-compute these to allow list_of("Foo") to be called
        # within the declaration of the Foo class.
        if not getattr(c, 'initialized', False):
            c.initialized = True
            c.conv = conv if callable(conv) else get_class(conv, package=package, frame=None)
            c.conv_is_type = isinstance(c.conv, type)
            c.key_conv = key_conv if callable(key_conv) else get_class(key_conv, package=package, frame=None)
            c.key_conv_is_type = isinstance(c.key_conv, type)

        rv = dict()
        for k, v in d.items():
            key = k if c.key_conv_is_type and isinstance(k, c.key_conv) else c.key_conv(k)
            val = v if c.conv_is_type and isinstance(v, c.conv) else c.conv(v)
            if set_key:
                set_key(key, val)
            rv[key] = val
        return rv

    return wrapper


def get_class(name, package=None, frame=1):
    """
    Load a class (or function or other package attribute) from a string
    name. Automatically imports required package. Requested name may be
    relative. If relative and no package is passed, the call stack is
    examined at the frame counter and imports are relative to that package.

    ::

       get_class("foo.Bar")                     # Bar class from package foo
       get_class(".Foo")  or  get_class("Foo")  # Foo class from current package
       get_class(".Foo", frame=2)               # Foo class from caller's package

    :param str name: A string containing a package name and class or object
    name joined by a dot. The package will be loaded and the attribute will
    be returned. From the name of the function, the intention if for
    automatic loading of classes. For example,
    `get_class("amethyst.core.Object")`, however, python doesn't really
    distinguish between loading a class and loading a function or other
    package variable, so the object after the last dot can really be
    anything available in the package -- even unrelated imports to the
    package! For this reason, if classes or packages are imported for user
    or configuration input, it is a good idea to verify that the imported
    object matches some expected base class.

    :param package: String or package object to use as the base for
    relative imports.

    :param frame: Frame depth, for the default base package. When set to 1,
    relative class names are looked up relative to the caller's package.
    When set to a larger value, will look up relative to the caller's
    caller's ... package. Set to 0 or None (or set an explicit value for
    *package* to disable automatically selecting a base package.

    """
    # Rewrite "Foo" as ".Foo"
    if '.' not in name:
        name = '.' + name

    # Split out module and object name
    mod = name[0:name.rindex(".")]
    cls = name[len(mod)+1:]
    pkg = package if isinstance(package, types.ModuleType) else None
    # if name is ".Foo" or "..Foo" we should not have stripped off a "."
    if mod in ('', '.'):
        mod = mod + '.'

    # Inspect stack and get calling package if relative name
    if frame and package is None and name.startswith('.') or '.' not in name:
        try:
            pkg = inspect.getmodule(inspect.stack()[frame][0])
        except Exception:
            pass

    # Special case for ".Foo", we got the package directly
    if mod == '.' and pkg:
        pass
    else:
        if pkg and (package is None or isinstance(package, types.ModuleType)):
            package = pkg.__name__
        pkg = importlib.import_module(mod, package)
    return getattr(pkg, cls)


def tupley(thingun):
    """
    Make sure thingun is like a tuple - a list, set, tuple. If not, wraps
    thingun into a single-item or empty (when None) tuple.
    """
    if thingun is None:
        return ()
    if isinstance(thingun, (list, tuple, set, frozenset)):
        return thingun
    return (thingun,)


def coalesce(*args):
    """
    Returns first argument which is not `None`. If no non-None argumenst,
    then will return `None`. Also returns `None` if argument list is empty.
    """
    for x in args:
        if x is not None:
            return x
    return None


RE_TYPE = type(re.compile("^$"))
NONE_TYPE = type(None)
def smartmatch(val, other):
    """
    Smart match against a value

    Convenient function to use in attribute validation. Attempts to
    determine if a value is like other values. Behavior depends on type of
    the other object:

    * `list`, `tuple`, `set`, `frozenset`: Test membership and return the value
      unmodified.

    * `dict`: Look up the item and return the hashed value.

    * compiled `regex`: call ``other.search(val)``. Remember to anchor your
      search if that is desired!

    * `callable`: call ``other(val)`` and return the result

    * `type`, `NoneType`: Test ``val is other`` and, if true, return value

    * anything else: Test ``val == other`` and, if true, return value

    If none of the above match, raises a :py:exc:`ValueError`
    """
    if isinstance(other, (list, tuple, set, frozenset)):
        if val in other:
            return val

    elif isinstance(other, dict):
        if val in other:
            return other[val]

    elif isinstance(other, RE_TYPE):
        if other.search(val):
            return val

    elif callable(other):
        return other(val)

    elif isinstance(other, (type, NONE_TYPE)):
        if val is other:
            return val

    elif val == other:
        return val

    raise ValueError("Invalid Value")


class cached_property(object):
    """
    Lazy Attribute Memoization

    .. NOTE:: functools in python 3.8 includes a cached_property decorator.
    It should be used in place of this for most cases.

    Creates properties with deferred calculation. Once calculated, the
    result is stored and returned from cache on subsequent access. Useful
    for expensive operations which may not be needed, or to ensure
    just-in-time construction (I like using this for database connections
    or building subwidgets in GUI classes, see examples below).

    Decorator Usage (most common)::

        class Foo(object):
            @cached_property
            def bar(self):
                print("Computing...")
                return 42   # or expensive_calculation()

        foo = Foo()

        print(foo.bar)      # Computing...  42
        print(foo.bar)      # 42

        foo.bar = 12
        print(foo.bar)      # 12

        del foo.bar         # Clears the cache
        print(foo.bar)      # Computing...  42

    Direct use allows calculation to be closure or dynamically chosen.
    The bar attribute will behave the same as above::

        class Foo(object):
            def __init__(self, **kwargs):
                def expensive_calculation():
                    ...

                self.bar = cached_property(expensive_calculation, "bar")


    Example: Automatic, thread-safe, database connections::

        import threading
        import sqlite3
        from amethyst.core import cached_property

        class MyObject(object):
            def __init__(self, **kwargs):
                self._thr_local = threading.local()

            @cached_property(delegate="_thr_local")
            def db(self):
                conn = sqlite3.connect("mydb.sqlite3")
                conn.execute("PRAGMA foreign_keys=ON")
                return conn

        # obj.db will be a different connection in each thread
        # and will only connect if used in the thread


    Example: GUI widget building::

        import wx
        from amethyst.core import cached_property as widget

        class SimpleWindow(wx.Frame):
            def __init__(self, *args, **kwargs):
                super(SimpleWindow, self).__init__(*args, **kwargs)
                self.sizer.Add(self.button1)
                self.sizer.Add(self.button_exit)

            @widget
            def sizer(self):
                widget = wx.BoxSizer(wx.VERTICAL)
                self.SetSizer(widget)
                return widget

            @widget
            def button1(self):
                widget = wx.Button(self, wx.ID_ANY, "Do Something")
                widget.Bind(wx.EVT_BUTTON, self.on_click1)
                return widget

            @widget
            def button_exit(self):
                widget = wx.Button(self, wx.ID_ANY, "Exit")
                widget.Bind(wx.EVT_BUTTON, lambda evt: wx.Exit())
                return widget

            def on_click1(self, evt):
                print("Ouch!")

        class MyApp(wx.App):
            def OnInit(self):
                self.mainwindow.Show(True)
                self.SetTopWindow(self.mainwindow)
                return True

            @widget
            def mainwindow(self):
                return SimpleWindow(None, -1, "This is a test")

        app = MyApp(0)
        app.MainLoop()
    """
    def __init__(self, meth=None, name=None, delegate=None):
        """
        :param meth: The method being decorated. Typically not passed to
           the constructor explicitly, see examples.

        :param name: Key name to use in object dict (or delegate attribute
           name). Automatically extracted from decorated method name if not
           specified.

        :param delegate: Attribute name containing an object to delegate
           storage to. If not `None`, the `name` attribute of `delegate`
           will be accessed (via `getattr`, `setattr`, and `delattr`) when
           determining whether to recompute the cached property and to
           store the computed property value (see example).

        .. NOTE:: If you aren't using the name or delegate options and can
        depend on python >= 3.8, the core functools package includes a
        cached_property decorator that should be used instead.
        """
        self.name = name
        self.delegate = delegate
        self.lock = threading.RLock()

        # Simplify implementations by just coding different methods.
        # Python name mangling prevents setting self.__xxx__ directly.
        if delegate:
            self._get = self.get_delegate
            self._set = self.set_delegate
            self._del = self.del_delegate
        else:
            self._get = self.get_obj_dict
            self._set = self.set_obj_dict
            self._del = self.del_obj_dict
        if meth is not None:
            self(meth)

    def __call__(self, meth):
        self.meth = meth
        if self.name is None:
            self.name = meth.__name__
        return self

    def __get__(self, obj, typ=None):
        return self._get(obj, typ)
    def __set__(self, obj, value):
        self._set(obj, value)
    def __delete__(self, obj):
        self._del(obj)

    # object-dict storage
    def get_obj_dict(self, obj, typ=None):
        rv = obj.__dict__.get(self.name, _NOT_FOUND)
        if rv is _NOT_FOUND:
            with self.lock:
                rv = obj.__dict__.get(self.name, _NOT_FOUND) # no races
                if rv is _NOT_FOUND:
                    obj.__dict__[self.name] = rv = self.meth(obj)
        return rv

    def set_obj_dict(self, obj, value):
        obj.__dict__[self.name] = value

    def del_obj_dict(self, obj):
        # Ignore exceptions to allow defensive clearing of the cache
        obj.__dict__.pop(self.name, None)

    # delegate storage
    def get_delegate(self, obj, typ=None):
        delegate = getattr(obj, self.delegate)
        rv = getattr(delegate, self.name, _NOT_FOUND)
        if rv is _NOT_FOUND:
            with self.lock:
                rv = getattr(delegate, self.name, _NOT_FOUND) # no races
                if rv is _NOT_FOUND:
                    rv = self.meth(obj)
                    setattr(delegate, self.name, rv)
        return rv

    def set_delegate(self, obj, value):
        setattr(getattr(obj, self.delegate), self.name, value)

    def del_delegate(self, obj):
        delattr(getattr(obj, self.delegate), self.name)
