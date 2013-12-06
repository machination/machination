import pprint
import sys
import os
import errno
import functools
from lxml import etree
from machination.xmldata import from_xml, to_xml
from machination import context
#from machination.xmltools import pstring
from machination.cosign import CosignPasswordMgr, CosignHandler

l = context.logger

# Try to make this work on python 2.x or python 3.x
#
# url and http request handling
try:
    import urllib.request as urllib_request
    import http.client as http_client
except ImportError:
    import urllib2 as urllib_request
    import httplib as http_client
import ssl
#
# memoisation
try:
    getattr(functools, 'lru_cache')
except AttributeError:
    from machination import threebits
    functools.lru_cache = threebits.lru_cache


import http.cookiejar

class HTTPSClientAuthHandler(urllib_request.HTTPSHandler):
    def __init__(self, key, cert):
        urllib_request.HTTPSHandler.__init__(self)
        self.key = key
        self.cert = cert

    def https_open(self, req):
        #Rather than pass in a reference to a connection class, we pass in
        # a reference to a function which, for all intents and purposes,
        # will behave as a constructor
        return self.do_open(self.getConnection, req)

    def getConnection(self, host, timeout=None):
        # See if we're using a version of python with ssl.SSLContext
        # (3.2 or above)
        try:
            context = ssl.SSLContext(ssl.PROTOCOL_TLSv1)
        except AttributeError:
            context = None

        if context:
            # python >= 3.2
            context.verify_mode = ssl.CERT_NONE
            context.load_cert_chain(certfile=self.cert, keyfile=self.key)
            try:
                con = http_client.HTTPSConnection(host,
                                                  context=context,
                                                  check_hostname=False)
            except IOError as e:
                if e.errno == errno.ENOENT:
                    e.filename = '{} or {}'.format(self.key, self.cert)
                    raise
        else:
            # python < 3.2
            try:
                con = http_client.HTTPSConnection(host,
                                              key_file=self.key,
                                              cert_file=self.cert)
            except IOError as e:
                if e.errno == errno.ENOENT:
                    e.filename = '{} or {}'.format(self.key, self.cert)
                    raise

        return con

class WebClient(object):
    """Machination WebClient"""

#    def __init__(self, service_id=None, obj_type=None, cred=None, service_elt=None):
    def __init__(self, hierarchy_url, authen_type, obj_type,
                 credentials=None, service_id=None):
        '''Create a new WebClient

        hierarchy_url: URL on which to contact hierarchy

        authen_type: Type of authentication to use (cosign, cert, public)

        obj_type: Type of entity making the request (os_instance, person, ...)

        credentials (=None): A dictionary of credential information or
          a callable that will return such.

        service_id (=None): Used by the 'cert' method to look up
         certificate locations if they are not specified.

        '''

        self.hierarchy_url = hierarchy_url
        self.authen_type = authen_type
        self.obj_type = obj_type
        self.url = '{}/{}'.format(
            self.hierarchy_url,
            self.authen_type
            )
        self.encoding = 'utf-8'
        self.l = context.logger
        self.cookie_file = os.path.join(context.status_dir(), 'cookies.txt')
        self.cookie_jar = None
        handlers = []

        if self.authen_type == 'cosign':
            self.l.lmsg('building cosign handlers')
            self.cookie_jar = http.cookiejar.MozillaCookieJar(
                self.cookie_file
                )
            handlers.append(
                urllib_request.HTTPCookieProcessor(
                    self.cookie_jar
                    )
                )
            if (not hasattr(credentials, '__call__')) and (credentials is not None):
                values = credentials
                credentials = lambda x: values
            handlers.append(
                CosignHandler(
                    self.authen_elt.get('cosignLoginPage'),
                    self.cookie_jar,
                    CosignPasswordMgr(callback = credentials),
                    save_cookies = True
                    )
                )

        elif self.authen_type == 'cert':
            # Get the cert and key locations from credentials
            try:
                # See if credentials is callable
                cred = credentials()
            except TypeError:
                # It should be a dictionary
                if credentials is None:
                    cred = {}
                else:
                    cred = credentials

            keyfile = cred.get('key')
            if keyfile is None and service_id is not None:
                keyfile = os.path.join(context.conf_dir(),
                                       'services',
                                       service_id,
                                       'myself.key')

            certfile = cred.get('cert')
            if certfile is None and service_id is not None:
                certfile = os.path.join(context.conf_dir(),
                                        'services',
                                        service_id,
                                        'myself.crt')

            handlers.append(
                HTTPSClientAuthHandler(keyfile,certfile)
                )

        elif self.authen_type == 'debug':
            try:
                # See if credentials is callable
                cred = credentials()
            except TypeError:
                # It should be a dictionary
                cred = credentials
            if cred is None:
                # Still not set: raise exception
                raise ValueError('"name" not set for debug authentication')

            self.url = '{}/{}:{}'.format(self.url,
                                         self.obj_type,
                                         cred.get('name'))

        elif self.authen_type == 'public':
            # Nothing to be done - just need it to be in the list of
            # auth types.
            pass
        else:
            raise ValueError(
                'Invalid authentication type "{}"'.format(self.authen_type)
                )

        self.opener = urllib_request.build_opener(*handlers)

    # Convenience method for constructing wc from an etree element.
    @classmethod
    def from_service_elt(cls, service_elt, obj_type, credentials=None):
        '''Class method: construct a WebClient from an etree element.
        '''
        tmp_auth = service_elt.xpath(
            'authentication[@id="{}"]'.format(obj_type)
            )
        if not tmp_auth:
            # Some default authentication types
            tmp_elt = etree.Element('authentication')
            tmp_elt.set('id', str(self.obj_type))
            if self.obj_type == 'person':
                tmp_elt.set("type", "basic")
            elif self.obj_type == 'os_instance':
                tmp_elt.set("type", "cert")
            elif self.obj_type is None:
                tmp_elt.set("type", "public")
            else:
                raise ValueError(
                    "Can't find authentication type for object type '{}'".format(obj_type)
                    )
            tmp_auth=[tmp_elt]
        authen_elt = tmp_auth[0]
        authen_type = authen_elt.get("type")
        if authen_type == 'debug' and credentials is None:
            credentials = {'name': authen_elt.get('username')}
        service_id = service_elt.get('id')
        hierarchy_url = service_elt.xpath('hierarchy/@id')[0]
        return cls(hierarchy_url = hierarchy_url,
                   authen_type = authen_type,
                   obj_type = obj_type,
                   credentials = credentials,
                   service_id = service_id)


    # Convenience method: construct wc from element in config matching
    # service_id.
    @classmethod
    def from_service_id(cls, service_id, obj_type, credentials=None):
        '''Class method: construct a WebClient from element in config.xml.
        '''
        try:
            service_elt = context.machination_worker_elt.xpath(
                'services/service[@id="{}"]'.format(service_id)
                )[0]
        except IndexError:
            raise Exception("service id '{}' not found in desired_status".format(service_id))
        return cls.from_service_elt(service_elt, obj_type, credentials)

    def call(self, name, *args):
        '''Invoke method name in hierarchy with arguments *args.
        '''
        l.lmsg("calling " + name + " on " + self.url)
        call_elt = etree.Element("r", call=name)
        for arg in args:
            call_elt.append(to_xml(arg))
        l.dmsg(etree.tostring(call_elt, pretty_print=True))

        # construct and send a request
        r = urllib_request.Request(
            self.url,
            etree.tostring(call_elt, encoding=self.encoding),
            {'Content-Type':
                 'application/x-www-form-urlencoded;charset=%s' % self.encoding}
            )
        urllib_request.install_opener(self.opener)
        f = urllib_request.urlopen(r)
        s = f.read().decode(self.encoding)
#        print("got:\n" + s)
        elt = etree.fromstring(s)
        if elt.tag == 'error':
            msg = elt.xpath('message/text()')[0]
            raise Exception('error at the server end:\n' + msg)
        ret = from_xml(elt)
        return ret

    @functools.lru_cache(maxsize=None)
    def memo(self, name, *args):
        '''Invoke method name in hierarchy and memoise results.
        '''
        return self.call(name, *args)

    def help(self):
        return self.call("Help")
