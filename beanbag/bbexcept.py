#!/usr/bin/env python

# Copyright (c) 2014 Red Hat, Inc. and/or its affiliates.
# Copyright (c) 2015 Anthony Towns
# Written by Anthony Towns <aj@erisian.com.au>
# See LICENSE file.


class BeanBagException(Exception):
    """Exception thrown when a BeanBag request fails.

       Data members:
         * msg      -- exception string, brief and human readable
         * response -- response object

       You can get the original request via bbe.response.request.
    """

    __slots__ = ('msg', 'response')

    def __init__(self, response, msg):
        """Create a BeanBagException"""

        self.msg = msg
        self.response = response

    def __repr__(self):
        return "%s(%s,%r)" % (self.__class__.__name__, self.msg,
          self.response)

    def __str__(self):
        msg = self.msg
        if self.response and hasattr(self.response, "content"):
            msg = "%s - response: %s" % (self.msg, self.response.content)
        return msg

