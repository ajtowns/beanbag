#!/usr/bin/env python

# Copyright (c) 2014 Red Hat, Inc. and/or its affiliates.
# Copyright (c) 2015 Anthony Towns
# Written by Anthony Towns <aj@erisian.com.au>
# See LICENSE file.

from .namespace import HierarchialBase
from .bbexcept import BeanBagException

import requests
try:
    from urlparse import urlparse, parse_qs
except ImportError:
    from urllib.parse import urlparse, parse_qs

try:
    import json
except ImportError:
    import simplejson as json


__all__ = ['BeanBag', 'verb', 'GET', 'HEAD', 'POST', 'PUT', 'PATCH', 'DELETE']
__version__ = '2.0.0'


def verb(verbname):
    """Construct a BeanBag compatible verb function

       :param verbname: verb to use (GET, POST, etc)
    """

    def do(url, body=None):
        base, path = ~url
        return base.make_request(path, verbname, body)
    do.__name__ = verbname
    do.__doc__ = "%s verb function" % (verbname,)
    return do

GET = verb("GET")
HEAD = verb("HEAD")
POST = verb("POST")
PUT = verb("PUT")
PATCH = verb("PATCH")
DELETE = verb("DELETE")


class BeanBag(HierarchialBase):
    mime_json = "application/json"

    def __init__(self, base_url, ext = "", session = None):
        """Create a BeanBag referencing a base REST path.

           :param base_url: the base URL prefix for all resources
           :param ext: extension to add to resource URLs, eg ".json"
           :param session: requests.Session instance used for this API. Useful
                  to set an auth procedure, or change verify parameter.
        """

        if session is None:
            session = requests.Session()

        self.base_url = base_url.rstrip("/") + "/"
        self.ext = ext

        self.session = session

    def encode(self, body):
        if isinstance(body, requests.Request):
            req = body
        elif body is None:
            req = requests.Request(data=None, headers={"Accept": self.mime_json})
        else:
            req = requests.Request(data=json.dumps(body),
                    headers={"Accept": self.mime_json,
                        "Content-Type": self.mime_json})
        return req

    def decode(self, response):
        if response.status_code < 200 or response.status_code >= 300:
            raise BeanBagException(
                    "Bad response code: %d" % (response.status_code,),
                    response)

        if not response.content:
            return None

        res_content = response.headers.get("content-type", None)
        if res_content is None:
            pass
        elif res_content.split(";",1)[0] == self.mime_json:
            pass
        else:
            raise BeanBagException("Bad content-type in response (Content-Type: %s; wanted %s)"
                                     % (res_content.split(";",1)[0],
                                         self.mime_json),
                                   response)
        try:
            obj = json.loads(response.text or response.content)
        except:
            raise BeanBagException("Could not decode response",
                    response)

        if isinstance(obj, dict) and len(obj) == 1 and "result" in obj:
            obj = obj["result"]

        return obj

    def baseurl(self, path):
        url, params = path
        return "%s%s%s" % (self.base_url, url, self.ext)

    def str(self, path):
        """Obtain the URL of a resource"""
        url, params = path
        url = self.baseurl(path)
        if params:
            url = "%s?%s" % (url, ";".join("%s=%s" % (str(k),str(v))
                        for k,v in params.items() if v is not None))
        return url

    def path(self):
        return ("", {})

    def attr(self, attr):
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
            for k,v in a.items():
                if v is not None:
                    newparams[k] = v
                elif k in newparams:
                    del newparams[k]

        return self.namespace((url, newparams))

    def invert(self, path):
        return self, path

    def make_request(self, path, verb, body):
        _, params = path
        req = self.encode(body)

        req.url = self.baseurl(path)
        req.params = params
        req.method = verb

        p = self.session.prepare_request(req)
        s = self.session.merge_environment_settings(p.url, {}, None, None, None)

        r = self.session.send(request=p, **s)

        return self.decode(r)

