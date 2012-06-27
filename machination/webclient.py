import pprint
import sys
from lxml import etree
from machination.xmldata import from_xml, to_xml
from machination import context
#from machination.xmltools import pstring

try:
    import urllib.request as urllib_request
except ImportError:
    import urllib2 as urllib_request

class WebClient(object):
    """Machination WebClient"""

    def __init__(self, url, user):
        self.url = url
        self.user = user
        self.encoding = 'utf-8'
        self.l = context.logger

    def call(self, name, *args):
        print(self.user + " is calling " + name + " on " + self.url)
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
