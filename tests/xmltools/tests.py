#!/usr/bin/python

import unittest
import inspect, os, shutil, pprint, copy
from lxml import etree

myfile = inspect.getfile(inspect.currentframe())
mydir = os.path.dirname(inspect.getfile(inspect.currentframe()))
os.environ['MACHINATION_BOOTSTRAP_DIR'] = mydir
from machination import context
from machination.workerdescription import WorkerDescription
from machination.xmltools import MRXpath
from machination.xmltools import status

class XMLTestCase(unittest.TestCase):

    def setUp(self):
        self.wdesired = context.desired_status.xpath("worker[@id='test']")[0]
        self.wschema = etree.parse(os.path.join(mydir, "test-worker-description.xml"))
        self.wdesc = WorkerDescription(self.wschema.getroot())
        self.rng = etree.RelaxNG(self.wschema)

    def test_validate_wds(self):
        self.rng.assertValid(self.wdesired)

    def test_worker_desired_status(self):
        self.assertEqual(self.wdesired.tag, "worker")
        self.assertEqual(self.wdesired.get("id"),"test")

class Testinfo1Case(unittest.TestCase):

    def setUp(self):
        self.wschema = etree.parse(os.path.join(mydir, "test-worker-description.xml"))
        self.wdesc = WorkerDescription(self.wschema.getroot())
        self.rng = etree.RelaxNG(self.wschema)
        self.tinfo = etree.parse(os.path.join(mydir,"worker-testinfo1.xml")).getroot()
        self.start = copy.deepcopy(self.tinfo.xpath("status[@id='start']/worker")[0])
        self.desired = copy.deepcopy(self.tinfo.xpath("status[@id='desired']/worker")[0])
        self.actions = {'add': set(), 'remove': set(), 'modify': set()}

    def populate_actions(self, setid):
        for a in self.tinfo.xpath("actionsets[@id='%s']" % setid)[0]:
            self.actions[a.tag].add(MRXpath(a.get("id")).to_xpath())
        
    def test_010_statuses_valid(self):
        self.rng.assertValid(self.start)
        self.rng.assertValid(self.desired)

    def test_020_wuwus_correct(self):
        self.assertFalse(self.wdesc.is_workunit("/worker"))
        self.assertTrue(self.wdesc.is_workunit("/worker/iniFile"))
        self.assertFalse(self.wdesc.is_workunit("/worker/iniFile/section"))
        self.assertFalse(self.wdesc.is_workunit("/worker/iniFile/section/keyvalue"))
#        self.assertFalse(self.wdesc.is_workunit("/worker/orderedItems"))
        self.assertTrue(self.wdesc.is_workunit("/worker/orderedItems/item"))
#        self.assertFalse(self.wdesc.is_workunit("/worker/unordered"))
        self.assertTrue(self.wdesc.is_workunit("/worker/unordered/item"))

    def test_030_generate_wus(self):
        self.populate_actions(1)
        start_st = status(self.start)
        working = copy.deepcopy(self.start)
        start_st.generate_wus(working, self.desired,self. actions, self.wdesc)
        


if __name__ == '__main__':
    xmlsuite = unittest.TestLoader().loadTestsFromTestCase(XMLTestCase)
    testinfo1_suite = unittest.TestLoader().loadTestsFromTestCase(Testinfo1Case)
    alltests = unittest.TestSuite([xmlsuite,testinfo1_suite])
    unittest.TextTestRunner(verbosity=2).run(alltests)
