"Wraps the fetcher in a worker"

from lxml import etree
from machination import context
from machination import xmltools
import os
import errno
import sys


class Worker(object):
    """Fetch tagged bundles from sources defined in config

    """

    def __init__(self):
        self.name = self.__module__.split('.')[-1]
        self.wd = xmltools.WorkerDescription(self.name,
                                             prefix='/status')

    def generate_status(self):
        w_elt = etree.Element("worker")
        w_elt.set("id", self.name)

        return w_elt

    def do_work(self, wus):
        results = []
