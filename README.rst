
amethyst-core
=============

A sober python base library for python 3. (`Full Documentation`_)

.. _`Full Documentation`: https://python-amethyst-core.readthedocs.io/en/latest/index.html

.. CAUTION:: EXPERIMENTAL CODE. The interface to this library is not yet
   stable. At this time, improvements will be made to the interface without
   regard to backward compatibility. Backward-incompatible changes will not
   necessarily be documented in the changelog, and changes may be added
   which eat your puppy.


A Generic Serializable Object
-----------------------------

The primary product of this module is a base python object class designed
for easy serialization. JSON serialization and de-serialization come for
free for attributes of (most of the) core python object types.

A Basic Class:

.. code:: python

   from amethyst.core import Object, Attr

   class MyObject(Object):
       foo = Attr(int)
       bar = Attr(isa=str).strip()

   myobj = MyObject(foo="23")
   print(myobj.foo + 1)      # => 24


Validation / Coersion
^^^^^^^^^^^^^^^^^^^^^

.. code:: python

   class MyObject(Object):
       amethyst_verifyclass = False  # don't check json for class name
       foo = Attr(int)               # coerce to int
       bar = Attr(isa=str).strip()   # ensure str then strip whitespace


Validated
"""""""""

* constructors

  .. code:: python

     myobj = MyObject({ "foo": "23", "bar": "Hello " })
     myobj = MyObject(foo="23", bar="Hello ")
     print(isinstance(myobj.foo, int))     # True
     print(myobj.bar)                      # "Hello"

* assignment

  .. code:: python

     myobj["foo"] = "23"                   # Converts to int
     myobj["foo"] = "Not an int"           # Raises exception
     myobj.foo = "23"                      # Converts to int
     myobj.foo = "Not an int"              # Raises exception

* set and update methods

  .. code:: python

     myobj.set("foo", value)               # Convert to int or raise exception
     myobj.update(foo=value)               # Convert to int or raise exception
     myobj.setdefault("foo", value)        # Convert or raise only if foo unset

* loading fresh from dict or json

  .. code:: python

     # Converts and trims
     myobj.load_data({"foo": "23", "bar": "Hello "})

     # Converts and trims
     myobj = MyObject.newFromJSON('{"foo": "23", "bar": "Hello "}')
     myobj.fromJSON('{"foo": "23", "bar": "Hello "}')


Not Validated
"""""""""""""

  .. code:: python

     myobj.direct_set("foo", "Not an int")     # DANGER: Not an exception!
     myobj.direct_update(foo="Not an int")     # DANGER: Not an exception!


Serialization
^^^^^^^^^^^^^

JSON text can be produced and loaded, even for nested objects.

.. code:: python

   json_string = myobj.toJSON()
   myobj2 = MyObject.newFromJSON(json_string)

Other serialization libraries can easily be used as well.

.. code:: python

   yaml_string = yaml.dump(myobj.deflate_data())
   myobj2 = MyObject.inflate_new(yaml.safe_load(yaml_string))


By default the JSON serializer injects type hints to ensure that objects
are de-serialized into the correct class:

.. code:: python

   # print(MyObject(foo=23, bar="plugh").toJSON())
   {"__class__": "__mymodule.MyObject__", "foo": 23, "bar": "plugh"}

When building an object from JSON, the constructor will look for these
hints and raise a ValueError if the type hint is missing or imported into
the wrong class.

.. code:: python

   # These raise ValueError
   MyObject.newFromJSON('{"foo":23, "bar":"plugh"}')
   MyObject.newFromJSON('{"__class__": "__mymodule.MyOtherObject__", "foo":23}')

Class verification can be skipped by passing `verifyclass=False` to the loader.

.. code:: python

   myobj = MyObject.newFromJSON('{"foo":23, "bar":"plugh"}', verifyclass=False)


If you want no munging or class verification at all, set the class parameters:

.. code:: python

   class MyObject(Object):
       amethyst_includeclass  = False
       amethyst_verifyclass   = False

       foo = Attr(int)
       bar = Attr(isa=str).strip()

   # No extra class info due to modified defaults:
   myobj = MyObject.newFromJSON('{"foo":"23", "bar":"plugh"}')
   print(myobj.toJSON())
   # => { "foo": 23, "bar": "plugh" }


Ecosystem integration
---------------------

Works with `sqlite3.Row` objects:

.. code:: python

    import sqlite3
    conn = sqlite3.connect(myfile)
    conn.row_factory = sqlite3.Row
    for row in conn.execute('SELECT * FROM mytable')
        obj = MyObject(row)
        ...

Works with `six.iteritems()`:

.. code:: python

    import six
    for k, v in six.iteritems(myobj):
        ...
