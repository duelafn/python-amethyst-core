#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division, absolute_import, print_function, unicode_literals
import unittest

import json
from amethyst.core import *

class MyTest(unittest.TestCase):

    def test_ttobject(self):
        obj = Object()
        self.assertEqual(obj.dict, {}, "Initial object is empty")

        with self.assertRaises(AttributeError, msg="Undeclared attrs raise AttributeError"):
            obj.foo

        with self.assertRaises(KeyError, msg="Missing keys raise KeyError"):
            obj["foo"]

        self.assertEqual(len(obj), 0, "Empty length works")

        self.assertEqual(json.loads(obj.toJSON()), {"__amethyst.core.obj.Object__": {}}, "Empty toJSON")

        obj = Object.newFromJSON('{"__amethyst.core.obj.Object__": {}}')
        obj = Object.newFromJSON('{"__class__": "__amethyst.core.obj.Object__"}')

        with self.assertRaises(ValueError, msg="class verification works"):
            obj = Object.newFromJSON('{"__amethyst.core.obj.NotObject__": {}}')

        return

        json_value = json.loads(obj.toJSON())
        self.assertEqual(set(json_value.keys()), set(["flags", "id", "__class__"]), "JSON Export - keys")
        self.assertEqual(json_value["__class__"], "Object", "JSON Export - __class__")
        self.assertEqual(json_value["id"], obj.id, "JSON Export - id")
        self.assertEqual(list(json_value["flags"].keys()), ["__set__"], "JSON Export - flags")
        self.assertEqual(sorted(json_value["flags"]["__set__"]), ["bar", "foo"], "JSON Export - flag set")

        obj.fromJSON('{"flags": {"__set__": ["chaz"]}, "id": "12345", "__class__": "Object"}')
        self.assertIsNone(obj.get("__class__"), "fromJSON removes __class__ key")
        self.assertTrue(obj.has_flag("chaz"), "fromJSON sets new flags")
        self.assertFalse(obj.has_flag("foo"), "fromJSON replaces old flags")

        with self.assertRaises(JSONValidationException, msg="Invalid if __class__ is missing"):
            obj.fromJSON('{"flags": {"__set__": ["chaz"]}, "id": "12345"}')

        self.assertIs(obj.fromJSON('{"flags": {"__set__": ["chaz"]}, "id": "12345"}', verifyclass=False), obj, "verifyclass=False allows missing __class__")

        with self.assertRaises(JSONValidationException, msg="Invalid if unexpected keys"):
            obj.fromJSON('{"flags": {"__set__": ["chaz"]}, "id": "12345", "__class__": "Object", "blob": 23}')

        self.assertIs(obj.fromJSON('{"flags": {"__set__": ["chaz"]}, "id": "12345", "__class__": "Object", "blob": 23}', strictkeys=False), obj, "strictkey=False allows unexpected keys")


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

        with self.assertRaises(Exception, msg="Duplicate attribute raises exception"):
            class Obj2(Obj):
                foo = Attr(int)

        class Obj3(Obj):
            jsonhooks = { "__bob__": (lambda obj: "BOB") }
            bab = Attr(int)

        self.assertTrue(hasattr(Obj3, "foo"), "Attrs are inherited")

        return

        obj = Obj3()
        obj.fromJSON('{"__class__": "Obj3", "bab": {"__bob__": "chaz"}, "flags": {"__set__": ["chaz"]}, "id": "12345"}')
        self.assertEqual(obj.bab, "BOB", "jsonhooks extensions")
        self.assertEqual(list(obj.flags)[0], "chaz", "jsonhooks extensions inherit originals")

        obj = Object()
        obj.fromJSON('{"__class__": "Object", "bab": {"__bob__": "chaz"}, "flags": {"__set__": ["chaz"]}, "id": "12345"}')
        self.assertEqual(obj.get("bab"), {"__bob__": "chaz"}, "jsonhooks extensions do no modify base classes")


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

if __name__ == '__main__':
    unittest.main()
