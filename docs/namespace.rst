.. module:: beanbag.namespace

beanbag.namespace
=================

The beanbag.namespace module allows defining classes that provide
arbitrary namespace behaviour. This is what allows the other beanbag
modules to provide their clever syntactic sugar.

A entry in a namespace is identified by two components: a base and a path.
The base is constructed once for a namespace and is common to all entries
in the namespace, and each entry's path is used to differentiate them. For
example, with ``AttrDict``, the base is the underlying dictionary
(``d``), while the path is the sequence of references into that dictionary
(eg, ``("foo", "bar")`` corresponding to ``d["foo"]["bar"]``). The reason
for splitting these apart is mostly efficiency -- the path element needs
to be cheap and easy to construct and copy since that may need to happen
for an attribute access.

To define a namespace you provide a class that inherits from
``beanbag.namespace.Namespace`` and defines the methods the base class
should have. The ``NamespaceMeta`` metaclass then creates a new base
class containing these methods, and builds the namespace class on
top of that base class, mapping Python's special method names to the
corresponding base class methods, minus the underscores. For example,
to define the behavour of the ``~`` operator (aka ``__invert__(self)``),
the Base class defines a method:

.. code:: python

   def invert(self, path):
       ...

The code can rely on the base value being ``self``, and the path being
``path``, then do whatever calculation is necessary to create a result. If
that result should be a different entry in the same namespace, that can
be created by invoking ``self.namespace(newpath)``.

In order to make inplace operations work more smoothly, returning
``None`` from those options will be automatically treated as returning
the original namespace object (ie ``self.namespace(path)``, without the
overhead of reconstructing the object). This is primarily to make it easier
to avoid the "double setting" behaviour of python's inplace operations, ie
where ``a[i] += j`` is converted into:

.. code:: python

   tmp = a.__getitem__(i)   # tmp = a[i]
   res = tmp.__iadd__(j)    # tmp += j
   a.__setitem__(i, res)    # a[i] = tmp

In particular, implementations of ``setitem`` and ``setattr`` can avoid
poor behaviour here by testing whether the value being set (``res``)
is already the existing value, and performing a no-op if so. The
``SettableHierarchialNS`` class implements this behaviour.

NamespaceMeta
-------------

The ``NamespaceMeta`` metaclass provides the magic for creating arbitrary
namespaces from Base classes as discussed above. When set as the metaclass
for a class, it will turn a base class into a namespace class directly,
while constructing an appropriate base class for the namespace to use.

.. autoclass:: NamespaceMeta
   :members:
   :special-members:
   :undoc-members:

NamespaceBase
-------------

The generated base class will inherit from ``NamespaceBase``
(or the base class corresponding to any namespaces the namespace class
inherits from), and will have a ``Namespace`` attribute referencing the
namespace class. Further, the generated base class can be accessed by
using the inverse opertor on the namespace class, ie ``MyNamespaceBase
= ~MyNamespace``.

.. autoclass:: NamespaceBase
   :members:

Namespace
---------

``Namespace`` provides a trivial Base implementation. It's primarily
useful as a parent class for inheritance, so that you don't have
explicitly set ``NamespaceMeta`` as your metaclass.

.. autoclass:: Namespace
   :members:

HierarchialNS
-------------

``HierarchialNS`` provides a simple basis for producing namespaces with
freeform attribute and item hierarchies, eg, where you might have something
like ``ns.foo.bar["baz"]``.

By default, this class specifies a path as a tuple of attributes, but this
can be changed by overriding the ``path`` and ``_get`` methods. If some
conversion is desired on either attribute or item access, the ``attr``
and ``item`` methods can be overridden respectively.

Otherwise, to get useful behaviour from this class, you probably want to
provide some additional methods, such as ``__call__``.

.. autoclass:: HierarchialNS
   :exclude-members: .base
   :show-inheritance:
   :members:
   :special-members:
   :undoc-members:

SettableHierarchialNS
---------------------

``SettableHierarchialNS`` is intended to make life slightly easier if you
want to be able to assign to your hierarchial namespace. It provides ``set``
and ``delete`` methods that you can implement, without having to go to the
trouble of implementing both item and attribute variants of both functions.

This class implements the check for "setting to self" mentioned earlier in
order to prevent inplace operations having two effects. It uses the ``eq``
method to test for equality.

.. autoclass:: SettableHierarchialNS
   :show-inheritance:
   :exclude-members: .base
   :members:
   :special-members:
   :undoc-members:

sig_adapt
---------

This is a helper function to make that generated methods in the namespace
object provide more useful help.

.. autofunction:: sig_adapt
