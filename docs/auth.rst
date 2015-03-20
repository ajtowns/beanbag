.. module:: beanbag.auth

beanbag.auth -- Authentication Helpers
======================================

Kerberos Helper
---------------

To setup kerberos auth:

.. code:: python

   >>> import requests
   >>> session = requests.Session()
   >>> session.auth = beanbag.KerbAuth()
   >>> foo = beanbag.BeanBag("http://hostname/api/", session=session)

.. autoclass:: KerbAuth
   :members: __init__
   :undoc-members:

OAuth 1.0a Helper
-----------------

``OAuth10aDance`` helps with determining the user creds, compared to using
OAuth1 directly.

.. autoclass:: OAuth10aDance
   :members: __init__, get_auth_url, have_creds, oauth, obtain_creds, verify_user
   :member-order: bysource

