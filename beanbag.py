#!/usr/bin/env python

# Copyright (c) 2014 Red Hat, Inc.
# Written by Anthony Towns <atowns@redhat.com>
# GPLv2+

"""Usage:

>>> import beanbag
>>> foo = beanbag.BeanBag("http://hostname/api/")

To setup kerb auth:

>>> import requests
>>> session = requests.Session()
>>> session.auth = beanbag.KerbAuth()
>>> foo = beanbag.BeanBag("http://hostname/api/", session=session)

To setup oauth auth:

>>> from requests_oauth import OAuth1
>>> session.auth = OAuth1( secrets )
>>> foo = beanbag.BeanBag("http://hostname/api/", session=session)

To do REST queries, then:

>>> b = foo.resource(p1=3.14, p2=2.718)  # GET request
>>> foo.resource( {"a": 3, "b": 7} )     # POST request
>>> del foo.resource                     # DELETE request
>>> foo.resource = {"a" : 7, "b": 3}     # PUT request

You can chain paths as well:

>>> print foo.bar.baz[3]["xyzzy"].q
http://hostname/api/foo/bar/baz/3/xyzzy/q

To do a request on a resource that requires a trailing slash:

>>> print foo.bar._
http://hostname/api/foo/bar/
>>> print foo.bar[""]
http://hostname/api/foo/bar/
>>> print foo.bar["/"]
http://hostname/api/foo/bar/
>>> print foo["bar/"]
http://hostname/api/foo/bar/
>>> print foo.bar._.x == foo.bar.x
True
>>> print foo.bar["_"]
http://hostname/api/foo/bar/_

"""

import requests
import urlparse

try:
    import json
except ImportError:
    import simplejson as json

__all__ = ['BeanBag', 'BeanBagException', 'BeanBagRequest', 'KerbAuth']

class BeanBagPath(object):
    __slots__ = ("__bbr", "__path")

    def __init__(self, bbr, path):
        self.__bbr = bbr
        self.__path = path

    def __getattr__(self, attr):
        if attr == "_": attr = "/"
        return self.__getitem__(attr)

    def __setattr__(self, attr, val):
        if attr == "_": attr = "/"
        if attr.startswith("_BeanBagPath__"):
            return super(BeanBagPath, self).__setattr__(attr, val)
        return self.__setitem__(attr, val)

    def __delattr__(self, attr):
        return self.__delitem__(attr)

    def __getitem__(self, item):
        item = str(item).lstrip("/")
        if self.__path == "":
            newpath = item
        else:
            newpath = self.__path.rstrip("/") + "/" + item
        return BeanBagPath(self.__bbr, newpath)

    def __setitem__(self, attr, val):
        return self[attr]("PUT", val)

    def __delitem__(self, attr):
        return self[attr]("DELETE", None)

    def __iadd__(self, val):
        return self("PATCH", val)

    def __call__(self, *args, **kwargs):
        if len(args) == 0:
            verb, body = "GET", None
        elif len(args) == 1:
            verb, body = "POST", args[0]
        elif len(args) == 2:
            verb, body = args
        else:
            raise TypeError("__call__ expected up to 2 arguments, got %d"
                     % (len(args)))

        return self.__bbr.make_request(verb, self.__path, kwargs, body)

    def __eq__(self, other):
        if isinstance(other, BeanBagPath) and self.__bbr is other.__bbr:
            return str(self) == str(other)
        else:
            return False

    def __str__(self):
        return self.__bbr.path2url(self.__path)

    def __repr__(self):
        return "<%s(%s)>" % (type(self).__name__, str(self))

class BeanBagRequest(object):
    content_type = "application/json"
    def encode(self, obj):
        return json.dumps(obj)
    def decode(self, req):
        return req.json()

    def __init__(self, session, base_url, ext):
        self.base_url = base_url.rstrip("/") + "/"
        self.ext = ext

        self.session = session

        self.session.headers["accept"] = self.content_type
        self.session.headers["content-type"] = self.content_type

    def path2url(self, path):
        return self.base_url + path + self.ext

    def make_request(self, verb, path, params, body):
        path = self.path2url(path)

        if body is not None:
            body = self.encode(body)

        r = self.session.request(verb, path, params=params, data=body)

        if r.status_code > 200 or r.status_code >= 300:
            raise BeanBagException( "Bad response code: %d %s"
                                      % (r.status_code, r.reason),
                                    r, (verb, path, params, body))

        if r.headers["content-type"].split(";",1)[0] == self.content_type:
            return self.decode(r)

        else:
            raise BeanBagException("Non-JSON response (Content-Type: %s)"
                                     % (r.headers["content-type"],),
                                   r, (verb, path, params, body))

class BeanBag(BeanBagPath):
    def __init__(self, base_url, ext = "", session = None,
                 BBRequest=BeanBagRequest):
        if session is None:
            session = requests.Session()
        bbr = BBRequest(session, base_url, ext=ext)
        super(BeanBag, self).__init__(bbr, "")

class BeanBagException(Exception):
    __slots__ = ('msg', 'response', 'request')
    def __init__(self, msg, response, request):
        self.msg = msg
        self.response = response
        self.request = request

    def __repr__(self):
        return self.msg
    def __str__(self):
        return self.msg

class KerbAuth(object):
    def __init__(self):
        import time
        import kerberos

        self.header_cache = {}
        self.timeout = 300

        self.time = time.time
        self.kerberos = kerberos

    def __call__(self, r):
        hostname = urlparse.urlparse(r.url).hostname
        header, last = self.header_cache.get(hostname, (None, None))
        if not header or (self.time() - last) > self.timeout:
            service = "HTTP@" + hostname
            rc, vc = self.kerberos.authGSSClientInit(service);
            self.kerberos.authGSSClientStep(vc, "");
            header = "negotiate %s" % self.kerberos.authGSSClientResponse(vc)
            last = time.time()
            self.header_cache[hostname] = (header, last)
        r.headers['Authorization'] = header

class OAuth10aDance(object):
    req_token = None
    authorize = None
    acc_token = None

    client_key = None
    client_secret = None
    user_key = None
    user_secret = None

    def __init__(self,
                 req_token=None, acc_token=None, authorize=None,
                 client_key=None, client_secret=None,
                 user_key=None, user_secret=None):
        from requests_oauthlib import OAuth1
        self.OAuth1 = OAuth1

        # override instance variables based on parameters
        for s, v in locals().iteritems():
            if hasattr(self, s) and v is not None:
                setattr(self, s, v)

    def get_auth_url(self):
        oauth = self.OAuth1(self.client_key, client_secret = self.client_secret)
        r = requests.post(url=self.req_token, auth=oauth)
        credentials = urlparse.parse_qs(r.content)

        self.user_key = credentials.get('oauth_token', [""])[0]
        self.user_secret = credentials.get('oauth_token_secret', [""])[0]

        return self.authorize + '?oauth_token=' + self.user_key

    def verify(self, verifier):
        oauth = self.OAuth1(self.client_key,
                       client_secret=self.client_secret,
                       resource_owner_key=self.user_key,
                       resource_owner_secret=self.user_secret,
                       verifier=verifier)
        r = requests.post(url=self.acc_token, auth=oauth)
        credentials = urlparse.parse_qs(r.content)

        self.user_key = credentials.get('oauth_token', [""])[0]
        self.user_secret = credentials.get('oauth_token_secret', [""])[0]

    def ensure_creds(self, interactive):
        if not interactive:
            assert self.client_key and self.client_secret
            assert self.user_key and self.user_secret
            return

        if not self.client_key:
            self.client_key = raw_input('Please input client key: ')
        if not self.client_secret:
            self.client_secret = raw_input('Please input client secret: ')

        if self.user_key and self.user_secret:
            return

        assert self.req_token and self.acc_token and self.authorize

        print 'Please go to url:\n  %s' % (self.get_auth_url(),)
        verifier = raw_input('Please input the verifier: ')
        self.verify(verifier)

        print 'User key: %s\nUser secret: %s' % (self.user_key,
                                                 self.user_secret)

    def oauth(self):
        return self.OAuth1(self.client_key,
                           client_secret = self.client_secret,
                           resource_owner_key = self.user_key,
                           resource_owner_secret = self.user_secret)

