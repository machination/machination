#!/usr/bin/python

import unittest
import inspect, os, shutil
from lxml import etree

myfile = inspect.getfile(inspect.currentframe())
mydir = os.path.dirname(inspect.getfile(inspect.currentframe()))
os.environ['MACHINATION_BOOTSTRAP_DIR'] = mydir
from workers import dummyordered

class WorkertTestCase(unittest.TestCase):

    def setUp(self):
        self.w = dummyordered.worker(datadir = "testdata")
        self.w.clear_data()

    def tearDown(self):
        self.w.clear_data()
        shutil.rmtree(self.w.datadir)

    def test_desired(self):
        self.assertTrue(self.w.desired.tag == "worker")

    def test_datadir(self):
        self.assertTrue(self.w.datadir == "testdata")

    def test_direct_status(self):
        self.w.set_status("start-status1.xml")

if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(WorkerTestCase)
    unittest.TextTestRunner(verbosity=2).run(suite)
