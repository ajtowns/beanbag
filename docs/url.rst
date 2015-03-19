.. module:: beanbag

beanbag -- REST API access
==========================

Setup:

.. code:: python

   >>> import beanbag
   >>> foo = beanbag.BeanBag("http://hostname/api/")

To do REST queries, then:

.. code:: python

   >>> r = foo.resource(p1=3.14, p2=2.718)  # GET request
   >>> r = foo.resource( {"a": 3, "b": 7} ) # POST request
   >>> del foo.resource                     # DELETE request
   >>> foo.resource = {"a" : 7, "b": 3}     # PUT request
   >>> foo.resource += {"a" : 7, "b": 3}    # PATCH request

You can chain paths as well:

.. code:: python

   >>> print(foo.bar.baz[3]["xyzzy"].q)
   http://hostname/api/foo/bar/baz/3/xyzzy/q

To do a request on a resource that requires a trailing slash:

.. code:: python

   >>> print(foo.bar._)
   http://hostname/api/foo/bar/
   >>> print(foo.bar[""])
   http://hostname/api/foo/bar/
   >>> print(foo.bar["/"])
   http://hostname/api/foo/bar/
   >>> print(foo["bar/"])
   http://hostname/api/foo/bar/
   >>> print(foo.bar._.x == foo.bar.x)
   True
   >>> print(foo.bar["_"]
   http://hostname/api/foo/bar/_)

To access REST interfaces that require authentication, you need to
specify a session object. BeanBag supplies helpers to make Kerberos
and OAuth 1.0a authentication easier.

To setup kerberos auth:

.. code:: python

   >>> import requests
   >>> session = requests.Session()
   >>> session.auth = beanbag.KerbAuth()
   >>> foo = beanbag.BeanBag("http://hostname/api/", session=session)

To setup oauth using OAuth1 directly:

.. code:: python

   >>> import requests
   >>> from requests_oauth import OAuth1
   >>> session = requests.Session()
   >>> session.auth = OAuth1( consumer creds, user creds )
   >>> foo = beanbag.BeanBag("http://hostname/api/", session=session)

To setup oauth using beanbag's OAuth10aDance helper (which will
generate the authentication url and construct user credentials from the
verification token supplied when the auth url is visited in a browser),
see the twitter_example script.

BeanBag class
-------------

.. autoclass:: BeanBag
   :members: __init__, __str__, __getattr__, __getitem__, __call__, __setattr__, __setitem__, __delattr__, __delitem__, __iadd__
   :member-order: bysource

BeanBagException
----------------

.. autoexception:: BeanBagException
   :members:
   :special-members:

Authentication Helpers
----------------------

.. autoclass:: KerbAuth
   :members:
   :special-members:

.. autoclass:: OAuth10aDance
   :members:
   :special-members:
   :undoc-members:

