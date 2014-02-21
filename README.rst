
BeanBag
=======

BeanBag is a simple module that lets you access REST APIs in an easy
way. The idea is calling a REST API shouldn't be any harder than calling
an XML-RPC API, and ideally no harder than calling a local API.

It uses the wonderful ``requests`` module, which is the only sensible way
to talk to the web from python.

It's heavily inspired by Kadir Pekel's Hammock, though sadly only
shares a license, and not any actual code. Hammock is available from
`https://github.com/kadirpekel/hammock`.

Proof
-----

Here's how you access github with BeanBag:

    >>> import beanbag
  
    >>> github = beanbag.BeanBag("https://api.github.com")

    >>> watchers = github.repos.ajtowns.beanbag.watchers()
    >>> for w in watchers: print w["login"]

Pretty easy! (Easier than Hammock even :)

The above was a basic GET request, but you can do PUT requests easily too,
though you'll usually need to provide some sort of authentication details:

    >>> import requests

    >>> sess = requests.Session()
    >>> sess.auth = (user, pass)   # github email address, password
    >>> github = beanbag.BeanBag("https://api.github.com", session=sess)

    >>> github.user.watched.ajtowns.beanbag = None

    >>> "https://api.github.com/repos/ajtowns/beanbag" in ( 
    ...     i["url"] for i in github.user.watched() )
    True

You can do DELETE requests too:

    >>> del github.user.watched.ajtowns.beanbag

    >>> "https://api.github.com/repos/ajtowns/beanbag" in (
    ...     i["url"] for i in github.user.watched() )
    False

You can use array-style references in place of attributes if you're
dealing with variable components (or paths that are python reserved words,
or otherwise invalid as an attribute):

    >>> owner, repo = "ajtowns", "beanbag"
    >>> watchers = github.repos[owner][repo].watchers()
    >>> for w in watchers: print w["login"]

POST and PATCH also have syntactic sugar, and 

    >>> # create a fork (POST request with empty body) 
    >>> repo = github.repos.ajtowns.beanbag.forks( None )
    >>> u,r = repo["owner"]["login"], repo["name"]
    >>> print u,r
    $YOU beanbag

    >>> print github.repos[u][r]()["description"]
    Helper module for accessing REST interfaces from Python

    >>> d = "My fork is way betterer!!"
    >>> github.repos[u][r] += {"name": r, "description": d}

    >>> print github.repos[u][r]()["description"]
    My fork is way betterer!!
    
By default, BeanBag only adds a trailing slash to the base URL. If you
want a trailing slash elsewhere, you can add "._", like so:

    >>> str(github)
    'https://api.github.com/'
    >>> str(github.repos)
    'https://api.github.com/repos'
    >>> str(github.repos._)
    'https://api.github.com/repos/'
    >>> str(github.repos["_"])
    'https://api.github.com/repos/_'

Also, you can use "str()" to find out the URL a resource actually maps to!

