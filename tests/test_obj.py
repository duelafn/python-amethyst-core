#!/usr/bin/env python
# -*- coding: utf-8 -*-
# SPDX-License-Identifier: LGPL-3.0

import unittest

import json
import marshal
import sqlite3

import amethyst.core.obj
from amethyst.core import ImmutableObjectException, DuplicateAttributeException
from amethyst.core import Object, Attr
from amethyst.core import amethyst_deflate, amethyst_inflate


class Obj(Object):
    foo = Attr(int)
    bar = Attr(isa=str).strip()
    baz = Attr(float)
    bip = Attr()


class MyTest(unittest.TestCase):
    def test_ttobject(self):
        obj = Object()
        self.assertEqual(obj.dict, {}, "Initial object is empty")
        self.assertEqual(len(obj), 0, "Empty length works")

        obj = Object({})
        self.assertEqual(obj.dict, {}, "Initial object is empty")

        self.assertEqual(json.loads(obj.toJSON()), {"__class__": "__amethyst.core.obj.Object__"}, "Empty toJSON")

        obj = Object.newFromJSON('{"__amethyst.core.obj.Object__": {}}')
        obj = Object.newFromJSON('{"__class__": "__amethyst.core.obj.Object__"}')

        self.assertIsNone(obj.get("__class__"), "fromJSON removes __class__ key")

        with self.assertRaises(ValueError, msg="class verification works"):
            obj = Object.newFromJSON('{"__amethyst.core.obj.NotObject__": {}}')

        with self.assertRaises(ValueError, msg="Invalid if __class__ is missing"):
            obj.fromJSON('{}')

        self.assertFalse(amethyst.core.obj.UNIQUE1 == amethyst.core.obj.UNIQUE2)
        self.assertTrue( amethyst.core.obj.UNIQUE1 != amethyst.core.obj.UNIQUE2)

        class ObjA(Object):
            foo = Attr(int)
            bar = Attr(isa=str).strip()

        class ObjB(Object):
            foo = Attr(int)
            bar = Attr(isa=str).strip()

        class ObjC(ObjA):
            pass

        a = ObjA(foo=23, bar="plugh")
        b = ObjB(foo=23, bar="plugh")
        self.assertFalse(a == b)
        self.assertFalse(b == a)
        self.assertTrue( b != a)
        self.assertTrue( a != b)

        a = ObjA(foo=23, bar="plugh")
        c = ObjC(foo=23, bar="plugh")
        self.assertFalse(a == c)
        self.assertFalse(c == a)
        self.assertTrue( c != a)
        self.assertTrue( a != c)

        a1 = ObjA(foo=23, bar="plugh")
        a2 = ObjA(foo=23, bar="plugh")
        self.assertTrue( a1 == a2)
        self.assertFalse(a1 != a2)

        a1 = ObjA(foo=23, bar="plugh")
        a2 = ObjA(foo=23, bar="barf")
        self.assertFalse(a1 == a2)

        a1 = ObjA(foo=23, bar="plugh")
        a2 = ObjA(bar="plugh")
        self.assertFalse(a1 == a2)

        a1 = ObjA(foo=23, bar="plugh")
        a2 = ObjA()
        self.assertFalse(a1 == a2)

        a1 = ObjA()
        a2 = ObjA(foo=23, bar="plugh")
        self.assertFalse(a1 == a2)

        a1 = ObjA()
        a2 = ObjA()
        self.assertTrue(a1 == a2)

        a1 = ObjA(foo=24)
        a2 = ObjA(foo=24)
        self.assertTrue(a1 == a2)
        self.assertTrue(a1 is not a2)

        self.assertEqual(a1.pop("foo"), 24)
        self.assertEqual(list(a1.keys()), [])

        self.assertTrue(a1.attr_value_ok("foo", 12))
        self.assertTrue(a1.attr_value_ok("foo", "23"))
        self.assertTrue(not a1.attr_value_ok("foo", "2.3"))
        self.assertTrue(not a1.attr_value_ok("plugh", 23))


    def test_overrides(self):
        """
        Some of our methods are explicitly allowed to be replaced. These
        tests replace them with exceptions and verify that other method
        calls don't accidentally call the overrides.
        """
        class ObjOver1(Object):
            foo = Attr(int)
            bar = Attr(isa=str).strip()

            def croak(self, *args, **kwargs):
                raise Exception("Bummer")

            items = croak
            keys = croak
            values = croak
            get = croak
            set = croak
            setdefault = croak
            direct_set = croak
            pop = croak
            update = croak
            direct_update = croak
            attr_value_ok = croak
            load_data = croak
            deflate_data = croak
            inflate_new = croak

        myobj = ObjOver1(foo=23)

        with self.assertRaisesRegex(Exception, r'Bummer'):
            myobj.items()

        myobj.other = 15
        self.assertEqual(myobj.other, 15)
        self.assertEqual(myobj.bar, None)
        self.assertEqual(len(myobj), 1)
        self.assertTrue("foo" in myobj)
        self.assertEqual(myobj.foo, 23)
        self.assertEqual(myobj['foo'], 23)
        del myobj['foo']
        self.assertEqual(myobj.foo, None)
        myobj.foo = 24
        self.assertEqual(myobj.foo, 24)
        myobj['foo'] = 25
        self.assertEqual(myobj.foo, 25)
        myobj.amethyst_validate_update(dict(foo=26))
        myobj.amethyst_validate_data(dict(foo=27))
        myobj.amethyst_load_data(dict(foo=28), verifyclass=False)
        self.assertEqual(myobj.foo, 28)
        self.assertNotEqual(myobj.toJSON(), '')
        myobj.fromJSON('{"foo":"29"}', verifyclass=False)
        self.assertEqual(myobj.foo, 29)


    def test_other_attrs(self):
        """Other attributes explicitly allowed and are not stored in data hash"""
        myobj = Obj(foo=23)
        myobj.other = 15
        self.assertEqual(myobj.other, 15)
        self.assertEqual(myobj.deflate_data().get("other", None), None)
        self.assertFalse("other" in myobj.toJSON())

        # other not listed in keys or values
        self.assertEqual(list(myobj.keys()), ["foo"])
        self.assertEqual(list(myobj.values()), [23])

        with self.assertRaises(AttributeError, msg="Getattr raises exception for names undeclared attrs"):
            myobj.undefined
        with self.assertRaises(KeyError, msg="Getitem raises exception for names undeclared attrs"):
            myobj['undefined']
        with self.assertRaises(KeyError):
            myobj['undefined'] = 42
        with self.assertRaises(KeyError):
            print(myobj['undefined'])
        self.assertEqual(myobj.deflate_data().get("undefined", None), None)
        self.assertFalse("undefined" in myobj.toJSON())

        # However, the dict interface should be for proper attrs only
        with self.assertRaises(KeyError):
            print(myobj['other'])
        with self.assertRaises(KeyError):
            myobj['other'] = 42
        self.assertEqual(myobj.other, 15)
        self.assertEqual(myobj.deflate_data().get("other", None), None)
        self.assertFalse("other" in myobj.toJSON())


    def test_README_validation(self):
        class MyObject(Object):
            amethyst_verifyclass = False
            amethyst_register_type = False
            foo = Attr(int)
            bar = Attr(isa=str).strip()

        # constructors
        myobj = MyObject({ "foo": "23", "bar": "Hello " })
        self.assertIsInstance(myobj.foo, int)
        self.assertEqual(myobj.foo, 23)
        self.assertEqual(myobj.bar, "Hello")

        myobj = MyObject(foo="23", bar="Hello ")
        self.assertIsInstance(myobj.foo, int)
        self.assertEqual(myobj.bar, "Hello")

        # assignment
        myobj["foo"] = "24"                   # Converts to int
        self.assertIsInstance(myobj.foo, int)
        self.assertEqual(myobj.foo, 24)

        myobj.foo = "25"                      # Converts to int
        self.assertIsInstance(myobj["foo"], int)
        self.assertEqual(myobj["foo"], 25)

        with self.assertRaises(ValueError):
            myobj["foo"] = "Not an int"       # Raises exception
        with self.assertRaises(ValueError):
            myobj.foo = "Not an int"          # Raises exception

        # set and update methods
        myobj.set("foo", "26")
        self.assertIsInstance(myobj.foo, int)
        self.assertEqual(myobj.foo, 26)

        myobj.update(foo="27")
        self.assertIsInstance(myobj.foo, int)
        self.assertEqual(myobj.foo, 27)

        myobj.foo = 28
        myobj.setdefault("foo", 29)
        self.assertIsInstance(myobj.foo, int)
        self.assertEqual(myobj.foo, 28)
        del myobj["foo"]
        myobj.setdefault("foo", "30")
        self.assertIsInstance(myobj.foo, int)
        self.assertEqual(myobj.foo, 30)

        with self.assertRaises(ValueError):
            myobj.set("foo", "Not an int")          # Raises exception
        with self.assertRaises(ValueError):
            myobj.update(foo="Not an int")          # Raises exception

        myobj.foo = 24
        myobj.setdefault("foo", "Not an int")       # Not an error (foo already set)
        del myobj["foo"]
        with self.assertRaises(ValueError):
            myobj.setdefault("foo", "Not an int")   # Raises exception if foo unset

        # loading fresh from dict or json
        myobj.fromJSON('{"foo": "32", "bar": "Hello1 "}')
        self.assertEqual(myobj.foo, 32)
        self.assertEqual(myobj.bar, "Hello1")
        myobj = MyObject.newFromJSON('{"foo": "33", "bar": "Hello2 "}')
        self.assertEqual(myobj.foo, 33)
        self.assertEqual(myobj.bar, "Hello2")
        myobj.load_data({"foo": "34", "bar": "Hello3 "})
        self.assertEqual(myobj.foo, 34)
        self.assertEqual(myobj.bar, "Hello3")

        # Not Validated
        myobj.direct_set("foo", "Not an int")     # DANGER: Not an exception!
        self.assertEqual(myobj.foo, "Not an int")
        myobj.foo = 42
        self.assertEqual(myobj.foo, 42)
        myobj.direct_update(foo="Not an int")     # DANGER: Not an exception!
        self.assertEqual(myobj.foo, "Not an int")


    def test_README_serialization(self):
        class ObjSer(Object):
            foo = Attr(int)
            bar = Attr(Obj)

        myobj = Obj(foo="23")
        self.assertEqual(myobj.foo + 1, 24)

        # JSON can be produced and loaded
        myobj = Obj(foo=42, bar="Hello")
        json_string = myobj.toJSON()
        myobj1 = Obj.newFromJSON(json_string)
        self.assertEqual(myobj.dict, myobj1.dict)

        # Even for nested objects
        myobj1 = Obj(foo=12, bar="Hello")
        myobj2 = ObjSer(foo=13, bar=myobj1)
        json_string = myobj2.toJSON()
        myobjn = ObjSer.newFromJSON(json_string)
        self.assertEqual(myobjn.foo, 13)
        self.assertEqual(myobjn.bar.foo, 12)
        self.assertEqual(myobjn.bar.bar, "Hello")

        # Other serialization libraries
        myobj = Obj(foo=42, bar="Hello")
        deflated = marshal.dumps(myobj.deflate_data())
        myobj2 = Obj.inflate_new(marshal.loads(deflated))
        self.assertEqual(myobj.dict, myobj2.dict)
        self.assertTrue(myobj.dict is not myobj2.dict)

        myobj1 = Obj(foo=15, bar="Hello1")
        myobj2 = ObjSer(foo=16, bar=myobj1)
        deflated = marshal.dumps(myobj2.deflate_data())
        myobjn = ObjSer.inflate_new(marshal.loads(deflated))
        self.assertEqual(myobjn.foo, 16)
        self.assertEqual(myobjn.bar.foo, 15)
        self.assertEqual(myobjn.bar.bar, "Hello1")

        # Type hints
        myobj = Obj(foo=23)
        self.assertEqual(
            str(myobj.toJSON(sort_keys=True)),
            '{{"__class__": "__{}.Obj__", "foo": 23}}'.format(self.__module__)
        )

        # required by default
        myobj = Obj.newFromJSON('{{"__class__": "__{}.Obj__", "foo":23}}'.format(self.__module__))
        self.assertEqual(myobj.foo, 23)

        with self.assertRaisesRegex(ValueError, r'should be __{}\.Obj__'.format(self.__module__)):
            Obj.newFromJSON('{"foo":23, "bar":"plugh"}')
        with self.assertRaisesRegex(ValueError, r'expected __{}\.Obj__'.format(self.__module__)):
            Obj.newFromJSON('{{"__class__": "__{}.ObjSer__", "foo":23}}'.format(self.__module__))

        # local override
        myobj = Obj.newFromJSON('{"foo":23, "bar":"plugh"}', verifyclass=False)
        self.assertEqual(myobj.foo, 23)
        self.assertEqual(myobj.bar, "plugh")

        class ObjSer1(Object):
            amethyst_includeclass  = False
            amethyst_verifyclass   = False
            foo = Attr(int)
            bar = Attr(isa=str).strip()

        myobj = ObjSer1.newFromJSON('{"foo":"23", "bar":"plugh"}')
        self.assertEqual(myobj.toJSON(sort_keys=True), '{"bar": "plugh", "foo": 23}')


    def test_immutability(self):
        obj = Obj()

        obj.amethyst_make_immutable()
        self.assertFalse(obj.amethyst_is_mutable(), "is not mutable")

        with self.assertRaises(ImmutableObjectException, msg="Can't set fields when immutable"):
            obj["foo"] = 23

        self.assertIs(obj.amethyst_make_mutable(), obj, "make_mutable returns self")
        self.assertTrue(obj.amethyst_is_mutable(), "is mutable")
        obj["bip"] = 23

        self.assertIs(obj.amethyst_make_immutable(), obj, "make_mutable returns self")
        self.assertFalse(obj.amethyst_is_mutable(), "is not mutable")

        self.assertEqual(obj["bip"], 23, "Can read values when immutable")


    def test_subclass(self):
        obj = Obj(foo=23)
        obj["bar"] = "12"

        self.assertEqual(obj.foo, 23, "Getattr works in subclass when set by constructor")
        self.assertEqual(obj.bar, "12", "Getattr works in subclass when set by setitem")
        self.assertIsNone(obj.baz, "Getattr works on uninitialized values")

        self.assertEqual(obj.dict, {"foo": 23, "bar": "12"}, "No autovivification")

        obj.amethyst_make_immutable()
        self.assertIsNone(obj.bip, "Can read non-existant keys when immutable")

        obj = Object()
        with self.assertRaises(AttributeError, msg="Subclasses don't change parent attributes"):
            obj.foo

        with self.assertRaises(DuplicateAttributeException, msg="Duplicate attribute raises exception"):
            class ObjSub1(Obj):
                foo = Attr(int)

        class ObjSub(Obj):
            jsonhooks = { "__bob__": (lambda obj: "BOB") }
            bab = Attr(int)
            flags = Attr(isa=set)

        self.assertTrue(hasattr(ObjSub, "foo"), "Attrs are inherited")

        obj = ObjSub()
        obj.fromJSON('{{"__class__": "__{}.ObjSub__", "bar": {{"__bob__": "chaz"}}, "flags": {{"__set__": ["chaz"]}}, "baz": "123.45"}}'.format(self.__module__))
        self.assertEqual(obj.bar, "BOB", "jsonhooks extensions")
        self.assertEqual(list(obj.flags)[0], "chaz", "jsonhooks extensions inherit originals")

        obj = Object()
        obj.fromJSON('{"__class__": "__amethyst.core.obj.Object__", "bab": {"__bob__": "chaz"}, "flags": {"__set__": ["chaz"]}, "baz": "123.45"}', import_strategy="sloppy")
        self.assertEqual(obj.get("bab"), {"__bob__": "chaz"}, "jsonhooks extensions do not modify base classes")


    def test_default(self):
        class ObjDflt(Object):
            foo = Attr(int, default=3)
            bar = Attr(default=list)
            baz = Attr(default=[])

        a = ObjDflt()
        b = ObjDflt()

        self.assertEqual(a.foo, 3, "default int a")
        self.assertEqual(b.foo, 3, "default int b")

        self.assertIsInstance(a.bar, list, "default list constructor")
        self.assertIsInstance(a.baz, list, "default list")

        self.assertTrue(a.bar is not b.bar, "default list constructor initializes different objects")
        self.assertTrue(a.baz is b.baz, "default list initializes identical object")


    def test_nested(self):
        class ObjNest(Object):
            foo = Attr(int)
            bar = Attr(Obj)
            baz = Attr(isa=Obj)

        myobj1 = Obj(foo=12, bar="Hello")
        myobj2 = ObjNest(foo=13, bar=myobj1, baz=myobj1)
        self.assertTrue(myobj2.bar is myobj1)            # identical objects
        self.assertTrue(myobj2.bar.dict is myobj1.dict)  # shallowly
        self.assertTrue(myobj2.baz is myobj1)            # isa does not modify


    def test_in_de_flation(self):
        obj = Obj(foo=23, bip=[Obj(baz=2.3), 11])

        dname = "__{}.{}__".format(Obj.__module__, Obj.__name__)
        self.assertIn(dname, ('__test_obj.Obj__', '____main__.Obj__'))

        plain = amethyst_deflate(obj)
        self.assertIsInstance(plain, dict)
        self.assertIsInstance(plain[dname], dict)
        self.assertIsInstance(plain[dname]['foo'], int)
        self.assertIsInstance(plain[dname]['bip'], list)
        self.assertIsInstance(plain[dname]['bip'][0], dict)

        new = amethyst_inflate(plain)
        self.assertIsInstance(new, Obj)
        self.assertEqual(new.foo, 23)
        self.assertIsInstance(new.bip[0], Obj)
        self.assertEqual(new.bip[0].baz, 2.3)
        self.assertEqual(new.bip[1], 11)
        self.assertIsNone(new.bar)
        self.assertIsNone(new.baz)
        self.assertIsNone(new.bip[0].foo)

    def test_integration(self):
        """
        Tests to ensure that we play well with other common libraries.

        six:
          - ensure that we can be passed to six.iteritems()

        sqlite3:
          - ensure that sqlite3.Row objects can be used to initialize objects
        """
        # six.iteritems(obj)
        try:
            import six
            obj = Obj(foo=12, bar="hi", baz=2.3)
            got = set()
            for k, v in six.iteritems(obj):
                got.add("{}={}".format(k, v))
            self.assertEqual(got, set(["foo=12", "bar=hi", "baz=2.3"]), "works with six.iteritems")

        except ImportError:
            raise unittest.SkipTest("six not installed, skipping six integration tests")

        # Object(sqlite3.Row)
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        conn.execute("CREATE TABLE test (foo INTEGER, bar TEXT, baz TEXT, bip TEXT)")
        conn.execute("INSERT INTO test VALUES (74, 'plugh', '12.5', NULL)")

        obj = Obj(conn.execute('SELECT * FROM test').fetchone())
        self.assertEqual(obj.foo, 74)
        self.assertEqual(obj.bar, "plugh")
        self.assertEqual(obj.baz, 12.5)
        self.assertEqual(obj.bip, None)


if __name__ == '__main__':
    unittest.main()
