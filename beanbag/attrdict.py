#!/usr/bin/env python

from . import namespace


class AttrDict(namespace.SettableHierarchialNS):
    """Allow access to dictionary via attributes as well as
       array-style references."""

    def __init__(self, base=None):
        """Provide an AttrDict view of a dictionary.

        :param base: dictionary/list to be viewed
        """

        if base is None:
            self.base = {}
        else:
            self.base = base

    def repr(self, path):
        return "<%s(%s)>" % (self.Namespace.__name__, ".".join(map(str, path)))

    def item(self, item):
        return item

    def descend(self, path, create=True):
        base = self.base
        for p in path:
            try:
                base = base[p]
            except:
                if isinstance(create, type) and issubclass(create, Exception):
                    raise create(p)
                elif create and isinstance(base, dict):
                    base[p] = {}
                    base = base[p]
                elif not create:
                    return None
                else:
                    raise
        return base

    def pos(self, path):
        """View underlying dict object"""

        return self.descend(path, create=KeyError)

    def str(self, path):
        return str(self.pos(path))

    def get(self, path):
        o = self.descend(path, create=False)
        if isinstance(o, dict) or isinstance(o, list) or o is None:
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
        p = self.pos(path)
        if isinstance(p, list):
            return (self.namespace(path + (i,)) for i in range(len(p)))
        else:
            return self.pos(path).__iter__()

    def len(self, path):
        return self.pos(path).__len__()

