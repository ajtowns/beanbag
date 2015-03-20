#!/usr/bin/env python

import py.test
import beanbag.v1 as beanbag
import json

class FakeResponse(object):
    def __init__(self, status_code=200, content={}):
        self.headers = {"content-type": "application/json"}
        self.text = self.content = json.dumps(content)
        self.status_code = status_code

_Any = object()

class FakeSession(object):
    def __init__(self):
        self.headers = {}
        self.expecting = None

    def expect(self, verb, path, params=None, data=None):
        assert self.expecting is None, "Missed request"
        self.expecting = (verb, path, params, data)

    def request(self, verb, path, params=None, data=None):
        assert self.expecting is not None, \
                "Unexpected request: %s %s %s %s" % (verb, path, params, data)

        exp_verb, exp_path, exp_params, exp_data = self.expecting
        self.expecting = None

        if data is not None:
            dec_data = json.loads(data)
        else:
            dec_data = None

        if exp_verb is _Any: exp_verb = verb
        if exp_path is _Any: exp_path = path
        if exp_params is _Any: exp_params = params
        if exp_data is _Any: exp_data = dec_data

        if exp_params is None and params == {}:
            exp_params = {}
        if exp_params == {} and params is None:
            exp_params = None

        assert exp_verb == verb and exp_path == path and exp_params == params and exp_data == dec_data

        res_obj = dict(verb=verb, path=path, params=params, data=data)
        return FakeResponse(content = res_obj)

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

