#!/usr/bin/env python

# Copyright (c) 2014 Red Hat, Inc. and/or its affiliates.
# Written by Anthony Towns <atowns@redhat.com>
# See LICENSE file.

"""Helper module for accessing REST interfaces

Setup:

>>> import beanbag
>>> foo = beanbag.BeanBag("http://hostname/api/")

To do REST queries, then:

>>> r = foo.resource(p1=3.14, p2=2.718)  # GET request
>>> r = foo.resource( {"a": 3, "b": 7} ) # POST request
>>> del foo.resource                     # DELETE request
>>> foo.resource = {"a" : 7, "b": 3}     # PUT request
>>> foo.resource += {"a" : 7, "b": 3}    # PATCH request

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

To access REST interfaces that require authentication, you need to
specify a session object. BeanBag supplies helpers to make Kerberos
and OAuth 1.0a authentication easier.

To setup kerberos auth:

>>> import requests
>>> session = requests.Session()
>>> session.auth = beanbag.KerbAuth()
>>> foo = beanbag.BeanBag("http://hostname/api/", session=session)

To setup oauth using OAuth1 directly:

>>> import requests
>>> from requests_oauth import OAuth1
>>> session = requests.Session()
>>> session.auth = OAuth1( consumer creds, user creds )
>>> foo = beanbag.BeanBag("http://hostname/api/", session=session)

To setup oauth using beanbag's OAuth10aDance helper (which will
generate the authentication url and construct user credentials from the
verification token supplied when the auth url is visited in a browser),
see the twitter_example script.

"""

__version__ = '1.0.0'

import requests
import urlparse

try:
    import json
except ImportError:
    import simplejson as json

__all__ = ['BeanBag', 'BeanBagException',
           'KerbAuth', 'OAuth10aDance']

class BeanBagPath(object):
    __slots__ = ("__bbr", "__path")

    def __init__(self, bbr, path):
        self.__bbr = bbr
        self.__path = path

    def __repr__(self):
        return "<%s(%s)>" % (type(self).__name__, str(self))

    def __str__(self):
        """Obtain the URL of a resource"""
        return self.__bbr.path2url(self.__path)

    def __getattr__(self, attr):
        """Refer to a subresource.

           Example:
           >>> x = BeanBag("http://host/api")
           >>> print x.myresource
           http://host/api/myresource
           >>> print x.myresource._
           http://host/api/myresource/
        """

        if attr == "_": attr = "/"
        return self.__getitem__(attr)

    def __getitem__(self, item):
        """Refer to a subresource.

           Example:
           >>> x = BeanBag("http://host/api")
           >>> y = "myresource"
           >>> print x[y]
           http://host/api/myresource
           >>> print x[y+"/"]
           http://host/api/myresource/
        """

        item = str(item).lstrip("/")
        if self.__path == "":
            newpath = item
        else:
            newpath = self.__path.rstrip("/") + "/" + item
        return BeanBagPath(self.__bbr, newpath)

    def __call__(self, *args, **kwargs):
        """Make a GET, POST or generic request to a resource.

           Example:
           >>> x = BeanBag("http://host/api")

           GET request:
           >>> r = x()

           GET request with parameters passed via query string
           >>> r = x(p1='foo', p2=3)

           POST request:
           >>> r = x( {'a': 1, 'b': 2} )

           Custom HTTP verb with request body:
           >>> r = x( "RANDOMIZE", {'a': 1, 'b': 2} )

           Custom HTTP verb with empty request body:
           >>> r = x( "OPTIONS", None )
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
        return self.__bbr.make_request(verb, self.__path, kwargs, body)

    def __setattr__(self, attr, val):
        """Make a PUT request to a subresource.

           Example:
           >>> x = BeanBag("http://host/api")
           >>> x.res = {"a": 1}
        """

        if attr == "_": attr = "/"
        if attr.startswith("_BeanBagPath__"):
            return super(BeanBagPath, self).__setattr__(attr, val)
        return self.__setitem__(attr, val)

    def __setitem__(self, attr, val):
        """Make a PUT request to a subresource.

           Example:
           >>> x = BeanBag("http://host/api")
           >>> x["res"] = {"a": 1}
        """

        return self[attr]("PUT", val)

    def __delattr__(self, attr):
        """Make a DELETE request to a subresource.

           Example:
           >>> x = BeanBag("http://host/api")
           >>> del x.res
        """

        return self.__delitem__(attr)

    def __delitem__(self, attr):
        """Make a DELETE request to a subresource.

           Example:
           >>> x = BeanBag("http://host/api")
           >>> del x["res"]
        """

        return self[attr]("DELETE", None)

    def __iadd__(self, val):
        """Make a PATCH request to a resource.

           Example:
           >>> x = BeanBag("http://host/api")
           >>> x += {"op": "replace", "path": "/a", "value": 3}
        """

        return self("PATCH", val)

    def __eq__(self, other):
        """Compare two resource references."""
        if isinstance(other, BeanBagPath) and self.__bbr is other.__bbr:
            return str(self) == str(other)
        else:
            return False

class BeanBag(BeanBagPath):
    __slots__ = ()
    def __init__(self, base_url, ext = "", session = None,
                 fmt='json'):
        """Create a BeanBag reference a base REST path.

           Parameters:
               base_url: the base URL prefix for all resources
               ext: extension to add to resource URLs, eg ".json"
               session: requests.Session instance used for this API. Useful
                  to set an auth procedure, or change verify parameter.
               fmt: either 'json' for json data, or a tuple specifying a
                  content-type string, encode function (for encoding the
                  request body) and a decode function (for decoding responses)
        """

        if session is None:
            session = requests.Session()

        if fmt == 'json':
            content_type = "application/json"
            encode = json.dumps
            decode = lambda req: req.json()
        else:
            content_type, encode, decode = fmt

        bbr = BeanBagRequest(session, base_url, ext=ext,
                content_type=content_type, encode=encode, decode=decode)

        super(BeanBag, self).__init__(bbr, "")

class BeanBagRequest(object):
    def __init__(self, session, base_url, ext, content_type, encode, decode):
        self.base_url = base_url.rstrip("/") + "/"
        self.ext = ext

        self.content_type = content_type
        self.encode = encode
        self.decode = decode

        self.session = session

        self.session.headers["accept"] = self.content_type
        self.session.headers["content-type"] = self.content_type

    def path2url(self, path):
        return self.base_url + path + self.ext

    def make_request(self, verb, path, params, body):
        path = self.path2url(path)

        if body is None:
            ebody = None
        else:
            try:
                ebody = self.encode(body)
            except:
                raise BeanBagException("Could not encode request body",
                        None, (body,))

        r = self.session.request(verb, path, params=params, data=ebody)

        if r.status_code < 200 or r.status_code >= 300:
            raise BeanBagException( "Bad response code: %d %s"
                                      % (r.status_code, r.reason),
                                    r, (verb, path, params, ebody))

        if r.content == "":
            return None

        elif r.headers.get("content-type", self.content_type).split(";",1)[0] == self.content_type:
            try:
                return self.decode(r)
            except:
                raise BeanBagException("Could not decode response",
                        r, (verb, path, params, ebody))

        else:
            raise BeanBagException("Bad content-type in response (Content-Type: %s)"
                                     % (r.headers["content-type"],),
                                   r, (verb, path, params, ebody))

class BeanBagException(Exception):
    """Exception thrown when a BeanBag request fails.

       Data members:
          msg      -- exception string, brief and human readable
          request  -- original request object
          response -- response object

       Use request and response fields for debugging.
    """

    __slots__ = ('msg', 'response', 'request')

    def __init__(self, msg, response, request):
        """Create a BeanBagException"""

        self.msg = msg
        self.response = response
        self.request = request

    def __repr__(self):
        return "%s(%s,...)" % (self.__class__.__name__, self.msg)
    def __str__(self):
        return self.msg

class KerbAuth(requests.auth.AuthBase):
    """Helper class for basic Kerberos authentication using requests
       library. A single instance can be used for multiple sites. Each
       request to the same site will use the same authorization token
       for a period of 180 seconds (.timeout member).

       Usage:
       >>> session = requests.Session()
       >>> session.auth = KerbAuth()
    """

    def __init__(self):
        import time
        import kerberos

        self.header_cache = {}
        self.timeout = 180

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
            last = self.time()
            self.header_cache[hostname] = (header, last)
        r.headers['Authorization'] = header
        return r

class OAuth10aDance(object):
    __slots__ = [
            'req_token', 'authorize', 'acc_token',  # oauth resource URLs
            'client_key', 'client_secret',          # client creds
            'user_key', 'user_secret',              # user creds
            'OAuth1'                                # OAuth1 module ref
            ]

    def __init__(self,
                 req_token=None, acc_token=None, authorize=None,
                 client_key=None, client_secret=None,
                 user_key=None, user_secret=None):
        from requests_oauthlib import OAuth1
        self.OAuth1 = OAuth1

        # override instance variables based on parameters
        for s in self.__slots__:
            u = locals().get(s, None)
            if u is not None:
                setattr(self, s, u)
            elif not hasattr(self, s):
                setattr(self, s, None)

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

