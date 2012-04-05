#!/usr/bin/python

import unittest
from lxml import etree
from workers import dummyordered

class TestInstantiation(unittest.TestCase):

    def setUp(self):
        self.w = dummyordered.worker()
        

    def test_desired(self):
        self.assertTrue(self.w.desired.tag == "worker")

if __name__ == '__main__':
    unittest.main()
