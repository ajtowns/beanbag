#!/usr/bin/env python

import py.test
from beanbag.v2 import BeanBag, GET, POST, PUT, PATCH, DELETE
import json
from fake_req import FakeSession, _Any

def test_bb():
    s = FakeSession()
    b = BeanBag("http://www.example.org/path/", session=s)

    assert str(b) == "http://www.example.org/path/"

    s.expect("GET", "http://www.example.org/path/")
    GET(b)

    s.expect("GET", "http://www.example.org/path/", params=dict(a=1, b=2))
    GET(b(a=1, b=2))

    s.expect("PUT", "http://www.example.org/path/")
    PUT(b._, None)

    s.expect("PATCH", "http://www.example.org/path/")
    PATCH(b._, None)

    s.expect("DELETE", "http://www.example.org/path/")
    DELETE(b._)

    s.expect("POST", "http://www.example.org/path/foo", data={"a": 1})
    POST(b.foo, dict(a=1))

