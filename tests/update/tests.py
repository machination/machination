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
from machination.workers import dummyordered as do

class UpdateTestCase(unittest.TestCase):

    def setUp(self):
        self.u = Update()
        st = etree.fromstring(
            """
<worker id='dummyordered'>
  <sysitem id='1'>sysone</sysitem>
  <sysitem id='removeme'>rem</sysitem>
  <notordered id='3'>changeme</notordered>
  <notordered id='2'>notwo</notordered>
</worker>
            """)
        do.worker.set_status(st)

    def test_desired_status(self):
        st = self.u.desired_status()
#        print()
#        print(etree.tostring(st))
        self.assertEqual(st.tag, 'status')

    def test_gather_status(self):
        st = self.u.gather_status()
        print()
        print(etree.tostring(st))
        # make sure the dummyordered worker element is in status
        self.assertNotEqual(len(st.xpath('/status/worker[@id="dummyordered"]')),0)

    def test_do_update(self):
        self.u

if __name__ == '__main__':
    upsuite = unittest.TestLoader().loadTestsFromTestCase(UpdateTestCase)
    alltests = unittest.TestSuite([])
#    unittest.TextTestRunner(verbosity=2).run(alltests)
    unittest.TextTestRunner(verbosity=2).run(upsuite)
