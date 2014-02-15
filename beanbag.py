
import requests
import kerberos
import time
import urlparse

try:
    import json
except ImportError:
    import simplejson as json

class BeanBag(object):
    """Class to make accessing REST APIs feel pythonic"""

    def __init__(self, base_url):
        self._request = BeanBagRequest(base_url)
        self._bb = BeanBagSub(self._request, "") 

    def __getattr__(self, attr):
        return getattr(self._bb, attr)

    def __setattr__(self, attr, val):
        if attr[0] == "_" or hasattr(self, attr):
            return super(BeanBag, self).__setattr__(attr, val)
        else:
            return self._bb.__setattr__(attr, val)

    def __delattr__(self, attr):
        return self._bb.__delattr__(attr)
    
    def __getitem__(self, attr):
        return self._bb.__getitem__(attr)

    def __setitem__(self, attr, val):
        return self._bb.__setitem__(attr, val)

    def __delitem__(self, attr):
        return self._bb.__delitem__(attr)

    def __call__(self, *args, **kwargs):
        return self._bb(*args, **kwargs)

class BeanBagSub(object):
    def __init__(self, bbr, path):
        self.__bbr = bbr
        self.__path = path

    def __getattr__(self, attr):
        return self.__getitem__(attr)

    def __setattr__(self, attr, val):
        if attr.startswith("_BeanBagSub__"):
            return super(BeanBagSub, self).__setattr__(attr, val)
        return self.__setitem__(attr, val)

    def __delattr__(self, attr):
        return self.__delitem__(attr)

    def __getitem__(self, item):
        item = str(item).strip("/")
        if self.__path == "":
            newpath = item
        else:
            newpath = self.__path.rstrip("/") + "/" + item
        return BeanBagSub(self.__bbr, newpath)

    def __setitem__(self, attr, val):
        return self[attr]("PUT", val)
    
    def __delitem__(self, attr):
        return self[attr]("DELETE", None)
    
    def __iadd__(self, val):
        return self("PATCH", val)

    def __call__(self, *args, **kwargs):
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

    def _url(self):
        return self.__bbr.base_url + self.__path

class BeanBagRequest(object):
    def __init__(self, base_url):
        self.base_url = base_url.rstrip("/") + "/"

        self.content_types = ["application/json", "test/json"]
        self.session = requests.Session()
        self.session.headers["accept"] = "application/json"
        self.session.headers["content-type"] = "application/json"

        self.__kerb_auth_header = None
        self.__kerb_auth_time = None

    @property
    def hostname(self):
        return urlparse.urlparse(self.base_url).hostname

    def __kerb_auth(self):
        if not self.__kerb_auth_header or \
                (time.time() - self.__kerb_auth_time) > 300:
            service = "HTTP@" + self.hostname
            try:
                rc, vc = kerberos.authGSSClientInit(service);
            except kerberos.GSSError, e:
                raise kerberos.GSSError(e)
            try:
                kerberos.authGSSClientStep(vc, "");
            except kerberos.GSSError, e:
                raise kerberos.GSSError(e)
            self.__kerb_auth_header = \
                    "negotiate %s" % kerberos.authGSSClientResponse(vc)
            self.__kerb_auth_time = time.time()
        self.session.headers['Authorization'] = self.__kerb_auth_header

    def set_sslcert(self, cabundle):
        if cabundle is None:
            self.session.verify = False
        else:
            self.session.verify = cabundle

    def make_request(self, verb, path, params, body):
        path = self.base_url + path

        self.__kerb_auth()

        if body is not None:
            body = json.dumps(body)
        r = self.session.request(verb, path, params=params, data=body)
        if r.status_code > 200 or r.status_code >= 300:
            raise BeanBagException( "Bad response code: %d %s" 
                                      % (r.status_code, r.reason),
                                    r, (verb, path, params, body))

        if r.headers["content-type"].split(";",1)[0] in self.content_types:
            return r.json()

        else:
            raise BeanBagException("Non-JSON response (Content-Type: %s)" 
                                     % (r.headers["content-type"],), 
                                   r, (verb, path, params, body))

class BeanBagException(Exception):
    def __init__(self, msg, response, request):
        self.msg = msg
        self.response = response
        self.request = request

    def __repr__(self):
        return self.msg
    def __str__(self):
        return self.msg

