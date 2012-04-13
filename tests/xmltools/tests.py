#!/usr/bin/python

import unittest
import inspect, os, shutil, pprint, copy
from lxml import etree

myfile = inspect.getfile(inspect.currentframe())
mydir = os.path.dirname(inspect.getfile(inspect.currentframe()))
os.environ['MACHINATION_BOOTSTRAP_DIR'] = mydir
from machination import context
from machination.xmltools import MRXpath
from machination.xmltools import WorkerDescription
from machination.xmltools import Status
from machination.xmltools import XMLCompare

class MRXpathTestCase(unittest.TestCase):

    def test_constructor_strxpath(self):
        mrx = MRXpath("/a/b/c[@id='/d/e[@id=\"1\"]']")
        self.assertEqual('/a/b/c[\'/d/e[@id="1"]\']', mrx.to_abbrev_xpath())

    def test_constructor_strabbrevxpath(self):
        mrx = MRXpath('/a/b/c[\'/d/e[@id="1"]\']')
        self.assertEqual("/a/b/c[@id='/d/e[@id=\"1\"]']", mrx.to_xpath())

    def test_constructor_list(self):
        mrx = MRXpath([[''], ['a'], ['b'], ['c', '/d/e[@id="1"]']])
        self.assertEqual('/a/b/c[\'/d/e[@id="1"]\']', mrx.to_abbrev_xpath())

    def test_constructor_mrxpath(self):
        mrx = MRXpath('/a/b/c[\'/d/e[@id="1"]\']')
        mrx2 = MRXpath(mrx)
        self.assertEqual(mrx, mrx2)

    def test_sequence_getone(self):
        mrx = MRXpath('/a/b/c[\'/d/e[@id="1"]\']')
        self.assertEqual(str(mrx[0]),"a")
        self.assertEqual(str(mrx[2]),'c[@id=\'/d/e[@id="1"]\']')

    def test_sequence_getslice(self):
        mrx = MRXpath('/a/b/c[\'/d/e[@id="1"]\']')
        self.assertEqual(mrx[:2], MRXpath("/a/b"))
        self.assertEqual(mrx[1:], MRXpath('b/c[@id=\'/d/e[@id="1"]\']'))
        self.assertEqual(mrx[1:2].reroot(), MRXpath("/b"))

    def test_sequence_setslice(self):
        mrx = MRXpath('/a/b/c[\'/d/e[@id="1"]\']')
        mrx[0] = "splat"
        self.assertEqual(str(mrx[0]), "splat")
        mrx[:2] = "frog/mince[1]"
        self.assertEqual(str(mrx), "/frog/mince[@id='1']/c[@id='/d/e[@id=\"1\"]']")

    def test_tests(self):
        mrx = MRXpath('/a/b/c[\'/d/e[@id="1"]\']')
        self.assertTrue(mrx.is_element())
        self.assertFalse(mrx.is_attribute())
        self.assertTrue(mrx.is_rooted())
        mrx.append("@att")
        self.assertFalse(mrx.is_element())
        self.assertTrue(mrx.is_attribute())

    def test_ancestors(self):
        mrx = MRXpath("/a/b/c")
        self.assertEqual(mrx.ancestors(), [MRXpath("/a/b"), MRXpath("/a")])

    def test_name_id(self):
        mrx = MRXpath('/a/b/c[\'/d/e[@id="1"]\']')
        self.assertEqual(mrx.name(), "c")
        self.assertEqual(mrx.id(), '/d/e[@id="1"]')

class WDTestCase(unittest.TestCase):

    def setUp(self):
        self.wdesired = context.desired_status.xpath("worker[@id='test']")[0]
        self.wdesc = WorkerDescription("test")
        self.rng = etree.RelaxNG(self.wdesc.desc)

    def test_validate_wds(self):
        self.rng.assertValid(self.wdesired)

    def test_worker_desired_status(self):
        self.assertEqual(self.wdesired.tag, "worker")
        self.assertEqual(self.wdesired.get("id"),"test")

class XMLCompareTestCase(unittest.TestCase):
    def setUp(self):
        self.tinfo = etree.parse(os.path.join(mydir,"worker-testinfo1.xml")).getroot()
        self.start = copy.deepcopy(self.tinfo.xpath("status[@id='start']")[0])
        del self.start.attrib['id']
        self.desired = copy.deepcopy(self.tinfo.xpath("status[@id='desired']")[0])
        del self.desired.attrib['id']
        self.xmlc = XMLCompare(self.start, self.desired)

    def test_constructor(self):
        print()
#        pprint.pprint(self.xmlc.byxpath)
        self.assertIn("/status/worker[@id='test']/orderedItems/item[@id='2']", self.xmlc.bystate['right'])

    def test_find_work(self):
        work = self.xmlc.find_work()
        print()
        pprint.pprint(self.xmlc.actions(work))
        self.assertIn('/status/worker[@id=\'test\']/iniFile' , work)
        self.assertNotIn("/status/worker[@id='test']/orderedItems", work)

        # quick memoization test
        work2 = self.xmlc.find_work()
        self.assertEqual(work, work2)

class Testinfo1Case(unittest.TestCase):

    def setUp(self):
        self.wdesc = WorkerDescription('test')
        self.rng = etree.RelaxNG(self.wdesc.desc)
        self.tinfo = etree.parse(os.path.join(mydir,"worker-testinfo1.xml")).getroot()
        self.actions = {'add': set(), 'remove': set(), 'modify': set()}
        self.start = copy.deepcopy(self.tinfo.xpath("status[@id='start']")[0])
        del self.start.attrib['id']
        self.desired = copy.deepcopy(self.tinfo.xpath("status[@id='desired']")[0])
        del self.desired.attrib['id']
        self.comp = XMLCompare(self.start, self.desired)


    def populate_actions(self, setid):
        for a in self.tinfo.xpath("actionsets[@id='%s']" % setid)[0]:
            self.actions[a.tag].add(MRXpath(a.get("id")).to_xpath())

    def test_010_statuses_valid(self):
        self.rng.assertValid(self.start.xpath("worker[@id='test']")[0])
        self.rng.assertValid(self.desired.xpath("worker[@id='test']")[0])

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
#        self.populate_actions(1)
        start_st = Status(self.start, worker_prefix='/status')
        print()
        print(start_st.worker_prefix())
        start_st.generate_wus(self.comp)



if __name__ == '__main__':
    mrxsuite = unittest.TestLoader().loadTestsFromTestCase(MRXpathTestCase)
    xmlcomp_suite = unittest.TestLoader().loadTestsFromTestCase(XMLCompareTestCase)
    wdsuite = unittest.TestLoader().loadTestsFromTestCase(WDTestCase)
    testinfo1_suite = unittest.TestLoader().loadTestsFromTestCase(Testinfo1Case)
    alltests = unittest.TestSuite([mrxsuite, wdsuite, xmlcomp_suite, testinfo1_suite])
    unittest.TextTestRunner(verbosity=2).run(alltests)
