#!/usr/bin/env python

# Copyright (c) 2014 Red Hat, Inc. and/or its affiliates.
# Copyright (c) 2015 Anthony Towns
# Written by Anthony Towns <aj@erisian.com.au>
# See LICENSE file.

from .namespace import HierarchialNS
from .bbexcept import BeanBagException
from .attrdict import AttrDict

import requests

try:
    import json
except ImportError:
    import simplejson as json


__all__ = ['BeanBag', 'Request', 'verb', 'GET', 'HEAD', 'POST', 'PUT', 'PATCH', 'DELETE']
__version__ = '2.0.0'


def verb(verbname):
    """Construct a BeanBag compatible verb function

       :param verbname: verb to use (GET, POST, etc)
    """

    def do(url, body=None):
        base, path = ~url
        req = base.encode(body)
        res = base.make_request(path, verbname, req)
        return base.decode(res)

    do.__name__ = verbname
    do.__doc__ = "%s verb function" % (verbname,)
    return do

GET = verb("GET")
HEAD = verb("HEAD")
POST = verb("POST")
PUT = verb("PUT")
PATCH = verb("PATCH")
DELETE = verb("DELETE")


class Request(AttrDict):
    def __init__(self, **kwargs):
        """Create a Request object

           Request objects act as placeholders for the arguments to
           the requests() function of the requests.Session being used.
           They are used as the interface between the encode() and
           make_request() functions, and may also be used by the API
           caller.

           NB: A Request object is only suitable for one use, as it may
           be modified in-place during the request. For this reason,
           __init__ makes a (shallow) copy of all the keyword arguments
           supplied rather than using them directly.
        """

        for badarg in ["method", "url", "params"]:
            if badarg in kwargs:
                raise TypeError("__init__() got forbidden keyword argument '%s'" % (badarg,))

        d = {}
        for k, v in kwargs.items():
            if isinstance(v, list):
                v = v[:]
            elif isinstance(v, dict):
                v = v.copy()
            d[k] = v
        (~AttrDict).__init__(self, d)


class BeanBag(HierarchialNS):
    mime_json = "application/json"

    def __init__(self, base_url, ext="", session=None, use_attrdict=True):
        """Create a BeanBag referencing a base REST path.

           :param base_url: the base URL prefix for all resources
           :param ext: extension to add to resource URLs, eg ".json"
           :param session: requests.Session instance used for this API. Useful
                  to set an auth procedure, or change verify parameter.
           :param use_attrdict: if true, ``decode()`` will wrap dicts and
                  lists in a ``beanbag.attrdict.AttrDict`` for syntactic
                  sugar.
        """

        if session is None:
            session = requests.Session()

        self.base_url = base_url.rstrip("/") + "/"
        self.ext = ext

        self.session = session
        self.use_attrdict = use_attrdict

    def encode(self, body):
        """Convert a python object into a beanbag.Request object.

           This function converts the user provided body object (or None
           when there is no body) into a requests.Request object, by
           encoding it as JSON string. (Note that the url and method
           members of the Request are provided later by the

           :param body: provided by the API user, usually a dict or None
        """

        if isinstance(body, Request):
            req = body
        elif body is None:
            req = Request(data=None, headers={"Accept": self.mime_json})
        else:
            if isinstance(body, AttrDict):
                body = +body
            req = Request(data=json.dumps(body),
                    headers={"Accept": self.mime_json,
                        "Content-Type": self.mime_json})
        return req

    def decode(self, response):
        """Converts a requests.Response object to a python object

           This function converts the REST API's response back into a
           python object by decoding it from JSON (or raises an exception
           if the response indicates an error).

           :param response: requests.Response object
        """

        if response.status_code < 200 or response.status_code >= 300:
            raise BeanBagException(response,
                    "Bad response code: %d" % (response.status_code,))

        if not response.content:
            return None

        res_content = response.headers.get("content-type", None)
        if res_content is None:
            pass
        elif res_content.split(";", 1)[0] == self.mime_json:
            pass
        else:
            raise BeanBagException(response,
                    "Bad content-type in response (Content-Type: %s; wanted %s)"
                                     % (res_content.split(";", 1)[0],
                                         self.mime_json))
        try:
            obj = json.loads(response.text or response.content)
        except:
            raise BeanBagException(response, "Could not decode response")

        if self.use_attrdict:
            if isinstance(obj, dict) or isinstance(obj, list):
                obj = AttrDict(obj)

        return obj

    def baseurl_params(self, path):
        """Construct the base URL of a resource (excluding URL params)"""

        url, params = path
        return ("%s%s%s" % (self.base_url, url, self.ext)), params

    def str(self, path):
        """Obtain the URL of a resource"""

        url, params = self.baseurl_params(path)
        if params:
            url = "%s?%s" % (url, ";".join("%s=%s" % (str(k), str(v))
                        for k, v in params.items() if v is not None))
        return url

    def path(self):
        return ("", {})

    def attr(self, attr):
        """Special processing for attribute access

           This converts ._ to a trailing slash.
        """

        if attr == "_":
            attr = "/"
        return str(attr)

    def _get(self, path, el):
        url, params = path
        el = str(el).lstrip("/")
        if url == "":
            newurl = el
        else:
            newurl = url.rstrip("/") + "/" + el
        return (newurl, params)

    def call(self, path, *args, **kwargs):
        """Set URL parameters"""

        url, params = path
        newparams = params.copy()
        for a in tuple(args) + (kwargs,):
            for k, v in a.items():
                if v is not None:
                    newparams[k] = v
                elif k in newparams:
                    del newparams[k]

        return self.namespace((url, newparams))

    def invert(self, path):
        """Provide access to the base/path via the namespace object

           .. code::

              bb = BeanBag(...)
              base, path = ~bb.foo
              assert isinstance(base, BeanBagBase)

           This is the little bit of glue needed so that it's possible to
           call methods defined in BeanBagBase directly rather than just
           the operators BeanBag supports.
        """

        return self, path

    def make_request(self, path, verb, request):
        """Make a REST request to a resource"""

        url, params = self.baseurl_params(path)

        assert isinstance(request, Request)
        request = +request   # convert to dictionary

        return self.session.request(
                method=verb, url=url, params=params, **request)

