#!/usr/bin/env python

from . import namespace


class AttrDict(namespace.SettableHierarchialBase):
    """Allow access to dictionary via attributes as well as
       array-style references."""

    def __init__(self, basedict=None):
        """Provide an AttrDict view of a dictionary.

        :param basedict: dictionary to be viewed
        """

        if basedict is None:
            self.basedict = {}
        else:
            self.basedict = basedict

    def repr(self, path):
        return "<%s(%s)>" % (self.Namespace.__name__, ".".join(map(str, path)))

    def descend(self, path, create=True):
        base = self.basedict
        for p in path:
            if p not in base:
                if isinstance(create, type) and issubclass(create, Exception):
                    raise create(p)
                elif create:
                    base[p] = {}
                else:
                    return None
            base = base[p]
        return base

    def pos(self, path):
        """View underlying dict object"""

        return self.descend(path, create=KeyError)

    def str(self, path):
        return str(self.pos(path))

    def get(self, path):
        o = self.descend(path, create=False)
        if isinstance(o, dict) or o is None:
            return self.namespace(path)
        else:
            return o

    def set(self, path, val):
        o = self.descend(path[:-1])
        o[path[-1]] = val

    def delete(self, path):
        o = self.descend(path[:-1], create=KeyError)
        del o[path[-1]]

    def eq(self, path, other):
        """self == other"""

        try:
            return other == (self.pos(path))
        except KeyError:
            return False

    def contains(self, path, val):
        return val in self.pos(path)

    def iter(self, path):
        return self.pos(path).__iter__()

    def len(self, path):
        return self.pos(path).__len__()

