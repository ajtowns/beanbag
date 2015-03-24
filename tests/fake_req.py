#!/usr/bin/env python

import json

class FakeResponse(object):
    def __init__(self, status_code=200, content={}):
        if not isinstance(content, str):
            content = json.dumps(content)

        self.headers = {"content-type": "application/json"}
        self.text = self.content = content
        self.status_code = status_code

_Any = object()

class FakeSession(object):
    def __init__(self):
        self.headers = {}
        self.expecting = None

    def expect(self, method, url, params=None, data=None):
        assert self.expecting is None, "Missed request"
        self.expecting = (method, url, params, data)

    def merge_environment_settings(self, *args, **kwargs):
        return {}

    def prepare_request(self, req):
        assert req.json is None and req.files == []
        return req

    def send(self, request, **kwargs):
        assert not kwargs
        assert isinstance(request.data, str) or request.data == []
        data = request.data
        if not data:
            data = None

        return self.request(
                method=request.method,
                url=request.url,
                params=request.params,
                data=data,
                headers=request.headers)

    def request(self, method, url, params=None, data=None, headers=None):
        assert self.expecting is not None, \
                "Unexpected request: %s %s %s %s" % (method, url, params, data)

        exp_method, exp_url, exp_params, exp_data = self.expecting
        self.expecting = None

        if data is not None:
            dec_data = json.loads(data)
        else:
            dec_data = None

        if exp_method is _Any: exp_method = method
        if exp_url is _Any: exp_url = url
        if exp_params is _Any: exp_params = params
        if exp_data is _Any: exp_data = dec_data

        if exp_params is None and params == {}:
            exp_params = {}
        if exp_params == {} and params is None:
            exp_params = None

        assert exp_method == method and exp_url == url and exp_params == params and exp_data == dec_data

        res_obj = dict(method=method, url=url, params=params, data=data)
        status_code = 200

        if params and "status" in params:
            status_code = int(params["status"])
        if params and "result" in params:
            res_obj = str(params["result"])

        return FakeResponse(status_code=status_code, content=res_obj)
