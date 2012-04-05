#!/usr/bin/python

import unittest
import inspect, os, shutil
from lxml import etree

myfile = inspect.getfile(inspect.currentframe())
mydir = os.path.dirname(inspect.getfile(inspect.currentframe()))
os.environ['MACHINATION_BOOTSTRAP_DIR'] = mydir
from workers import dummyordered

class WorkerTestCase(unittest.TestCase):

    def setUp(self):
        self.w = dummyordered.worker(datadir = os.path.join(mydir,"testdata"))

    def tearDown(self):
        self.w.clear_data()

    def test_desired(self):
        self.assertEqual(self.w.end_desired.tag, "worker")

    def test_datadir(self):
        self.assertEqual(self.w.datadir, os.path.join(mydir,"testdata"))

    def set_status(self,fname):
        self.w.set_status(etree.parse(os.path.join(mydir,fname)).getroot())

    def test_set_status(self):
        self.set_status("start-status1.xml")
        self.pdb = dummyordered.pretend_db(os.path.join(self.w.datadir, "pdb"))
        self.assertEqual(self.pdb.get_start(), "4")
        self.assertEqual(self.pdb.get_end(), "3")

if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(WorkerTestCase)
    unittest.TextTestRunner(verbosity=2).run(suite)
