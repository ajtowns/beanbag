#!/usr/bin/env python

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

    def request(self, verb, path, params=None, data=None, headers=None):
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
