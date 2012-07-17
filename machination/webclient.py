import pprint
import sys
import os
from lxml import etree
from machination.xmldata import from_xml, to_xml
from machination import context
#from machination.xmltools import pstring
from machination.cosign import CosignPasswordMgr, CosignHandler

try:
    import urllib.request as urllib_request
    import http.client as http_client
except ImportError:
    import urllib2 as urllib_request
    import httplib as http_client

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
        return http_client.HTTPSConnection(host,
                                           key_file=self.key,
                                           cert_file=self.cert)

class WebClient(object):
    """Machination WebClient"""

    def __init__(self, service_id, url, authen_type):
        self.service_id
        self.url = url
        self.authen_type = authen_type
        self.encoding = 'utf-8'
        self.l = context.logger
        self.cookie_file = os.path.join(context.status_dir(), 'cookies.txt')
        self.cookie_jar = None
        handlers = []
        if self.authen_type == 'cosign':
            self.cookie_jar = http.cookiejar.MozillaCookieJar(
                self.cookie_file
                )
            try:
                self.cookie_jar.load(ignore_discard=True)
            except IOError:
                pass
            handlers.append(
                self.cookie_jar
                )
            handlers.append(
                CosignHandler(
                    'https://www.ease.ed.ac.uk/',
                    self.cookie_jar,
                    CosignPasswordMgr()
                    )
                )
        elif self.authen_type == 'cert':
            handlers.append(
                HTTPSClientAuthHandler(
                    os.path.join(context.conf_dir(),
                                 'services',
                                 self.service_id,
                                 'client.key'),
                    os.path.join(context.conf_dir(),
                                 'services',
                                 self.service_id,
                                 'client.crt')
                    )
                )

        self.opener = urllib_request.build_opener(*handlers)

    def full_url(self):
        return '{}/{}'.format(self.url, self.authen_type)

    def call(self, name, *args):
        print("calling " + name + " on " + self.full_url())
        call_elt = etree.Element("r", call=name)
        for arg in args:
            call_elt.append(to_xml(arg))
        print(etree.tostring(call_elt, pretty_print=True))

        # construct and send a request
        r = urllib_request.Request(
            self.full_url(),
            etree.tostring(call_elt, encoding=self.encoding),
            {'Content-Type':
                 'application/x-www-form-urlencoded;charset=%s' % self.encoding})
        urllib_request.install_opener(opener)
        f = urllib_request.urlopen(r)
        s = f.read().decode(self.encoding)
#        print("got:\n" + s)
        elt = etree.fromstring(s)
        if elt.tag == 'error':
            raise Exception('error at the server end:\n' + elt[0].text)
        ret = from_xml(elt)
        return ret

    def help(self):
        return self.call("Help")
