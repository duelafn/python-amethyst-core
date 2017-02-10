#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division, absolute_import, print_function, unicode_literals
import unittest

from amethyst.core import cached_property, coalesce

class Foo(object):
    def __init__(self, bar=None):
        self.computed = 0
        if bar is not None:
            self.bar = bar

    @cached_property
    def bar(self):
        self.computed += 1
        return 42


class MyTest(unittest.TestCase):

    def test_coalesce(self):
        self.assertIsNone(coalesce(), "Nothing!")
        self.assertIsNone(coalesce(None, None, None), "None!")
        self.assertEqual(coalesce(42, None, None), 42, "Match first")
        self.assertEqual(coalesce(None, 42, None, None), 42, "Match middle")
        self.assertEqual(coalesce(None, None, None, "42"), "42", "Match last")
        self.assertEqual(coalesce(None, 0, None, None), 0, "Match zero")
        self.assertFalse(coalesce(None, False, None, None), "Match falsey")

    def test_cached_property(self):
        foo = Foo()

        self.assertEqual(foo.computed, 0, "Not calculated yet")
        self.assertEqual(foo.bar, 42, "Computed")
        self.assertEqual(foo.computed, 1, "Calculated once")
        self.assertEqual(foo.bar, 42, "Cached")
        self.assertEqual(foo.computed, 1, "Calculated once (still)")

        foo.bar = 12
        self.assertEqual(foo.bar, 12, "Assigned")
        self.assertEqual(foo.computed, 1, "Calculated once (still)")

        del foo.bar
        self.assertEqual(foo.bar, 42, "Recomputed")
        self.assertEqual(foo.computed, 2, "Calculated twice")

        foo = Foo(bar=12)
        self.assertEqual(foo.bar, 12, "Assigned")
        self.assertEqual(foo.computed, 0, "Never calculated")

        del foo.bar
        self.assertEqual(foo.bar, 42, "Cleared / Computed")
        self.assertEqual(foo.computed, 1, "Calculated finally")


if __name__ == '__main__':
    unittest.main()
