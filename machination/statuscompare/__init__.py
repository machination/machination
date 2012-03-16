#!/usr/bin/python
# vim: set fileencoding=utf-8:

"""A machination module to calculate the difference between profile and status.

Machination (and its workers) will call this library to ask for a 'worklist'
based on differences between the 'local' status.xml and the downloaded profile.

"""

from lxml import etree


class XMLCompare(object):

    def __init__(self, leftxml, rightxml):
        self.leftxml = leftxml
        self.rightxml = rightxml
        self.leftset = set()
        self.rightset = set()
        self.bystate = {'left': {},
                        'right': {},
                        'same': {},
                        'datadiff': {},
                        'structdiff': {}}
        self.byxpath = {}

    def compare(self):
        """Compare the xpath sets and generate a diff dict"""

        self.make_xpath(self.leftset, self.leftxml.getroot())

        self.make_xpath(self.rightset, self.rightxml.getroot())

        for xpath in self.leftset.difference(self.rightset):
            self.bystate['left'][xpath] = 1
            self.byxpath[xpath] = 'left'

        for xpath in self.rightset.difference(self.leftset):
            self.bystate['right'][xpath] = 1
            self.byxpath[xpath] = 'right'

        self.find_diffs(self.leftset.intersection(self.rightset))

    def find_diffs(self, xpathlist):
        """Find differing values in the intersection set"""

        for xpath in xpathlist:
            l = self.leftxml.xpath(xpath)
            r = self.rightxml.xpath(xpath)

            # l[0] or r[0] can be element objects, or attr strings
            # Try to get the tag - if it fails, its an attribute
            lval = ""
            rval = ""

            try:
                lval = l[0].tag
                rval = r[0].tag
            except AttributeError:
                lval = l[0]
                rval = r[0]

            if lval != rval:
                self.bystate['datadiff'][xpath] = 1
                self.byxpath[xpath] = 'datadiff'
                parentpath = '/'
                for parent in xpath.split('/')[:-1]:
                    parent = parentpath + parent
                    self.bystate['structdiff'][parent] = 1
                    self.byxpath[parent] = 'structdiff'
                    if parent == '/':
                        parentpath = parent
                    else:
                        parentpath = parent + "/"

    def make_xpath(self, xpathset, elt, current="/"):
        """Recursively construct xpaths for all elements."""

        id = ""
        if elt.attrib.get("id"):
            id = "[@id='%s']" % (elt.attrib.get("id"))

        xpath = "%s%s%s" % (current, elt.tag, id)
        xpathset.add(xpath)

        for attr in elt.attrib:
            attr_path = "%s/@%s" % (xpath, attr)
            xpathset.add(attr_path)

        current = xpath + "/"
        for childelt in elt:
            self.make_xpath(xpathset, childelt, current)


if __name__ == "__main__":

    import sys
    import pprint
    pp = pprint.PrettyPrinter()

    leftfile = sys.argv[1]
    rightfile = sys.argv[2]

    leftxml = etree.parse(leftfile)
    rightxml = etree.parse(rightfile)

    xmlcmp = XMLCompare(leftxml, rightxml)
    xmlcmp.compare()
    pp.pprint(xmlcmp.byxpath)
