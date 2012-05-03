import pprint
import sys
from lxml import etree
import urllib.request
from machination.xmldata import from_xml, to_xml
from machination import context


class WebClient(object):
    """Machination WebClient"""

    def __init__(self, url, user):
        self.url = url
        self.user = user
        self.encoding = 'utf-8'
        self.l = context.logger

    def call(self, name, *args):
        print self.user + " is calling " + name + " on " + self.url
        call_elt = etree.Element("r",call=name,user=self.user)
        for arg in args:
            call_elt.append(machination.xmldata.to_xml(arg))
        print etree.tostring(call_elt,pretty_print=True)

        # construct and send a request
        r = urllib.request.Request\
            (self.url,
             etree.tostring(call_elt, encoding=self.encoding),
             {'Content-Type':
                  ' application/x-www-form-urlencoded;charset={}'.format(self.encoding)})
        f=urllib.request.urlopen(r)
        return etree.parse(f)

    def help(self):
        f = urllib2.urlopen(self.url,'<r call="Help" user="'
                            + self.user +
                            '"><s>/</s></r>')
        s = f.read()
        print s