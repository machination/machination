# WebClient module
#import cPickle
import pprint
import sys
from lxml import etree
import urllib2
import types
#from machination.exceptions import *
import machination.xmldata

class WebClient:
    "OO interface to Machination WebClient"

    def call(self,name,*args,**opts):
        print self.user + " is calling " + name + " on " + self.url
        call_elt = etree.Element("r",call=name,user=self.user)
        for arg in args:
            call_elt.append(machination.xmldata.to_xml(arg))
        print etree.tostring(call_elt,pretty_print=True)
        f=urllib2.urlopen(self.url,etree.tostring(call_elt))
        return etree.parse(f)

    def help(self):
        f = urllib2.urlopen(self.url,'<r call="Help" user="'
                            + self.user +
                            '"><s>/</s></r>')
        s = f.read()
        print s
