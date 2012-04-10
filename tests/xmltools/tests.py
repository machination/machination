#!/usr/bin/python

import unittest
import inspect, os, shutil
from lxml import etree

myfile = inspect.getfile(inspect.currentframe())
mydir = os.path.dirname(inspect.getfile(inspect.currentframe()))
os.environ['MACHINATION_BOOTSTRAP_DIR'] = mydir
from machination import context
from machination.workerdescription import WorkerDescription
from machination import xmltools

class XMLTestCase(unittest.TestCase):

    def setUp(self):
        self.wds = context.desired_status.xpath("worker[@id='test']")[0]

    def tearDown(self):
        self.wds = None
        
    def test_worker_desired_status(self):
        self.assertEqual(self.wds.tag, "worker")
        self.assertEqual(self.wds.get("id"),"test")

    def test_validate_wds(self):
        schema = etree.parse(os.path.join(mydir, "test-worker-description.xml"))
        rng = etree.RelaxNG(schema)
        rng.assertValid(self.wds)


if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(XMLTestCase)
    unittest.TextTestRunner(verbosity=2).run(suite)
