#!/usr/bin/env python

# Copyright (c) 2014 Red Hat, Inc. and/or its affiliates.
# Copyright (c) 2015 Anthony Towns
# Written by Anthony Towns <aj@erisian.com.au>
# See LICENSE file.

from __future__ import print_function
__version__ = '2.0.0'

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

def bbjsondecode(req):
    obj = json.loads(req.text or req.content)
    if isinstance(obj, dict) and len(obj) == 1 and "result" in obj:
        obj = obj["result"]
    return obj

class BeanBag(HierarchialBase):
    def __init__(self, base_url, ext = "", session = None,
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
            decode = bbjsondecode
        else:
            content_type, encode, decode = fmt

        self.base_url = base_url.rstrip("/") + "/"
        self.ext = ext

        self.content_type = content_type
        self.encode = encode
        self.decode = decode

        self.session = session

        self.session.headers["Accept"] = self.content_type
        self.session.headers["Content-Type"] = self.content_type

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

    def get(self, path, el):
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
        url = self.baseurl(path)

        header_override={}
        if body is None:
            ebody = None
            header_override={"Content-Type": None}
        else:
            try:
                ebody = self.encode(body)
            except:
                raise BeanBagException("Could not encode request body",
                        None, (body,))

        r = self.session.request(verb, url, params=params, data=ebody, headers=header_override)

        if r.status_code < 200 or r.status_code >= 300:
            raise BeanBagException( "Bad response code: %d"
                                      % (r.status_code,),
                                    r, (verb, url, params, ebody))

        if not r.content:
            return None

        res_content = r.headers.get("content-type", None)
        if res_content is None:
            pass
        elif res_content.split(";",1)[0] == self.content_type:
            pass
        else:
            raise BeanBagException("Bad content-type in response (Content-Type: %s; wanted %s)"
                                     % (res_content.split(";",1)[0],
                                         self.content_type),
                                   r, (verb, path, params, ebody))

        try:
            return self.decode(r)
        except:
            raise BeanBagException("Could not decode response",
                    r, (verb, path, params, ebody))
