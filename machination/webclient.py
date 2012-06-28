import pprint
import sys
import os
from lxml import etree
from machination.xmldata import from_xml, to_xml
from machination import context
#from machination.xmltools import pstring

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

    def __init__(self, url):
        self.url = url
#        self.user = user
        self.encoding = 'utf-8'
        self.l = context.logger

    def call(self, name, *args):
        print("calling " + name + " on " + self.url)
        call_elt = etree.Element("r", call=name)
        for arg in args:
            call_elt.append(to_xml(arg))
        print(etree.tostring(call_elt, pretty_print=True))

        # construct and send a request
        r = urllib_request.Request(
            self.url,
            etree.tostring(call_elt, encoding=self.encoding),
            {'Content-Type':
                 'application/x-www-form-urlencoded;charset=%s' % self.encoding})
        cert_handler = HTTPSClientAuthHandler(
            os.path.join(context.conf_dir(), 'secrets', 'client.key'),
            os.path.join(context.conf_dir(), 'secrets', 'client.crt'))
        opener = urllib_request.build_opener(cert_handler)
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
