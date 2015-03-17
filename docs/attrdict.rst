beanbag.attrdict -- Access dict members by attribute
====================================================

This module allows you to access dict members via attribute access,
allowing similar syntax to javascript. For example:

.. code::
   d = {"foo": 1, "bar": {"sub": {"subsub": 2}}}
   ad = AttrDict(d)
   assert ad.foo == 1
   assert ad.bar.sub.subsub == 2

Classes and Variables
---------------------

.. automodule:: beanbag.attrdict
   :members:
   :undoc-members:

