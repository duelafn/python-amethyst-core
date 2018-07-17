# -*- coding: utf-8 -*-
"""

"""
# Copyright (C) 2016  Dean Serenevy
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as published
# by the Free Software Foundation, version 3 of the License.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for
# more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this program. If not, see <http://www.gnu.org/licenses/>.
from __future__ import division, absolute_import, print_function, unicode_literals
__all__ = """
cached_property
smartmatch
coalesce
""".split()

import re

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

    Creates properties with deferred calculation. Once calculated, the
    result is stored and returned from cache on subsequent access. Useful
    for expensive operations which may not be needed, or to ensure
    just-in-time construction (I like using this for subwidget construction
    in GUI classes, see example below).

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


    Example GUI use::

        import wx
        from amethyst.core import cached_property as widget

        class SimpleWindow(wx.Frame):
            def __init__(self, *args, **kwargs):
                super(SimpleWindow, self).__init__(*args, **kwargs)
                self.sizer.Add(self.button1)
                self.sizer.Add(self.button2)
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
            def button2(self):
                widget = wx.Button(self, wx.ID_ANY, "Do Something Else")
                widget.Bind(wx.EVT_BUTTON, self.on_click2)
                return widget

            @widget
            def button_exit(self):
                widget = wx.Button(self, wx.ID_ANY, "Exit")
                widget.Bind(wx.EVT_BUTTON, lambda evt: wx.Exit())
                return widget

            def on_click1(self, evt):
                print("Ouch!")

            def on_click2(self, evt):
                print("Ouch again!")

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
    def __init__(self, meth=None, name=None):
        self.name = name
        if meth is not None:
            self(meth)

    def __call__(self, meth):
        self.meth = meth
        if self.name is None:
            self.name = meth.__name__
        return self

    def __get__(self, obj, typ=None):
        if self.name not in obj.__dict__:
            obj.__dict__[self.name] = self.meth(obj)
        return obj.__dict__[self.name]

    def __set__(self, obj, value):
        obj.__dict__[self.name] = value

    def __delete__(self, obj):
        if self.name in obj.__dict__:
            del obj.__dict__[self.name]
