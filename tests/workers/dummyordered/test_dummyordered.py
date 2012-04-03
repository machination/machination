#!/usr/bin/python

import unittest
from lxml import etree
from workers import dummyordered

class TestInstantiation(unittest.TestCase):

    def setUp(self):
        self.do = DummyOrdered(etree.parse("desired-status1.xml").getroot())
        

    def test_desired(self):
        self.assertTrue(self.do.desired.tag == "worker")
