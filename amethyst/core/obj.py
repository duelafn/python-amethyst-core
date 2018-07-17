# -*- coding: utf-8 -*-
"""
Generic serializable object

SYNOPSIS

    from amethyst.core import Object, Attr

    class MyObject(Object):
        # Private encoders available only this this class and subclasses
        jsonencoders = { MyClass:       (lambda obj: { "__myclass__": obj.toDict() }) }
        jsonhooks    = { "__myclass__": (lambda obj: MyClass(**obj)) }

        # Attr() defines properties and will include in serialization.
        foo = Attr(int)
        bar = Attr(str).strip()

        # foo and bar will be automatically extracted from kwargs.
        # .other will not be serialized by .toJSON()
        def __init__(self, other=None, **kwargs):
            # Note: We do not validate data passed to constructor by default
            super().__init__(**self.validate_data(kwargs))
            self.other = other


    # ...
    myobj = MyObject(foo=23, other="Hello")
    myobj.toJSON()   # { "__my.module.MyObject__": { "foo": 23 } }

    myobj = MyObject()
    myobj.fromJSON({ "foo": 23, "bar": " plugh  " })
    print(myobj.bar)      # "plugh"  (no spaces)



DESCRIPTION

Implements the dictionary interface and stores everything in self.dict.

Subclasses can define Attr()s which will have properties defined as
shortcuts to read and write keys in the dictionary.

By storing all attributes in a dict, we can be trivially serialized.
toJSON() and fromJSON() methods exist to help with this, and should be used
for all JSON serialization since they will correctly handle `set()` and
other values (see the `JSONEncoder` and `JSONObjectHook` methods).
Additionally, the JSON methods will perform automatic validation based on
type information passed to the Attr() objects and will ensure that it is
loading data for the correct class and that no unexpected keys are present.
"""
# Copyright (C) 2016  Dean Serenevy
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, version 3 of the License.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for
# more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
from __future__ import division, absolute_import, print_function, unicode_literals

__all__ = """
Object
Attr
AmethystException
  DuplicateAttributeException
  ImmutableObjectException
register_amethyst_type
""".split()

import json
import six

from .util import coalesce, smartmatch


class AmethystException(Exception): pass
class ImmutableObjectException(AmethystException): pass
class DuplicateAttributeException(AmethystException): pass


class Attr(object):
    """
    Base class for Amethyst Object Attributes.

    Attribute descriptions primarily consist of a function which takes in a
    value and either returns a (possibly modified) value or else raises a
    ValueError. Python's standard object constructors generally work well,
    though beware that `str` will generally accept anything.

        foo = Attr(int)                   # Coerce to int (strict parsing)
        foo = Attr(float).int()           # Parse via float, but then integerize
        foo = 0 < Attr(int)               # Positive integer
        foo = (0 <= Attr(int)) <= 200     # Parens are necessary!

        # Stringify, then strip whitespace
        foo = Attr(str).strip()

        # Python 3: Accept bytes or str, decoding if possible (only decodes
        # bytes since decode not a method of str)
        foo = Attr(isa=(bytes, str)).decode("UTF-8")

        # Coerce to a list via .split()
        foo = Attr(isa=(list, str)).split()

    Anything based off of Amethyst's `Object` class generally will work as well:

        class MyClass(amethyst.core.Object):
            ...

        class MyClass2(amethyst.core.Object):
            foo = Attr(MyClass)

    """
    def __init__(self, convert=None, verify=None, isa=None, default=None, builder=None, fget=None, fset=None, fdel=None, doc=None, OVERRIDE=False):
        """
        Base attribute descriptor

        @param convert: Attribute converter. At this time, only callables
        are supported. Callable should accept a single argument, the value,
        and should return a canonicalized value. Invalid values should
        raise a ValueError(). If converter is `None`, values will be passed
        unmodified.

        @param verify: Attribute verifier. Called after conversion, this
        callable should return a truthy result if the value is acceptable.

        @param isa: Called after conversion but before verification,
        ensures that the value is one of the passed types.

        @param default: Default value applied at object creation time. If
        default is a callable, it will be called to produce the default
        (e.g., `list`).

        @param builder: Callable which will lazily build a default value
        when the attribute is first used.

        @param fget, fset, fdel: If any of these functions are defined,
        they will be used to construct the object property. If all three
        are none (the default), then the functions which get/set/del the
        appropriate key in the object dictionary will be defined.

        @param doc: Documentation to be attached to the property.

        @param OVERRIDE: When true, allow attribute to replace an existing
        attribute (from a parent class).
        """
        if verify is not None and not callable(verify):
            raise TypeError("Unknown 'verify' type")
        if convert is not None and not callable(convert):
            raise TypeError("Unknown 'convert' type")
        self.convert = convert
        self.isa     = isa
        self.verify  = verify
        self.fget    = fget
        self.fset    = fset
        self.fdel    = fdel
        self.doc     = doc
        self.default = default
        self.builder = builder
        self.OVERRIDE = OVERRIDE

    def build_property(self, name):
        if self.fget is None and self.fset is None and self.fdel is None:

            def fget(obj):
                try:
                    return obj.dict[name]
                except KeyError:
                    # default happens before builder
                    if self.default is not None:
                        obj.dict[name] = self.get_default()
                        return obj.dict[name]
                    if self.builder is not None:
                        obj.dict[name] = self.builder()
                        return obj.dict[name]
                return None

            def fset(obj, value):
                obj.assert_mutable()
                obj.dict[name] = value

            def fdel(obj):
                obj.assert_mutable()
                del obj.dict[name]

            return property(fget, fset, fdel, self.doc)

        else:
            return property(self.fget, self.fset, self.fdel, self.doc)

    def get_default(self):
        if callable(self.default):
            return self.default()
        else:
            return self.default

    def __call__(self, value, key=None):
        if self.convert:
            value = self.convert(value)
        if self.isa:
            if not isinstance(value, self.isa):
                raise ValueError("Value of '{}' is not an instance of {}".format(key, str(self.isa)))
        if self.verify:
            if not self.verify(value):
                raise ValueError("Value of '{}' does not satisfy verification callback".format(key))
        return value

    def __and__(self, other):
        return Attr(
            lambda v: other(self(v)),
            OVERRIDE=(self.OVERRIDE or getattr(other, "OVERRIDE", False)),
            doc=(self.doc or getattr(other, "doc", None)),
        )
    def __rand__(self, other):
        return Attr(
            lambda v: self(other(v)),
            OVERRIDE=(self.OVERRIDE or getattr(other, "OVERRIDE", False)),
            doc=(self.doc or getattr(other, "doc", None)),
        )

    def __or__(self, other):
        def convert(value):
            try:
                return self(value)
            except ValueError as err:
                if callable(other):
                    return other(value)
                elif value == other:
                    return other
                else:
                    raise err
        return Attr(convert,
            OVERRIDE=(self.OVERRIDE or getattr(other, "OVERRIDE", False)),
            doc=(self.doc or getattr(other, "doc", None)),
        )
    def __ror__(self, other):
        def convert(value):
            try:
                if callable(other):
                    return other(value)
                elif value == other:
                    return other
                else:
                    raise ValueError("Invalid value")
            except ValueError:
                return self(value)
        return Attr(convert,
            OVERRIDE=(self.OVERRIDE or getattr(other, "OVERRIDE", False)),
            doc=(self.doc or getattr(other, "doc", None)),
        )

    def __eq__(self, other):
        """
        Tests via smartmatch

        WARNING: hash lookups must be idempotent (looking if the result of
        a previous lookup had better return the same thing) since we offer
        no guarantees that validation may not happen more than once.

        GOOD:  `{ "a": "A", "b": "B",  "A": "A", "B": "B" }`

        BAD:   `{ "a": "A", "b": "B" }`  # will fail on repeated validation since "A" and "B" are not keys
        """
        return Attr(lambda v: smartmatch(self(v), other), OVERRIDE=self.OVERRIDE, doc=self.doc)
    def __ne__(self, other):
        """Ensure no smartmatch"""
        def convert(value):
            val = self(value)
            try:
                # If we do not match the other value, this raises an
                # exception (thus we can return val).
                smartmatch(val, other)
            except ValueError:
                return val
            # otherwise, we've matched the smartmatch, this we match what
            # we don't want to be - raise a value error.
            raise ValueError("Invalid Value")
        return Attr(convert, OVERRIDE=self.OVERRIDE, doc=self.doc)

    # This is starting to get cute:
    def __lt__(self, other):
        def convert(value):
            val = self(value)
            if val < other: return val
            raise ValueError("Invalid Value")
        return Attr(convert, OVERRIDE=self.OVERRIDE, doc=self.doc)
    def __le__(self, other):
        def convert(value):
            val = self(value)
            if val <= other: return val
            raise ValueError("Invalid Value")
        return Attr(convert, OVERRIDE=self.OVERRIDE, doc=self.doc)
    def __ge__(self, other):
        def convert(value):
            val = self(value)
            if val >= other: return val
            raise ValueError("Invalid Value")
        return Attr(convert, OVERRIDE=self.OVERRIDE, doc=self.doc)
    def __gt__(self, other):
        def convert(value):
            val = self(value)
            if val > other: return val
            raise ValueError("Invalid Value")
        return Attr(convert, OVERRIDE=self.OVERRIDE, doc=self.doc)

    # These modifiers make no sense unless they are idempotent since we may
    # validate multiple times. Thus, we only define those whose semantics
    # swing that way.
    def __mod__(self, other):
        return Attr(lambda v: self(v) % other, OVERRIDE=self.OVERRIDE, doc=self.doc)
    def __pos__(self):
        return Attr(lambda v: +self(v), OVERRIDE=self.OVERRIDE, doc=self.doc)
    def __abs__(self):
        return Attr(lambda v: abs(self(v)), OVERRIDE=self.OVERRIDE, doc=self.doc)

    # I don't see much use for float() since it is the first thing you
    # would want to do. However, int() could be useful since
    # Attr(float).int() is a more flexible converter (integerizing stringy
    # floats rather than raising an exception). Just for completeness, we
    # include complex too.
    def float(self):
        return Attr(lambda v: float(self(v)), OVERRIDE=self.OVERRIDE, doc=self.doc)
    def int(self):
        return Attr(lambda v: int(self(v)), OVERRIDE=self.OVERRIDE, doc=self.doc)
    def complex(self):
        return Attr(lambda v: complex(self(v)), OVERRIDE=self.OVERRIDE, doc=self.doc)

    # Can also define a handful of common methods one might wish to call,
    # and call them if present. Happy duck-typing.
    def strip(self, chars=None):
        """Return a new attribute which strips whitespace if applicable (duck typing)."""
        def convert(value):
            value = self(value)
            return value.strip(chars) if hasattr(value, "strip") else value
        return Attr(convert, OVERRIDE=self.OVERRIDE, doc=self.doc)
    def rstrip(self, chars=None):
        """Return a new attribute which strips whitespace from the right side if applicable (duck typing)."""
        def convert(value):
            value = self(value)
            return value.rstrip(chars) if hasattr(value, "rstrip") else value
        return Attr(convert, OVERRIDE=self.OVERRIDE, doc=self.doc)
    def lstrip(self, chars=None):
        """Return a new attribute which strips whitespace from the left side if applicable (duck typing)."""
        def convert(value):
            value = self(value)
            return value.lstrip(chars) if hasattr(value, "lstrip") else value
        return Attr(convert, OVERRIDE=self.OVERRIDE, doc=self.doc)

    def encode(self, encoding="UTF-8", errors="strict"):
        """Return a new attribute which encodes value if applicable (duck typing). Defaults to UTF-8 encoding."""
        def convert(value):
            value = self(value)
            return value.encode(encoding, errors) if hasattr(value, "encode") else value
        return Attr(convert, OVERRIDE=self.OVERRIDE, doc=self.doc)
    def decode(self, encoding="UTF-8", errors="strict"):
        """Return a new attribute which decodes value if applicable (duck typing). Defaults to UTF-8 encoding."""
        def convert(value):
            value = self(value)
            return value.decode(encoding, errors) if hasattr(value, "decode") else value
        return Attr(convert, OVERRIDE=self.OVERRIDE, doc=self.doc)

    def lower(self):
        """Return a new attribute which lower-cases value if applicable (duck typing)."""
        def convert(value):
            value = self(value)
            return value.lower() if hasattr(value, "lower") else value
        return Attr(convert, OVERRIDE=self.OVERRIDE, doc=self.doc)
    def upper(self):
        """Return a new attribute which upper-cases value if applicable (duck typing)."""
        def convert(value):
            value = self(value)
            return value.upper() if hasattr(value, "upper") else value
        return Attr(convert, OVERRIDE=self.OVERRIDE, doc=self.doc)
    def title(self):
        """Return a new attribute which title-cases value if applicable (duck typing)."""
        def convert(value):
            value = self(value)
            return value.title() if hasattr(value, "title") else value
        return Attr(convert, OVERRIDE=self.OVERRIDE, doc=self.doc)
    def capitalize(self):
        """Return a new attribute which capitalizes value if applicable (duck typing)."""
        def convert(value):
            value = self(value)
            return value.capitalize() if hasattr(value, "capitalize") else value
        return Attr(convert, OVERRIDE=self.OVERRIDE, doc=self.doc)
    def casefold(self):
        """Return a new attribute which casefolds value if applicable (duck typing)."""
        def convert(value):
            value = self(value)
            return value.casefold() if hasattr(value, "casefold") else value
        return Attr(convert, OVERRIDE=self.OVERRIDE, doc=self.doc)

    def split(self, sep=None, maxsplit=-1):
        """Return a new attribute which splits its value if applicable (duck typing)."""
        def convert(value):
            value = self(value)
            return value.split(sep, maxsplit) if hasattr(value, "split") else value
        return Attr(convert, OVERRIDE=self.OVERRIDE, doc=self.doc)


global_amethyst_encoders = dict()
global_amethyst_hooks = dict()
def register_amethyst_type(cls, encode, decode, name=None, overwrite=False, wrap_encode=True):
    if name is None:
        if isinstance(cls, BaseObject):
            name = cls._dundername
        else:
            name = "__{}.{}__".format(cls.__module__, cls.__name__)
    if cls in global_amethyst_encoders and not overwrite:
        raise ValueError("Class encoder '{}' already reqistered".format(cls))
    if name in global_amethyst_hooks and not overwrite:
        raise ValueError("Class hook '{}' already reqistered".format(name))
    global_amethyst_encoders[cls] = lambda obj: { name: encode(obj) } if wrap_encode else encode
    global_amethyst_hooks[name]   = decode


# Python3 moved the builtin modules around, force the name so py3 can talk to py2
register_amethyst_type(set, list, set, name="__set__")
register_amethyst_type(frozenset, list, frozenset, name="__frozenset__")


class AttrsMetaclass(type):
    """
    Metaclass for Amethyst Object class descendants. Simply looks at all
    attributes for any which are instances of `Attr`. The `Attr` itself is
    saved to the `_attr` class attribute (a dictionary) and a property
    created in its place via the Attr `build_property` method.
    """
    def __new__(cls, class_name, bases, attrs):
        new_attrs = dict()
        for name in list(attrs.keys()):
            if isinstance(attrs[name], Attr):
                new_attrs[name] = attrs.pop(name)
                new_attrs[name].name = name

        new_cls = super(AttrsMetaclass, cls).__new__(cls, class_name, bases, attrs)

        # Need some bootstrapping
        if class_name != 'BaseObject' and attrs.get("amethyst_register_type", True):
            register_amethyst_type(
                new_cls,
                encode    = (lambda obj: obj.dict),
                decode    = (lambda obj: new_cls().load_data(obj, verifyclass=False)),
                overwrite = False
            )

        # Merge json hooks into the base _json* hooks.
        for jattr in "jsonhooks", "jsonencoders":
            if hasattr(new_cls, jattr):
                _jattr = "_" + jattr
                setattr(new_cls, _jattr, dict(getattr(new_cls, _jattr)))# Shallow clone
                getattr(new_cls, _jattr).update(getattr(new_cls, jattr))
                delattr(new_cls, jattr)

        for name, attr in six.iteritems(new_attrs):
            if not attr.OVERRIDE and hasattr(new_cls, name):
                raise DuplicateAttributeException("Attribute {} in {} already defined in a parent class.".format(name, cls.__name__))
            setattr(new_cls, name, attr.build_property(name))

        new_cls._attrs = new_cls._attrs.copy()
        new_cls._attrs.update(new_attrs)
        new_cls._dundername = "__{}.{}__".format(new_cls.__module__, new_cls.__name__)

        return new_cls


# Manually create a base object so that we can run in both python 2 and 3.
#
#   https://wiki.python.org/moin/PortingToPy3k/BilingualQuickRef#metaclasses
BaseObject = AttrsMetaclass(str('BaseObject'), (), {
    "_attrs": {},
    "_jsonencoders": {},
    "_jsonhooks": {},
})


class Object(BaseObject):
    """
    Amethyst Base Object

    @cvar amethyst_includeclass: When True (the default), serialization will
    include a key "__class__" containing the class name of the object which
    can be used during loading to verify that the object is of the correct
    type.

    @cvar amethyst_verifyclass: When True (the default), loading data from JSON
    or a dict passed to `load_data()` will check for the "__class__" key
    described above, and an exception will be thrown if it is not found.

    @cvar amethyst_import_strategy: When "strict" (the default), then
    loading data from JSON or a dictionary via `load_data()` requires all
    keys present in the data structure to correspond with keys in the
    attribute list. If any additional keys are present, an exception will
    be raised. When "loose", additional keys will be ignored and not copied
    into the object dictionary. When "sloppy", unknown attributes will be
    copied unmodified into the object dict.
    """
    amethyst_register_type = True
    amethyst_includeclass  = True
    amethyst_verifyclass   = True
    amethyst_import_strategy = "strict"
    amethyst_classhint_style = "flat"

    def __init__(self, *args, **kwargs):
        """
        Initializes self.dict with all passed kwargs.
        Object is mutable by default.

        As a special case, Object may be initialized by a single dictionary
        argument and NO keyword arguments. This situation is intended for
        use with attribute verification. Exact behavior may change, but it
        is not expected to. Such a dictionary will simply be passed to
        `load_data()`.

        WARNING: Passing a single value to the constructor which is NOT a
        dictionary object is reserved for internal use only and behavior is
        likely to change.
        """
        super(Object, self).__init__()
        self._mutable_ = True
        self.dict = kwargs

        # Special-case of single argument:
        if len(args) == 1 and not kwargs:
            data = args[0]
            if isinstance(data, type(self)):
                # - NOT A COPY! Primary case of Object(Object()) is
                #   re-import by JSON Hook, thus we just need another view
                #   of the same data (returning the same object would also
                #   work, but I don't know how to do that, and isn't really
                #   worth it).
                #
                # - Object already one of our type, no need to merge defaults
                self.dict = data.dict
                self._mutable_ = data._mutable_
            else:
                # Just a dict passed use standard load data method
                self.load_data(data, verifyclass=False)

        for name, attr in six.iteritems(self._attrs):
            if attr.default is not None and name not in self.dict:
                self.dict[name] = attr.get_default()

    def assert_mutable(self, msg="May not modify, object is immutable"):
        if not self._mutable_:
            raise ImmutableObjectException(msg)
        return self

    def is_mutable(self):
        return self._mutable_
    def make_mutable(self):
        self._mutable_ = True
        return self
    def make_immutable(self):
        self._mutable_ = False
        return self

    def __str__(self):
        return str(self.dict)
    def __repr__(self):
        return repr(self.dict)

    def __len__(self):
        return len(self.dict)
    def __contains__(self, key):
        return key in self.dict
    def __iter__(self):
        return iter(self.dict)

    def __getitem__(self, key):
        return self.dict[key]
    def __setitem__(self, key, value):
        self.assert_mutable()
        self.dict[key] = value
    def __delitem__(self, key):
        self.assert_mutable()
        del self.dict[key]

    def get(self, key, dflt=None):
        return self.dict.get(key, dflt)

    def set(self, *args, **kwargs):
        """
        Verify then set canonicalized value. Positional args take precedence over kwargs.

            obj.set(key, val)
            obj.set(foo=val)
        """
        self.assert_mutable()
        for i in range(0, len(args), 2):
            kwargs[args[i]] = args[i+1]
        return self.dict.update(self.validate_update(kwargs))

    def setdefault(self, key, value):
        """If missing a value, verify then set"""
        self.assert_mutable()
        if key not in self.dict:
            self.set(key, value)
        return self.dict[key]

    def pop(self, key, dflt=None):
        self.assert_mutable()
        return self.dict.pop(key, dflt)

    def update(self, *args, **kwargs):
        """
        Update without verification
        """
        self.assert_mutable()
        for d in args:
            self.dict.update(d)
        if kwargs:
            self.dict.update(kwargs)
        return self

    def validate_data(self, d, import_strategy=None):
        """
        Convert and validate with the intention of updating only some of
        the object's .dict values. Returns a new dictionary with
        canonicalized values, and defaults inserted.

        This method does not change the object. Typical usage would look
        like either:

            myobj.dict = myobj.validate_data(data)

        or

            validated = myobj.validate_data(data)
            mynewobj = MyClass(**validated)

        Subclasses of `Object` can also use this method to inflate specific
        attibutes at load time. For instance, to inflate non-`Object`
        objects or ensure objects from hand-written config files. Be sure to
        override `validate_update` as well if programmatic updates may need
        special inflation rules.
        """
        strategy = coalesce(import_strategy, self.amethyst_import_strategy)
        data = d.copy() if strategy == "sloppy" else dict()
        keys = set(d.keys()) if strategy == "strict" else set()
        for name, attr in six.iteritems(self._attrs):
            keys.discard(name)
            if name in d:
                data[name] = attr(d[name], name)
            elif attr.default is not None:
                data[name] = attr.get_default()
        if keys:
            raise ValueError("keys {} not permitted in {} object".format(keys, self._dundername))
        return data

    def validate_update(self, d, import_strategy=None):
        """
        Convert and validate with the intention of updating only some of
        the object's .dict values. Returns a new dictionary with
        canonicalized values.

        This method does not change the object. Pass the resulting dict to
        the .update() method if you decide to accept the changes.
        """
        strategy = coalesce(import_strategy, self.amethyst_import_strategy)
        data = d.copy() if strategy == "sloppy" else dict()
        for key, val in six.iteritems(d):
            attr = self._attrs.get(key)
            if attr is None and strategy == "strict":
                raise ValueError("key {} not permitted in {} object".format(key, self._dundername))
            elif attr is not None:
                data[key] = attr(val, key)
        return data

    def attr_value_ok(self, name, value):
        """
        Validate a single value independently of any others. Just checks
        that the attribute validator does not raise an exception.
        """
        if name in self._attrs:
            try:
                self._attrs[name](value, name)
                return True
            except ValueError:
                return False
        return False

    def load_data(self, data, import_strategy=None, verifyclass=None):
        """
        Loads a data dictionary with validation. Modifies the passed dict
        and replaces current self.dict object with the one passed.

        @param import_strategy: Provides a local override to the `amethyst_import_strategy` class attribute.
        @param verifyclass: Provides a local override to the `amethyst_verifyclass` class attribute.

        This method transparently loads data in either "single-key" or "flat" formats:

            { "__my.module.MyClass__": { ... obj.dict ... } }

            { "__class__": "MyClass", ... obj.dict ... }

        Keep in mind that the default base value for `amethyst_verifyclass` is
        True, so, by default, at least one of the class identification keys
        is expected to be present.
        """
        self.assert_mutable()
        verifyclass = coalesce(verifyclass, self.amethyst_verifyclass)

        # We only deal in dicts here
        if isinstance(data, self.__class__):
            verifyclass = False

        if isinstance(data, Object):
            data = data.dict

        if not isinstance(data, dict):
            raise ValueError("expected dictionary object")

        # Accept data in single-key mode. Pop out the inner dict and, if
        # the indicated class name is what we expect, we can bypass the
        # class verification step.
        if 1 == len(data):
            for key in data:
                if key == self._dundername:
                    verifyclass = False# We're good
                    data = data[key]
                    if not isinstance(data, dict):
                        raise ValueError("expected dictionary object")

        # verifyclass may need to be locally overridden if the source is
        # broken. Once we do verify the class, remove it from the dict to
        # make key iteration safe.
        if verifyclass and data.get("__class__") != self._dundername:
            raise ValueError("got {} object, but expected {}".format(data.get("__class__"), self._dundername))
        data.pop("__class__", None)

        # Run the validator
        self.dict = self.validate_data(data, import_strategy=import_strategy)
        return self

    def JSONEncoder(self, obj):
        """
        Fallback method for JSON encoding.

        If the standard JSONEncoder is unable to encode an object, this
        method will be called. Per the json documentation, it should return
        an object which is JSON serializable or else raise a TypeError.

        This base encoder, looks up an object's class in a dict and calls
        the corresponding function to do the translation. The built-in
        translators map:

            set       => { "__set__": [ ... ] }
            frozenset => { "__frozenset__": [ ... ] }

        Additional translators may be added by creating a class variable
        `jsonencoders` which is a dict mapping classes to a function. These
        translators will merged onto the base translators (silently
        replacing duplicates) by the metaclass at class (not object)
        creation.
        """
        global global_amethyst_encoders

        if obj.__class__ in self._jsonencoders:
            return self._jsonencoders[obj.__class__](obj)
        elif obj.__class__ in global_amethyst_encoders:
            return global_amethyst_encoders[obj.__class__](obj)
        raise TypeError("Can't encode {}".format(repr(obj)))

    def JSONObjectHook(self, obj):
        """
        Object hook for JSON decoding.

        This method is called for every decoded JSON object. If necessary,
        it should return a new or modified object that should be used instead.

        This base encoder, translates single-key dicts into new objects if
        the single-key is a special value. The built-in translators are:

            { "__set__": [ ... ] }       => set
            { "__frozenset__": [ ... ] } => frozenset

        Additional translators may be added by creating a class variable
        `jsonhooks` which is a dict mapping the special key to a function.
        These translators will merged onto the base translators (silently
        replacing duplicates) by the metaclass at class (not object)
        creation.

        Keep in mind that JSON input comes from untrusted sources, so
        translators will need to be robust against malformed structures.
        """
        global global_amethyst_hooks
        if isinstance(obj, dict) and 1 == len(obj):
            for key in obj:
                if key in self._jsonhooks:
                    return self._jsonhooks[key](obj[key])
                elif key in global_amethyst_hooks:
                    return global_amethyst_hooks[key](obj[key])
        return obj

    def toJSON(self, includeclass=None, style=None, **kwargs):
        """
        Paramters are sent directly to json.dumps except:

        @param includeclass: When true, include a class indicator using the
          method requested by the `style` parameter. When `None` (the
          default), defer to the value of the class variable
          `amethyst_includeclass`.

        @param style: When including class, what style to use. Options are:

            * "flat" to produce a JSON string in the form:

                { "__class__": "MyClass", ... obj.dict ... }

            * "single-key" to produce a JSON string in the form:

                { "__my.module.MyClass__": { ... obj.dict ... } }

        The default style is taken from the class `amethyst_classhint_style`
        attribute.
        """
        kwargs.setdefault('default', self.JSONEncoder)
        includeclass = coalesce(includeclass, self.amethyst_includeclass)
        style = coalesce(style, self.amethyst_classhint_style)
        popclass = False

        try:
            dump = self.dict
            if includeclass:
                if style == "flat":
                    popclass = True
                    self.dict["__class__"] = self._dundername
                elif style == "single-key":
                    dump = { self._dundername: self.dict }
                else:
                    raise AmethystException("Unknown class style '{}'".format(style))
            rv = json.dumps(dump, **kwargs)
        finally:
            if popclass:
                self.dict.pop("__class__", None)
        return rv

    @classmethod
    def newFromJSON(cls, data, import_strategy=None, verifyclass=None, **kwargs):
        self = cls()
        mutable = self.is_mutable()# In case some subclass is default immutable
        if not mutable: self.make_mutable()
        self.fromJSON(data, import_strategy=import_strategy, verifyclass=verifyclass, **kwargs)
        if not mutable: self.make_immutable()
        return self

    def fromJSON(self, data, import_strategy=None, verifyclass=None, **kwargs):
        """
        Paramters are sent directly to json.loads except:

        @param import_strategy: Provides a local override to the `amethyst_import_strategy` class attribute.
        @param verifyclass: Provides a local override to the `amethyst_verifyclass` class attribute.
        """
        kwargs.setdefault('object_hook', self.JSONObjectHook)
        return self.load_data(json.loads(data, **kwargs), import_strategy=import_strategy, verifyclass=verifyclass)
