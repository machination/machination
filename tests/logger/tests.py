#!/usr/bin/python

import unittest
import inspect
import os
from lxml import etree
from lxml.builder import E

myfile = inspect.getfile(inspect.currentframe())
mydir = os.path.dirname(inspect.getfile(inspect.currentframe()))
os.environ['MACHINATION_BOOTSTRAP_DIR'] = mydir
from machination import context


class LoggerTestCase(unittest.TestCase):

    def setUp(self):
        context.logger.dmsg('hello')

if __name__ == '__main__':
    logsuite = unittest.TestLoader().loadTestsFromTestCase(LoggerTestCase)
    alltests = unittest.TestSuite([logsuite])
    unittest.TextTestRunner(verbosity=2).run(alltests)
