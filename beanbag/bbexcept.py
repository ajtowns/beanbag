#!/usr/bin/env python

# Copyright (c) 2014 Red Hat, Inc. and/or its affiliates.
# Copyright (c) 2015 Anthony Towns
# Written by Anthony Towns <aj@erisian.com.au>
# See LICENSE file.


class BeanBagException(Exception):
    """Exception thrown when a BeanBag request fails.

       Data members:
         * msg      -- exception string, brief and human readable
         * request  -- original request object
         * response -- response object

       Use request and response fields for debugging.
    """

    __slots__ = ('msg', 'response', 'request')

    def __init__(self, msg, response, request):
        """Create a BeanBagException"""

        self.msg = msg
        self.response = response
        self.request = request

    def __repr__(self):
        return "%s(%s,%s,%s)" % (self.__class__.__name__, self.msg,
          self.response, self.request)

    def __str__(self):
        msg = self.msg
        if self.response and hasattr(self.response, "content"):
          msg = "%s - response: %s" % (self.msg, self.response.content)
        return msg

