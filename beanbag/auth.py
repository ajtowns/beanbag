#!/usr/bin/env python

# Copyright (c) 2014 Red Hat, Inc. and/or its affiliates.
# Copyright (c) 2015 Anthony Towns
# Written by Anthony Towns <aj@erisian.com.au>
# See LICENSE file.

from __future__ import print_function

import requests
try:
    from urlparse import urlparse, parse_qs
except ImportError:
    from urllib.parse import urlparse, parse_qs

try:
    input = raw_input  # rename raw_input for compat with py3
except NameError:
    pass


class KerbAuth(requests.auth.AuthBase):
    """Helper class for basic Kerberos authentication using requests
       library. A single instance can be used for multiple sites. Each
       request to the same site will use the same authorization token
       for a period of 180 seconds.

       :Example:

       >>> session = requests.Session()
       >>> session.auth = KerbAuth()
    """

    def __init__(self, timeout=180):
        import time
        import kerberos

        self.header_cache = {}
        self.timeout = timeout

        self.time = time.time
        self.kerberos = kerberos

    def __call__(self, r):
        hostname = urlparse(r.url).hostname
        header, last = self.header_cache.get(hostname, (None, None))
        if not header or (self.time() - last) >= self.timeout:
            service = "HTTP@" + hostname
            rc, vc = self.kerberos.authGSSClientInit(service)
            self.kerberos.authGSSClientStep(vc, "")
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
        """Create an OAuth10aDance object to negotiatie OAuth 1.0a credentials.

        The first set of parameters are the URLs to the OAuth 1.0a service
        you wish to authenticate against.

        :param req_token: Request token URL
        :param authorize: User authorization URL
        :param acc_token: Access token URL

        These parameters (and the others) may also be provided by subclassing
        the OAuth10aDance class, eg:

        :Example:

        >>> class OAuthDanceTwitter(beanbag.OAuth10aDance):
        ...     req_token = "https://api.twitter.com/oauth/request_token"
        ...     authorize = "https://api.twitter.com/oauth/authorize"
        ...     acc_token = "https://api.twitter.com/oauth/access_token"

        The second set of parameters identify the client application to
        the server, and need to be obtained outside of the OAuth protocol.

        :param client_key: client/consumer key
        :param client_secret: client/consumer secret

        The final set of parameters identify the user to server. These
        may be left as None, and obtained using the OAuth 1.0a protocol
        via the ``obtain_creds()`` method or using the ``get_auth_url()``
        and ``verify_user()`` methods.

        :param user_key: user key
        :param user_secret: user secret

        Assuming OAuthDanceTwitter is defined as above, and you have
        obtained the client key and secret (see https://apps.twitter.com/
        for twitter) as ``k`` and ``s``, then putting these together
        looks like:

        :Example:

        >>> oauthdance = OAuthDanceTwitter(client_key=k, client_secret=s)
        >>> oauthdance.obtain_creds()
        Please go to url:
          https://api.twitter.com/oauth/authorize?oauth_token=...
          Please input the verifier: 1111111
        >>> session = requests.Session()
        >>> session.auth = oauthdance.oauth()
        """

        from requests_oauthlib import OAuth1
        self.OAuth1 = OAuth1

        # override instance variables based on parameters
        for s in self.__slots__:
            u = locals().get(s, None)
            if u is not None:
                setattr(self, s, u)
            elif not hasattr(self, s):
                setattr(self, s, None)

    def have_creds(self):
        """Check whether all credentials are filled in"""
        return (self.client_key and self.client_secret and
                self.user_key and self.user_secret)

    def get_auth_url(self):
        """URL for user to obtain verification code"""

        oauth = self.OAuth1(self.client_key, client_secret=self.client_secret)
        r = requests.post(url=self.req_token, auth=oauth)
        credentials = parse_qs(r.content.decode('utf-8'))

        self.user_key = credentials.get('oauth_token', [""])[0]
        self.user_secret = credentials.get('oauth_token_secret', [""])[0]

        return self.authorize + '?oauth_token=' + self.user_key

    def verify_user(self, verifier):
        """Set user key and secret based on verification code"""

        oauth = self.OAuth1(self.client_key,
                       client_secret=self.client_secret,
                       resource_owner_key=self.user_key,
                       resource_owner_secret=self.user_secret,
                       verifier=verifier)
        r = requests.post(url=self.acc_token, auth=oauth)
        credentials = parse_qs(r.content.decode('utf-8'))

        self.user_key = credentials.get('oauth_token', [""])[0]
        self.user_secret = credentials.get('oauth_token_secret', [""])[0]

    def obtain_creds(self):
        """Fill in credentials by interacting with the user (input/print)"""
        if not self.client_key:
            self.client_key = input('Please input client key: ')
        if not self.client_secret:
            self.client_secret = input('Please input client secret: ')

        if self.user_key and self.user_secret:
            return

        assert self.req_token and self.acc_token and self.authorize

        print('Please go to url:\n  %s' % (self.get_auth_url(),))
        verifier = input('Please input the verifier: ')
        self.verify_user(verifier)

        print('User key: %s\nUser secret: %s' % (self.user_key,
                                                 self.user_secret))

    def oauth(self):
        """Create an OAuth1 authenticator using client and user credentials"""

        assert self.have_creds()
        return self.OAuth1(self.client_key,
                           client_secret=self.client_secret,
                           resource_owner_key=self.user_key,
                           resource_owner_secret=self.user_secret)

