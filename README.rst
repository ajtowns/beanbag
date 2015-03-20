
BeanBag
=======

BeanBag is a simple module that lets you access REST APIs in an easy
way. For example:

   >>> import beanbag
   >>> github = beanbag.BeanBag("https://api.github.com")
   >>> watchers = github.repos.ajtowns.beanbag.watchers()
   >>> for w in watchers:
   ...     print(w["login"])

See `http://beanbag.readthedocs.org/` for more information.

