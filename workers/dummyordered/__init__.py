#!/usr/bin/python

"A test worker which relies on the order of elements in its XML"

from lxml import etree
from machination import context
import os

class DummyOrdered():
    "Test of order preservation"

    def __init__(self, my_desired_status):
        self.desired = my_desired_status

    def generate_status(self):
        pass

    def do_work(self,wus):
        pass
