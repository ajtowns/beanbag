#!/usr/bin/env python

import inspect
import functools
import sys


def sig_adapt(sigfn, dropargs=None, name=None):
    """Function decorator that changes the name and (optionally) signature
       of a function to match another function. This is useful for
       making the help of generic wrapper functions match the functions
       they're wrapping. For example:

       .. code::

          def foo(a, b, c, d=None):
              pass

          @sig_adapt(foo)
          def myfn(*args, **kwargs):
              pass

       The optional "name" parameter allows renaming the function to something
       different to the original function's name.

       The optional "dropargs" parameter allows dropping arguments by
       position or name.  (Note positions are 0 based, so to convert
       foo(self, a, b) to foo(a, b) specify dropargs=("self",) or
       dropargs=(0,))
    """

    # Python 3.3+, PEP 362
    if hasattr(inspect, "signature"):
        def adapter(fn):
            sig = inspect.signature(sigfn)
            if dropargs is not None:
                newparams = [p
                        for i, (name, p) in enumerate(sig.parameters.items())
                        if i not in dropargs and name not in dropargs]
                sig = sig.replace(parameters=newparams)

            functools.update_wrapper(fn, sigfn)
            if name is not None:
                fn.__name__ = name
            fn.__signature__ = sig
            return fn
        return adapter

    # Pre Python 3.3
    def adapter(fn):
        spec = list(inspect.getargspec(sigfn))
        if dropargs is not None:
            posargs = [arg for i, arg in enumerate(spec[0])
                    if i not in dropargs and arg not in dropargs]
            if len(spec) >= 4 and spec[3]:
                odefs = spec[3]
                nodefs = len(spec[0]) - len(odefs)
                defs = [odefs[i] for i, arg in enumerate(spec[0][-len(odefs):])
                        if i + nodefs not in dropargs and arg not in dropargs]
            else:
                defs = []

            spec = [posargs, spec[1], spec[2], defs]

        fargs = inspect.formatargspec(*spec)
        fargs = fargs.lstrip("(").rstrip(")")
        bfargs = inspect.formatargspec(*(spec[:3]))
        # eval is the only way to preserve function signature
        # prior to PEP 362 included in py3.3
        # (note that bfargs needs to drop any default values for arguments)
        l = "lambda %s: fn%s" % (fargs, bfargs)
        fn = eval(l, dict(fn=fn))
        functools.update_wrapper(fn, sigfn)
        if name is not None:
            fn.__name__ = name
        return fn

    return adapter


class NamespaceMeta(type):
    # attr ops are special because we have magic ".base" and ".path" attributes
    ops_attr = ["getattr", "setattr", "delattr"]

    # number ops are special since they have reverse and inplace variants
    __ops_num = "add sub mul pow div floordiv lshift rshift and or xor".split()

    ops_inum = ["i" + _x for _x in __ops_num]

    # other ops
    ops = ("repr str call bool"   # standard
           " getitem setitem delitem len iter reversed contains"   # container
           " enter exit"          # context
           " pos neg invert"      # unary
           " eq ne lt le gt ge"   # comparsion
           # "cmp rcmp hash unicode", # maybe should do these too?
          ).split() + __ops_num + ["r" + _x for _x in __ops_num]

    def __new__(mcls, name, bases, nmspc):
        basebases = tuple(~cls for cls in bases if isinstance(cls, mcls))
        if not basebases:
            basebases = (NamespaceBase,)

        qn = None
        if "__qualname__" in nmspc:
            qn = nmspc["__qualname__"]
            nmspc["__qualname__"] = qn + "Base"

        basecls = type.__new__(type, name + "Base", basebases, nmspc)

        conv_nmspc = mcls.make_namespace(basecls)

        if "__module__" in nmspc:
            conv_nmspc["__module__"] = nmspc["__module__"]
        if qn is not None:
            conv_nmspc["__qualname__"] = qn

        cls = type.__new__(mcls, name, bases, conv_nmspc)
        basecls.Namespace = cls

        return cls

    def __invert__(cls):
        """Obtain base class for namespace"""
        return getattr(cls, ".base")

    @staticmethod
    def wrap_path_fn(basefn):
        def fn(self, *args, **kwargs):
            return basefn(getattr(self, ".base"), getattr(self, ".path"),
                          *args, **kwargs)
        return fn

    @staticmethod
    def wrap_path_fn_inum(basefn):
        def fn(self, *args, **kwargs):
            r = basefn(getattr(self, ".base"), getattr(self, ".path"),
                       *args, **kwargs)
            if r is None:
                r = self
            return r
        return fn

    @staticmethod
    def wrap_path_fn_attr(basefn):
        def fn(self, attr, *args, **kwargs):
            if attr.startswith("."):
                return object.__setattr__(self, attr, *args, **kwargs)
            return basefn(getattr(self, ".base"), getattr(self, ".path"), attr, *args, **kwargs)
        return fn

    @classmethod
    def deferfn(mcls, cls, nsdict, basefnname, inum=False, attr=False):
        if not hasattr(cls, basefnname):
            return   # not implemented so nothing to do

        basefn = getattr(cls, basefnname)

        if inum:
            fn = mcls.wrap_path_fn_inum(basefn)
        elif attr:
            fn = mcls.wrap_path_fn_attr(basefn)
        else:
            fn = mcls.wrap_path_fn(basefn)

        fname = "__%s__" % (basefnname,)
        if basefnname == "bool" and sys.version_info[0] == 2:
            fname = "__nonzero__"

        fn = sig_adapt(basefn, dropargs=(1,), name=fname)(fn)

        nsdict[fname] = fn

    @classmethod
    def make_namespace(mcls, cls):
        """create a unique Namespace class based on provided class"""

        clsnmspc = {}

        for op in mcls.ops:
            mcls.deferfn(cls, clsnmspc, op)

        for op in mcls.ops_inum:
            mcls.deferfn(cls, clsnmspc, op, inum=True)

        for op in mcls.ops_attr:
            mcls.deferfn(cls, clsnmspc, op, attr=True)

        def init(self, *args, **kwargs):
            b = cls(*args, **kwargs)
            setattr(self, ".base", b)
            setattr(self, ".path", b.path())
        if "__init__" in cls.__dict__:
            init = sig_adapt(cls.__init__)(init)
        clsnmspc["__init__"] = init

        clsnmspc[".base"] = cls

        return clsnmspc


class NamespaceBase(object):
    """Base class for user-defined namespace classes' bases"""

    Namespace = None
    """Replaced in subclasses by the corresponding namespace class"""

    def namespace(self, path=None):
        """Used to create a new Namespace object from the Base class"""
        if path is None:
            path = self.path()
        r = self.Namespace.__new__(self.Namespace)
        setattr(r, ".base", self)
        setattr(r, ".path", path)
        return r


# setup base class so can use metaclass via inheritance
# (this is the only common syntax for using metaclasses that works
# with both py2 and py3)
Namespace = NamespaceMeta.__new__(NamespaceMeta, "Namespace", (object,), {})


class HierarchialNS(Namespace):
    def __init__(self):
        pass

    def path(self):
        """Returns empty path"""
        return ()

    def _get(self, path, el):
        """Returns updated path when new component is added"""
        return path + (el,)

    def str(self, path):
        """Returns path joined by dots"""
        return ".".join(str(x) for x in path)

    def repr(self, path):
        """Human readable representation of object"""
        return "<%s(%s)>" % (self.__class__.__name__, self.str(path))

    def eq(self, path, other):
        """self == other"""
        if isinstance(other, self.Namespace):
            return other.__eq__((self, path))
        elif isinstance(other, tuple) and len(other) == 2:
            oself, opath = other
            return self is oself and path == opath
        else:
            return False

    def ne(self, path, other):
        """self != other"""
        return not self.eq(path, other)

    def get(self, path):
        return self.namespace(path)

    def item(self, item):
        """Applies any conversion needed for items (self[item])"""
        return str(item)

    def attr(self, attr):
        """Applies any conversion needed for attributes (self.attr)"""
        return str(attr)

    def getattr(self, path, attr):
        """self.attr"""
        return self.get(self._get(path, self.attr(attr)))

    def getitem(self, path, item):
        """self[attr]"""
        return self.get(self._get(path, self.item(item)))


class SettableHierarchialNS(HierarchialNS):
    def set(self, path, val):
        """self.path = val or self[path] = val"""
        raise NotImplementedError

    def delete(self, path):
        """del self.path or del self[path]"""
        raise NotImplementedError

    def _set(self, path, val):
        """Helper function to avoid calling self.set() when doing inum ops

           Normally python will convert:
               self.path += val
           into
               a = self.path
               self.path = a.__iadd__(val)
           which is useful if __iadd__ doesn't just return self, but not
           desirable here
        """

        if self.eq(path, val):
            return None
        return self.set(path, val)

    def setattr(self, path, attr, val):
        """self.attr = val"""
        return self._set(self._get(path, self.attr(attr)), val)

    def setitem(self, path, item, val):
        """self[item] = val"""
        return self._set(self._get(path, self.item(item)), val)

    def delattr(self, path, attr):
        """del self.attr"""
        return self.delete(self._get(path, self.attr(attr)))

    def delitem(self, path, item):
        """del self[item]"""
        return self.delete(self._get(path, self.item(item)))

