#!/usr/bin/env python

import pytest
from beanbag.v2 import BeanBag, BeanBagException, GET, POST, PUT, PATCH, DELETE
from beanbag.attrdict import AttrDict
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

    s.expect("GET", "http://www.example.org/path/", params=dict(status=300))
    with pytest.raises(BeanBagException) as e:
        GET(b(status=300))
    assert "Bad response code: 300" == e.value.msg

    s.expect("GET", "http://www.example.org/path/", params=dict(result="BAD"))
    with pytest.raises(BeanBagException) as e:
        GET(b(result="BAD"))
    assert "Could not decode response" == e.value.msg

def test_sane_inheritance():
    class MyBeanBag(BeanBag):
        def helper(self, param):
            pass

        def encode(self, body):
            return super(~MyBeanBag, self).encode(body)

        def decode(self, response):
            return super(~MyBeanBag, self).decode(response)

    s = FakeSession()
    bb = MyBeanBag("http://www.example.org/path", session=s)

    assert type(bb) is MyBeanBag
    assert type(bb.subpath) is MyBeanBag
    assert type(bb[1]) is MyBeanBag

    assert hasattr(~MyBeanBag, "helper")

    s.expect("GET", "http://www.example.org/path/")
    GET(bb)

    s.expect("POST", "http://www.example.org/path/foo", data={"a": 1})
    r = POST(bb.foo, dict(a=1))
    assert type(r) is AttrDict
    assert r.data == '{"a": 1}' and r.method == 'POST'
