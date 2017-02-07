#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division, absolute_import, print_function, unicode_literals
import unittest

import six

from amethyst.core import Object, Attr

class MyTest(unittest.TestCase):

    def test_basic(self):
        class MyObject(Object):
            amethyst_register_type = False
            foo = Attr(int)
            bar = Attr(isa=six.text_type).strip()
            baz = Attr(isa=(int, list))

        myobj = MyObject(dict(foo=23, bar=" Hello "))

        self.assertEqual(myobj.foo, 23)
        self.assertEqual(myobj.bar, "Hello")

        myobj.set("foo", 15, foo=5)
        self.assertEqual(myobj.foo, 15, ".set() takes positional or kwargs and prefers positional")

        # Explicitly support list/tuple of isa types
        myobj.set(baz=23)
        self.assertEqual(myobj.baz, 23, "isa tuple:int")
        myobj.set(baz=["foo", "bar"])
        self.assertEqual(myobj.baz, ["foo", "bar"], "isa tuple:list")
        with self.assertRaises(ValueError):
            myobj.set("foo", "Not an int or list")

    def test_README_validation(self):
        class MyObject(Object):
            amethyst_verifyclass = False
            amethyst_register_type = False
            foo = Attr(int)
            bar = Attr(isa=six.text_type).strip()

        # dictionary constructor
        myobj = MyObject({ "foo": "23", "bar": "Hello " })
        self.assertIsInstance(myobj.foo, int)
        self.assertEqual(myobj.bar, "Hello")

        # set and load_data methods
        myobj.setdefault("foo", "Not an int")   # Not an error (foo already set)
        del myobj["foo"]
        with self.assertRaises(ValueError):
            myobj.setdefault("foo", "Not an int")   # Raises exception if foo unset
        with self.assertRaises(ValueError):
            myobj.set("foo", "Not an int")          # Raises exception

        myobj.load_data({"foo": "23", "bar": "Hello "})
        self.assertEqual(myobj.foo, 23)
        self.assertEqual(myobj.bar, "Hello")

        # loading from JSON
        myobj.fromJSON('{"foo": "23", "bar": "Hello "}')
        self.assertEqual(myobj.foo, 23)
        self.assertEqual(myobj.bar, "Hello")
        myobj = MyObject.newFromJSON('{"foo": "23", "bar": "Hello "}')
        self.assertEqual(myobj.foo, 23)
        self.assertEqual(myobj.bar, "Hello")

        # kwargs constructor
        myobj = MyObject(foo="23", bar="Hello ")
        self.assertNotIsInstance(myobj.foo, int)
        self.assertEqual(myobj.bar, "Hello ")

        # attribute assignment
        myobj.foo = "Not an int"                # Not an exception!
        myobj["foo"] = "Not an int"             # Not an exception!

        # update method
        myobj.update(foo="Not an int")          # Not an exception!

        self.assertEqual(myobj.foo, "Not an int")

    def test_README_serialization(self):
        class MyObject(Object):
            amethyst_register_type = False
            foo = Attr(int)
            bar = Attr(isa=six.text_type).strip()

        myobj = MyObject.newFromJSON(
            '{"foo":23, "bar":" plugh  "}',
            verifyclass=False
        )
        self.assertEqual(myobj.bar, "plugh")

        myobj = MyObject(foo=23)
        self.assertEqual(
            six.text_type(myobj.toJSON(sort_keys=True)),
            '{"__class__": "__test_attr.MyObject__", "foo": 23}'
        )

        self.assertEqual(
            six.text_type(myobj.toJSON(style="single-key")),
            '{"__test_attr.MyObject__": {"foo": 23}}'
        )

        self.assertEqual(
            six.text_type(myobj.toJSON(includeclass=False)),
            '{"foo": 23}'
        )

        class MyObject2(Object):
            amethyst_includeclass  = False
            amethyst_verifyclass   = False

            foo = Attr(int)
            bar = Attr(isa=six.text_type).strip()

        # No extra class info due to modified defaults:
        myobj = MyObject2.newFromJSON('{"foo":"23", "bar":" plugh  "}')
        self.assertEqual(
            six.text_type(myobj.toJSON(sort_keys=True)),
            '{"bar": "plugh", "foo": 23}'
        )

    def test_Attr_docs(self):
        # The Attr() docs specify a few specific odd cases:
        class MyObject(Object):
            amethyst_register_type = False
            foo_int      = Attr(int)
            foo_floatint = Attr(float).int()
            foo_posint   = 0 < Attr(int)
            foo_proofint = (0 <= Attr(int)) <= 200     # Parens are necessary!

        myobj = MyObject()

        myobj.set("foo_int", "23")
        self.assertEqual(myobj.foo_int, 23)

        myobj.set("foo_int", 23.6)
        self.assertEqual(myobj.foo_int, 23)

        myobj.set("foo_floatint", "23.3")
        self.assertEqual(myobj.foo_floatint, 23)

        myobj.set("foo_floatint", 23.6)
        self.assertEqual(myobj.foo_floatint, 23)

        myobj.set("foo_posint", "500")
        self.assertEqual(myobj.foo_posint, 500)

        myobj.set("foo_proofint", "150")
        self.assertEqual(myobj.foo_proofint, 150)

        myobj.set("foo_proofint", 200)
        self.assertEqual(myobj.foo_proofint, 200)

        myobj.set("foo_proofint", 0)
        self.assertEqual(myobj.foo_proofint, 0)

        with self.assertRaises(ValueError):
            myobj.set("foo_int", "23.4")
        with self.assertRaises(ValueError):
            myobj.set("foo_floatint", "sdf")
        with self.assertRaises(ValueError):
            myobj.set("foo_posint", 0)
        with self.assertRaises(ValueError):
            myobj.set("foo_posint", -5)
        with self.assertRaises(ValueError):
            myobj.set("foo_proofint", -5)
        with self.assertRaises(ValueError):
            myobj.set("foo_proofint", 201)



if __name__ == '__main__':
    unittest.main()
