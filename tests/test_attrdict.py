#!/usr/bin/env python

import py.test
from beanbag.attrdict import AttrDict
import json

j = json.loads('{"a": 1, "b": "blat", "c": {"d": "e"}}')
ad = AttrDict(j)

def test_manipulation():
    assert ad.c.d == "e"
    assert repr(ad.foo.bar) == "<AttrDict(foo.bar)>"

    ad.foo.bar = "hello"
    ad.foo.bar += ", world"
    ad.foo.baz = "yaarrrr"

    assert +ad.foo == {"bar": "hello, world", "baz": "yaarrrr"}
    py.test.raises(KeyError, "str(ad.c.x.y.z)")

    ad.c.x.y.z = 3
    assert ad.c.x.y.z == 3
    del ad.foo.bar
    assert +ad.foo == {"baz": "yaarrrr"}
    print(+ad)
    del ad.foo

    del ad.c.x
    assert +ad == {"a": 1, "b": "blat", "c": {"d": "e"}}

    py.test.raises(KeyError, "del ad.bar.baz")

    assert +ad is j
