#!/usr/bin/python

import unittest
import inspect, os, shutil, pprint, copy
from lxml import etree
from lxml.builder import E
import pkgutil
import importlib

myfile = inspect.getfile(inspect.currentframe())
mydir = os.path.dirname(inspect.getfile(inspect.currentframe()))
os.environ['MACHINATION_BOOTSTRAP_DIR'] = os.path.join(mydir, 'cache')
from machination.update import Update

class UpdateTestCase(unittest.TestCase):

    def setUp(self):
        self.u = Update()

    def test_desired_status(self):
        st = self.u.desired_status()
#        print()
#        print(etree.tostring(st))
        self.assertEqual(st.tag, 'status')

    def test_gather_status(self):
        st = self.u.gather_status()
        print()
        print(etree.tostring(st))

if __name__ == '__main__':
    upsuite = unittest.TestLoader().loadTestsFromTestCase(UpdateTestCase)
    alltests = unittest.TestSuite([])
#    unittest.TextTestRunner(verbosity=2).run(alltests)
    unittest.TextTestRunner(verbosity=2).run(upsuite)
