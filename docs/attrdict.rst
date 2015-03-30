.. module:: beanbag.attrdict

beanbag.attrdict -- Access dict members by attribute
====================================================

AttrDict
--------

This module provides the ``AttrDict`` class, which allows you to
access dict members via attribute access, allowing similar syntax to
javascript objects. For example:

.. code:: python

   d = {"foo": 1, "bar": {"sub": {"subsub": 2}}}
   ad = AttrDict(d)
   assert ad["foo"] == ad["foo"]
   assert ad.foo == 1
   assert ad.bar.sub.subsub == 2

Note that ``AttrDict`` simply provides a view on the native dict. That dict
can be obtained using the plus operator like so:

.. code:: python

   ad = AttrDict(d)
   assert +ad is d

This allows use of native dict methods such as ``d.update()`` or
``d.items()``. Note that attribute access binds more tightly than plus,
so brackets will usually need to be used, eg: ``(+ad.bar).items()``.

An ``AttrDict`` can also be directly used as an iterator (``for key in
attrdict: ...``) and as a container (``if key in attrdict: ...``).

.. autoclass:: AttrDict
   :members:
   :exclude-members: .base
   :special-members:

