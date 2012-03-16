#!/usr/bin/python
# vim: set fileencoding=utf-8:

"""Test suite for statuscompare module."""


import unittest
from lxml import etree
import sys

sys.path.append("..")
from machination import statuscompare


class TestStatusCompare(unittest.TestCase):

    def setUp(self):
        self.leftxml = etree.parse("left.xml")
        self.rightxml = etree.parse("right.xml")

    def test_compare(self):

        testresult = {"/a[@id='a']/e[@id='e']": 'left',
                      "/a[@id='a']/g[@id='g']/h[@id='h']/@tree": 'datadiff',
                      "/a[@id='a']/b[@id='b']/@animal": 'datadiff',
                      "/a[@id='a']/e[@id='e']/@id": 'left',
                      "/a[@id='a']/f[@id='f']/@id": 'right',
                      '/': 'structdiff',
                      "/a[@id='a']": 'structdiff',
                      "/a[@id='a']/b[@id='b']": 'structdiff',
                      "/a[@id='a']/g[@id='g']/h[@id='h']": 'structdiff',
                      "/a[@id='a']/g[@id='g']": 'structdiff',
                      "/a[@id='a']/f[@id='f']": 'right'}

        xmlcmp = statuscompare.XMLCompare(self.leftxml, self.rightxml)
        xmlcmp.compare()
        self.assertEqual(testresult, xmlcmp.byxpath)

if __name__ == "__main__":
    unittest.main()
