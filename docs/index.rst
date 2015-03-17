.. beanbag documentation master file, created by
   sphinx-quickstart on Tue Mar 17 15:11:56 2015.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

BeanBag
=======

.. module:: beanbag

BeanBag is a set of modules that provide some syntactic sugar to make
interacting with REST APIs easy and pleasant.

A simple example:

.. code:: python

   >>> import beanbag
   >>> github = beanbag.BeanBag("https://api.github.com")
   >>> watchers = github.repos.ajtowns.beanbag.watchers()
   >>> for w in watchers: print(w["login"])

Credits
-------

Code contributors:

 - Anthony Towns <aj@erisian.com.au>
 - Gary Martin <gjm@apache.org> 

Documentation contributors:

 - Anthony Towns <aj@erisian.com.au>

Test case contributors and bug reporters:

 - Anthony Towns <aj@erisian.com.au>
 - Russell Stuart <russell-github@stuart.id.au>

BeanBag is inspired by Kadir Pekel's Hammock, though sadly only
shares a license, and not any actual code. Hammock is available from
`https://github.com/kadirpekel/hammock`.

.. toctree::
   :maxdepth: 2

   url.rst
   attrdict.rst
   namespace.rst

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

