#!/usr/bin/env python

import py.test
import beanbag.v1 as beanbag
import json
from fake_req import FakeSession, _Any

def test_bb():
    s = FakeSession()
    b = beanbag.BeanBag("http://www.example.org/path/", session=s)

    assert str(b) == "http://www.example.org/path/"

    s.expect("GET", "http://www.example.org/path/")
    q = b()

    s.expect("GET", "http://www.example.org/path/", params=dict(a=1, b=2))
    q = b(a=1, b=2)

    s.expect("PUT", "http://www.example.org/path/")
    b._ = None

    s.expect("PATCH", "http://www.example.org/path/")
    b._ += None

    s.expect("DELETE", "http://www.example.org/path/")
    del b._

    s.expect("POST", "http://www.example.org/path/foo", data={"a": 1})
    q = b.foo(dict(a=1))

    s.expect("GET", "http://www.example.org/path/foo", params={"result": "/*INVALID*/"})
    try:
        q = b.foo(result="/*INVALID*/")
        assert False, "should have raised exception"
    except beanbag.BeanBagException as e:
        assert e.msg == "Could not decode response"

