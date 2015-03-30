#!/usr/bin/env python

# Copyright (c) 2014 Red Hat, Inc. and/or its affiliates.
# Copyright (c) 2015 Anthony Towns
# Written by Anthony Towns <aj@erisian.com.au>
# See LICENSE file.

from __future__ import print_function

from .namespace import SettableHierarchialNS
from .bbexcept import BeanBagException

import requests

try:
    import json
except ImportError:
    import simplejson as json


__all__ = ['BeanBag', 'BeanBagException']


class BeanBag(SettableHierarchialNS):
    def __init__(self, base_url, ext="", session=None,
                 fmt='json'):
        """Create a BeanBag referencing a base REST path.

           :param base_url: the base URL prefix for all resources
           :param ext: extension to add to resource URLs, eg ".json"
           :param session: requests.Session instance used for this API. Useful
                  to set an auth procedure, or change verify parameter.
           :param fmt: either 'json' for json data, or a tuple specifying a
                  content-type string, encode function (for encoding the
                  request body) and a decode function (for decoding responses)
        """

        if session is None:
            session = requests.Session()

        if fmt == 'json':
            content_type = "application/json"
            encode = json.dumps
            decode = lambda req: json.loads(req.text or req.content)
        else:
            content_type, encode, decode = fmt

        self.base_url = base_url.rstrip("/") + "/"
        self.ext = ext

        self.content_type = content_type
        self.encode = encode
        self.decode = decode

        self.session = session

        self.session.headers["accept"] = self.content_type
        self.session.headers["content-type"] = self.content_type

    def str(self, path):
        """Obtain the URL of a resource"""
        return self.base_url + path + self.ext

    def path(self):
        return ""

    def attr(self, attr):
        if attr == "_":
            attr = "/"
        return str(attr)

    def _get(self, path, el):
        el = str(el).lstrip("/")
        if path == "":
            newpath = el
        else:
            newpath = path.rstrip("/") + "/" + el
        return newpath

    def call(self, path, *args, **kwargs):
        """Make a GET, POST or generic request to a resource.

           :Example:

           >>> x = BeanBag("http://host/api")
           >>> r = x()                                 # GET request
           >>> r = x(p1='foo', p2=3)                   # GET request with parameters passed via query string
           >>> r = x( {'a': 1, 'b': 2} )               # POST request
           >>> r = x( "RANDOMIZE", {'a': 1, 'b': 2} )  # Custom HTTP verb with request body
           >>> r = x( "OPTIONS", None )                # Custom HTTP verb with empty request body
        """

        if len(args) == 0:
            verb, body = "GET", None
        elif len(args) == 1:
            verb, body = "POST", args[0]
        elif len(args) == 2:
            verb, body = args
        else:
            raise TypeError("__call__ expected up to 2 arguments, got %d"
                     % (len(args)))
        return self.make_request(path, verb, kwargs, body)

    def set(self, path, val):
        """Make a PUT request to a subresource.

           :Example:

           >>> x = BeanBag("http://host/api")
           >>> x.res = {"a": 1}
           >>> x["res"] = {"a": 1}
        """

        return self.make_request(path, "PUT", {}, val)

    def delete(self, path):
        """Make a DELETE request to a subresource.

           :Example:

           >>> x = BeanBag("http://host/api")
           >>> del x.res
           >>> del x["res"]
        """

        return self.make_request(path, "DELETE", {}, None)

    def iadd(self, path, val):
        """Make a PATCH request to a resource.

           :Example:

           >>> x = BeanBag("http://host/api")
           >>> x += {"op": "replace", "path": "/a", "value": 3}
        """

        self.make_request(path, "PATCH", {}, val)
        return None

    def make_request(self, path, verb, params, body):
        path = self.str(path)

        if body is None:
            ebody = None
        else:
            try:
                ebody = self.encode(body)
            except:
                raise BeanBagException(None, "Could not encode request body")

        r = self.session.request(verb, path, params=params, data=ebody)

        if r.status_code < 200 or r.status_code >= 300:
            raise BeanBagException(r,
                    "Bad response code: %d" % (r.status_code,))

        if not r.content:
            return None

        ctype = r.headers.get("content-type", self.content_type)
        ctype = ctype.split(";", 1)[0]
        if ctype != self.content_type:
            raise BeanBagException(r,
                    "Bad content-type in response (Content-Type: %s)"
                                     % (r.headers["content-type"],))

        try:
            return self.decode(r)
        except:
            raise BeanBagException(r, "Could not decode response")
