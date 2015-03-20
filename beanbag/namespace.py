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
                        if i+nodefs not in dropargs and arg not in dropargs]
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
    # number ops are special since they have reverse and inplace variants
    num_ops = "add sub mul pow div floordiv lshift rshift and or xor".split()

    inum_ops = ["i"+_x for _x in num_ops]

    ops = ("repr str call bool"   # standard
           " getitem setitem delitem len iter reversed contains"   # container
           " enter exit"          # context
           " pos neg invert"      # unary
           " eq ne lt le gt ge"   # comparsion
           # "cmp rcmp hash unicode", # maybe should do these too?
          ).split() + num_ops + ["r"+_x for _x in num_ops]

    def __new__(mcls, name, bases, nmspc):
        if "__namespace_name__" in nmspc:
            clsname = name
            nsname = nmspc["__namespace_name__"]
        else:
            if "__no_clever_meta__" in nmspc:
                clsname = name
                nsname = name + "NS"
            else:
                clsname = name + "Base"
                nsname = name

        cls = type.__new__(mcls, clsname, bases, nmspc)
        if clsname != name and sys.version_info[0] > 2:
            cls.__qualname__ = clsname

        NS, new = mcls.make_namespace(cls, name=nsname)
        cls.Namespace = NS
        cls.namespace = new

        if "__no_clever_meta__" in nmspc:
            return cls
        else:
            return NS

    @classmethod
    def deferfn(mcls, cls, nscls, basefnname, inplace=False):
        if not hasattr(cls, basefnname):
            return   # not implemented so nothing to do

        basefn = getattr(cls, basefnname)

        if not inplace:
            def fn(self, *args, **kwargs):
                return basefn(self._Namespace__base, self._Namespace__path,
                              *args, **kwargs)
        else:
            def fn(self, *args, **kwargs):
                r = basefn(self._Namespace__base, self._Namespace__path,
                           *args, **kwargs)
                if r is None:
                    r = self
                return r

        fname = "__%s__" % (basefnname,)
        if basefnname == "bool" and sys.version_info[0] == 2:
            fname = "__nonzero__"

        fn = sig_adapt(basefn, dropargs=(1,), name=fname)(fn)

        setattr(nscls, fname, fn)
        return fn

    @classmethod
    def make_namespace(mcls, cls, name=None):
        """create a unique Namespace class based on provided class"""

        if name is None:
            name = cls.__name__

        class Namespace(object):
            __slots__ = ("__base", "__path")
            __basecls = cls

            if hasattr(cls, "getattr"):
                @sig_adapt(cls.getattr, dropargs=(1,), name="__getattr__")
                def __getattr__(self, a):
                    if a.startswith("_Namespace__") or a.startswith("__"):
                        raise AttributeError(
                                "%s object '%s' has no attribute '%s'" %
                                  (self.__class__.__name__, repr(self), a))
                    r = self.__base.getattr(self.__path, a)
                    return r

            if hasattr(cls, "setattr"):
                @sig_adapt(cls.setattr, dropargs=(1,), name="__setattr__")
                def __setattr__(self, a, val):
                    if a.startswith("_Namespace__") or a.startswith("__"):
                        return object.__setattr__(self, a, val)
                    return self.__base.setattr(self.__path, a, val)

            if hasattr(cls, "delattr"):
                @sig_adapt(cls.delattr, dropargs=(1,), name="__delattr__")
                def __delattr__(self, a):
                    if a.startswith("_Namespace__") or a.startswith("__"):
                        return object.__delattr__(self, a)
                    return self.__base.delattr(self.__path, a)

        for op in mcls.ops:
            mcls.deferfn(cls, Namespace, op)

        for op in mcls.inum_ops:
            mcls.deferfn(cls, Namespace, op, inplace=True)

        def init(self, *args, **kwargs):
            self._Namespace__base = cls(*args, **kwargs)
            self._Namespace__path = self._Namespace__base.path()
        if "__init__" in cls.__dict__:
            init = sig_adapt(cls.__init__)(init)
        Namespace.__init__ = init

        Namespace.__name__ = name
        Namespace.__qualname__ = name
        Namespace.__module__ = cls.__module__

        def namespace(self, path=None):
            """Used to create a new Namespace object from the Base class"""
            if path is None:
                path = self.path()
            r = Namespace.__new__(Namespace)
            r._Namespace__base = self
            r._Namespace__path = path
            return r

        return Namespace, namespace


# setup base class so can use metaclass via inheritance
# (this is the only common syntax for using metaclasses that works
# with both py2 and py3)
NamespaceBase = type.__new__(NamespaceMeta, "NamespaceBase", (object,), {})


class HierarchialBase(NamespaceBase):
    __no_clever_meta__ = True

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


class SettableHierarchialBase(HierarchialBase):
    __no_clever_meta__ = True

    def set(self, path, val):
        """self.path = val or self[path] = val"""
        raise NotImplementedError

    def delete(self, path):
        """del self.path or del self[path]"""
        raise NotImplementedError

    def __set(self, path, val):
        # helper function to avoid calling self.set() when doing inplace ops
        # Normally python will convert:
        #     self.path += val
        # into
        #     a = self.path
        #     self.path = a.__iadd__(val)
        # which is useful if __iadd__ doesn't just return self, but not
        # desirable here

        if self.eq(path, val):
            return None
        return self.set(path, val)

    def setattr(self, path, attr, val):
        """self.attr = val"""
        return self.__set(self._get(path, self.attr(attr)), val)

    def setitem(self, path, item, val):
        """self[item] = val"""
        return self.__set(self._get(path, self.item(item)))

    def delattr(self, path, attr):
        """del self.attr"""
        return self.delete(self._get(path, self.attr(attr)))

    def delitem(self, path, item):
        """del self[item]"""
        return self.delete(self._get(path, self.item(item)))

