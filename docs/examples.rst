
Examples
========

What follows are some examples of using BeanBag for various services.

GitHub
------

`GitHub's REST API`_, using JSON for data and either HTTP Basic Auth or
OAuth2 for authentication. Basic Auth is perfect for a command line app,
since the user can just use their github account password directly.

.. _Github's REST API: https://developer.github.com/v3/

The following example uses the github API to list everyone who's starred
one of your repos, and which repo it is that they've starred.

.. literalinclude:: ../examples/github
   :language: python

Twitter
-------

`Twitter's REST API`_ is slightly more complicated. It still uses
JSON, but requires OAuth 1.0a to be used for authentication. OAuth is
designed primarily for webapps, where the application is controlled by
a third party. In particular it is designed to allow an "application" to
authenticate as "authorised by a particular user", rather than allowing
the application to directly authenticate itself as the user (eg, by using
the user's username and password directly, as we did above with github).

This in turn means that the application has to be able to identify itself.
This is done by gaining "client credential", in Twitter's case via
`Twitter Apps`_.

.. _Twitter's REST API: https://dev.twitter.com/rest/public
.. _Twitter Apps: https://apps.twitter.com/

The process of having an application to ask a user to provide a token that
allows it to access Twitter on behalf of the user is encapsulated in the
``OAuth10aDance`` class. In the example below is subclassed in order
to provide the Twitter-specific URLs that the user and application will
need to visit in order to gain the right tokens to do the authentication.
The ``obtain_creds()`` method is called, which will instruct the user to
enter any necessary credentials, after which a ``Session`` object is created
and setup to perform OAuth authentication using the provided credentials.

The final minor complication is that Twitter's endpoints all end with
".json", which would be annoying to have to specify via beanbag (since "."
is not a valid part of an attribute). The ``ext=`` keyword argument of the
``BeanBag`` constructor is used to supply this as the standard extension
for all URLs in the Twitter API.

.. literalinclude:: ../examples/twitter
   :language: python

