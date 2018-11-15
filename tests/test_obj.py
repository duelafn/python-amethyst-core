#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division, absolute_import, print_function, unicode_literals
import unittest

import json
from amethyst.core import Object, Attr
from amethyst.core import ImmutableObjectException, DuplicateAttributeException

class MyTest(unittest.TestCase):

    def test_ttobject(self):
        obj = Object()
        self.assertEqual(obj.dict, {}, "Initial object is empty")

        with self.assertRaises(AttributeError, msg="Undeclared attrs raise AttributeError"):
            obj.foo

        with self.assertRaises(KeyError, msg="Missing keys raise KeyError"):
            obj["foo"]

        self.assertEqual(len(obj), 0, "Empty length works")

        self.assertEqual(json.loads(obj.toJSON()), {"__class__": "__amethyst.core.obj.Object__"}, "Empty toJSON")

        obj = Object.newFromJSON('{"__amethyst.core.obj.Object__": {}}')
        obj = Object.newFromJSON('{"__class__": "__amethyst.core.obj.Object__"}')

        self.assertIsNone(obj.get("__class__"), "fromJSON removes __class__ key")

        with self.assertRaises(ValueError, msg="class verification works"):
            obj = Object.newFromJSON('{"__amethyst.core.obj.NotObject__": {}}')

        with self.assertRaises(ValueError, msg="Invalid if __class__ is missing"):
            obj.fromJSON('{}')


    def test_immutability(self):
        obj = Object(test=23)

        obj.make_immutable()
        self.assertFalse(obj.is_mutable(), "is not mutable")

        with self.assertRaises(ImmutableObjectException, msg="Can't set fields when immutable"):
            obj["foo"] = 23

        with self.assertRaises(AttributeError, msg="Getattr raises exception for names undeclared attrs"):
            obj.undefined

        self.assertIs(obj.make_mutable(), obj, "make_mutable returns self")
        self.assertTrue(obj.is_mutable(), "is mutable")
        obj["bar"] = 23

        self.assertIs(obj.make_immutable(), obj, "make_mutable returns self")
        self.assertFalse(obj.is_mutable(), "is not mutable")

        self.assertEqual(obj["bar"], 23, "Can read values when immutable")


    def test_subclass(self):
        class Obj(Object):
            foo = Attr(int)
            bar = Attr()
            baz = Attr(float)
            bip = Attr(float)

        obj = Obj(foo=23)
        obj["bar"] = 12

        self.assertEqual(obj.foo, 23, "Getattr works in subclass when set by constructor")
        self.assertEqual(obj.bar, 12, "Getattr works in subclass when set by setitem")
        self.assertIsNone(obj.baz, "Getattr works on uninitialized values")

        self.assertEqual(obj.dict, {"foo": 23, "bar": 12}, "No autovivification")

        obj.make_immutable()
        self.assertIsNone(obj.bip, "Can read non-existant keys when immutable")

        obj = Object()
        with self.assertRaises(AttributeError, msg="Subclasses don't change parent attributes"):
            obj.foo

        with self.assertRaises(DuplicateAttributeException, msg="Duplicate attribute raises exception"):
            class Obj2(Obj):
                foo = Attr(int)

        class Obj3(Obj):
            jsonhooks = { "__bob__": (lambda obj: "BOB") }
            bab = Attr(int)
            flags = Attr(isa=set)

        self.assertTrue(hasattr(Obj3, "foo"), "Attrs are inherited")

        obj = Obj3()
        obj.fromJSON('{"__class__": "__test_obj.Obj3__", "bar": {"__bob__": "chaz"}, "flags": {"__set__": ["chaz"]}, "baz": "123.45"}')
        self.assertEqual(obj.bar, "BOB", "jsonhooks extensions")
        self.assertEqual(list(obj.flags)[0], "chaz", "jsonhooks extensions inherit originals")

        obj = Object()
        obj.fromJSON('{"__class__": "__amethyst.core.obj.Object__", "bab": {"__bob__": "chaz"}, "flags": {"__set__": ["chaz"]}, "baz": "123.45"}', import_strategy="sloppy")
        self.assertEqual(obj.get("bab"), {"__bob__": "chaz"}, "jsonhooks extensions do not modify base classes")


    def test_default(self):
        class Obj4(Object):
            foo = Attr(int, default=3)
            bar = Attr(default=list)
            baz = Attr(default=[])

        a = Obj4()
        b = Obj4()

        self.assertEqual(a.foo, 3, "default int a")
        self.assertEqual(b.foo, 3, "default int b")

        self.assertIsInstance(a.bar, list, "default list constructor")
        self.assertIsInstance(a.baz, list, "default list")

        self.assertFalse(a.bar is b.bar, "default list constructor initializes different objects")
        self.assertTrue(a.baz is b.baz, "default list initializes identical object")


    def test_integration(self):
        class Obj5(Object):
            foo = Attr(int)
            bar = Attr()
            baz = Attr(float)
            bip = Attr(float)

        try:
            import six
            obj = Obj5(foo=12, bar="hi", baz=2.3)
            got = set()
            for k, v in six.iteritems(obj):
                got.add("{}={}".format(k, v))
            self.assertEqual(got, set(["foo=12", "bar=hi", "baz=2.3"]), "works with six.iteritems")

        except ImportError:
            raise unittest.SkipTest("six not installed, skipping six integration tests")


if __name__ == '__main__':
    unittest.main()
